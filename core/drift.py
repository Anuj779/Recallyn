# -*- coding: utf-8 -*-
"""
core/drift.py
=============
Context Drift Detection — Compare old snapshot vs current world.

CONCEPT: What is Context Drift?
---------------------------------------------------------------------------
Drift is when the world has changed in a way that matters for a workflow.

Example:
    When taught:  Manager = "Carol Singh"
    Right now:    Manager = "Priya Sharma"

The workflow would still run — but it might email the WRONG person.
That is drift.

CONCEPT: Why MATCH / DRIFT / UNKNOWN (not just yes/no)?
---------------------------------------------------------------------------
A simple yes/no binary ("changed / not changed") is too coarse.

MATCH   = "I compared the important fields and they're the same."
DRIFT   = "I compared the fields and found a meaningful change."
UNKNOWN = "I cannot make a reliable comparison."
           e.g., no snapshot was saved, or a field is missing.

UNKNOWN is NOT the same as safe. It means we don't know.
A cautious system treats UNKNOWN as potentially risky.
(Phase 4 will decide what to do about each verdict.)

CONCEPT: Alert Fatigue
---------------------------------------------------------------------------
If we flag EVERY tiny change as drift, the user will start ignoring
drift warnings. This defeats the purpose of the safety layer.

So we only flag MEANINGFUL changes:
    - Recipient identity changed          -> DRIFT
    - Recipient became inactive           -> DRIFT (CRITICAL)
    - Required file disappeared           -> DRIFT
    - Recipient email changed             -> DRIFT

We do NOT flag:
    - File size grew (expected over time) -> MATCH
    - Date is different (always true)     -> ignored
    - Content of the file changed         -> not modeled here

ARCHITECTURE RULE:
    Drift detection is purely deterministic Python.
    No LLM, no embeddings, no vector search.
    Simple field-by-field comparison with explicit rules.
---------------------------------------------------------------------------
"""

import sys
import io
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))
from context import build_current_context


# ===========================================================================
# RESULT STRUCTURES
# ===========================================================================

@dataclass
class DriftChange:
    """
    A single detected change between the old snapshot and current context.

    Fields:
        field     : The name of the field that changed (e.g., "recipient_name")
        old_value : What the field said in the saved snapshot
        new_value : What the field says NOW in the current world
        severity  : LOW | MEDIUM | HIGH | CRITICAL
        reason    : Human-readable explanation of why this matters
    """
    field:     str
    old_value: Any
    new_value: Any
    severity:  str       # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    reason:    str


@dataclass
class DriftResult:
    """
    The complete output of a drift check.

    Fields:
        workflow_id    : The workflow that was checked
        verdict        : "MATCH" | "DRIFT" | "UNKNOWN"
        changes        : List of DriftChange objects (empty if MATCH/UNKNOWN)
        reason         : Overall human-readable explanation
        suggested_fix  : Optional repair hint (e.g., "Use Priya as Manager?")
        old_snapshot   : The snapshot that was saved when the workflow was taught
        current_context: The context that was built from the current world
    """
    workflow_id:     str
    verdict:         str                     # "MATCH" | "DRIFT" | "UNKNOWN"
    changes:         List[DriftChange]       = field(default_factory=list)
    reason:          str                     = ""
    suggested_fix:   Optional[str]           = None
    old_snapshot:    Optional[Dict[str, Any]] = None
    current_context: Optional[Dict[str, Any]] = None


# ===========================================================================
# SEVERITY LEVELS (as integers for comparison)
# ===========================================================================

SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _highest_severity(changes: List[DriftChange]) -> str:
    """Return the highest severity among all detected changes."""
    if not changes:
        return "LOW"
    return max(changes, key=lambda c: SEVERITY_RANK.get(c.severity, 0)).severity


# ===========================================================================
# FIELD COMPARISON RULES
# ===========================================================================

def _compare_recipient(
    old: Dict[str, Any],
    current: Dict[str, Any],
    changes: List[DriftChange],
) -> None:
    """
    Compare recipient-related fields between old and current context.

    Rules:
        recipient_name changed   -> DRIFT (HIGH)
        recipient_status INACTIVE-> DRIFT (CRITICAL)
        recipient_email changed  -> DRIFT (MEDIUM)
        recipient not found now  -> DRIFT (HIGH)
    """
    # Only check if the snapshot modeled a recipient
    if "recipient_role" not in old:
        return

    old_name   = old.get("recipient_name")
    old_email  = old.get("recipient_email")
    old_status = old.get("recipient_status")

    cur_name   = current.get("recipient_name")
    cur_email  = current.get("recipient_email")
    cur_status = current.get("recipient_status")

    role = old.get("recipient_role", "?")

    # Rule 1: Recipient disappeared from the world
    if cur_name is None and old_name is not None:
        changes.append(DriftChange(
            field="recipient_name",
            old_value=old_name,
            new_value=None,
            severity="HIGH",
            reason=f"The contact for role '{role}' no longer exists in the directory."
        ))
        return  # No point checking further if contact is gone

    # Rule 2: Recipient name changed (different person in same role)
    if old_name and cur_name and old_name != cur_name:
        changes.append(DriftChange(
            field="recipient_name",
            old_value=old_name,
            new_value=cur_name,
            severity="HIGH",
            reason=(
                f"The '{role}' role is now held by '{cur_name}' "
                f"instead of '{old_name}'."
            )
        ))

    # Rule 3: Recipient became INACTIVE
    if cur_status and cur_status.upper() == "INACTIVE" and (old_status or "").upper() != "INACTIVE":
        changes.append(DriftChange(
            field="recipient_status",
            old_value=old_status,
            new_value=cur_status,
            severity="CRITICAL",
            reason=(
                f"'{cur_name or role}' is now INACTIVE. "
                "Sending to an inactive account may fail or be dangerous."
            )
        ))

    # Rule 4: Email address changed (same person, different address)
    if old_email and cur_email and old_email != cur_email:
        changes.append(DriftChange(
            field="recipient_email",
            old_value=old_email,
            new_value=cur_email,
            severity="MEDIUM",
            reason=f"The email address for '{role}' changed."
        ))


def _compare_file(
    old: Dict[str, Any],
    current: Dict[str, Any],
    changes: List[DriftChange],
) -> None:
    """
    Compare file-related fields between old and current context.

    Rules:
        file existed, now gone   -> DRIFT (HIGH)
        file didn't exist, now does -> DRIFT (LOW) — unexpected appearance
        file type changed        -> DRIFT (MEDIUM)
        file size changed        -> MATCH (ignored — expected)
    """
    if "source_file" not in old:
        return

    filename   = old.get("source_file", "?")
    old_exists = old.get("file_exists")
    cur_exists = current.get("file_exists")
    old_type   = old.get("file_type")
    cur_type   = current.get("file_type")

    # Rule 1: File was present, now missing
    if old_exists is True and cur_exists is False:
        changes.append(DriftChange(
            field="file_exists",
            old_value=True,
            new_value=False,
            severity="HIGH",
            reason=f"The file '{filename}' was available when the workflow was taught but is now missing."
        ))

    # Rule 2: File was absent, now present (unexpected appearance)
    elif old_exists is False and cur_exists is True:
        changes.append(DriftChange(
            field="file_exists",
            old_value=False,
            new_value=True,
            severity="LOW",
            reason=f"The file '{filename}' did not exist before but now it does."
        ))

    # Rule 3: File type changed (e.g., CSV replaced by PDF)
    elif old_type and cur_type and old_type != cur_type:
        changes.append(DriftChange(
            field="file_type",
            old_value=old_type,
            new_value=cur_type,
            severity="MEDIUM",
            reason=(
                f"The file '{filename}' changed type: was '{old_type}', now '{cur_type}'."
            )
        ))

    # File size change: intentionally NOT flagged (normal expected variation)


# ===========================================================================
# REPAIR SUGGESTION GENERATOR
# ===========================================================================

def _build_suggested_fix(changes: List[DriftChange]) -> Optional[str]:
    """
    Generate a simple human-readable repair suggestion for the most
    impactful detected drift.

    We only generate suggestions for actionable changes (not critical ones
    like INACTIVE status — those should be escalated, not auto-fixed).

    Returns None if no simple fix can be suggested.
    """
    for change in sorted(changes, key=lambda c: SEVERITY_RANK.get(c.severity, 0), reverse=True):

        if change.field == "recipient_name" and change.new_value:
            return (
                f"'{change.old_value}' is no longer the {change.field.split('_')[0]}. "
                f"Use '{change.new_value}' instead?"
            )

        if change.field == "recipient_email" and change.new_value:
            return f"Update email from '{change.old_value}' to '{change.new_value}'?"

        if change.field == "file_exists" and change.new_value is False:
            return f"The required file appears to be missing. Verify the file path before running."

    return None


# ===========================================================================
# MAIN DRIFT CHECK FUNCTION
# ===========================================================================

def check_drift(workflow) -> DriftResult:
    """
    Compare a workflow's saved context_snapshot against the current world.

    This is the main entry point for Phase 3 drift detection.

    Flow:
        1. If no snapshot exists -> UNKNOWN
        2. Build current context using same fields as the snapshot
        3. Compare fields using deterministic rules
        4. Return MATCH if no meaningful changes found
        5. Return DRIFT with details if meaningful changes found

    Args:
        workflow: A validated Workflow object (from schema.py)

    Returns:
        A DriftResult with verdict, changes, and optional suggested fix.
    """
    # -----------------------------------------------------------------------
    # Case 1: No snapshot exists -> UNKNOWN
    # -----------------------------------------------------------------------
    if workflow.context_snapshot is None:
        return DriftResult(
            workflow_id=workflow.id,
            verdict="UNKNOWN",
            reason=(
                "No context snapshot was saved when this workflow was taught. "
                "Cannot determine if the current environment matches."
            ),
        )

    old = workflow.context_snapshot

    # -----------------------------------------------------------------------
    # Case 2: Build current context from live world
    # -----------------------------------------------------------------------
    try:
        current = build_current_context(old)
    except Exception as e:
        return DriftResult(
            workflow_id=workflow.id,
            verdict="UNKNOWN",
            reason=f"Could not build current context: {e}",
            old_snapshot=old,
        )

    # -----------------------------------------------------------------------
    # Case 3: Run field comparison rules
    # -----------------------------------------------------------------------
    changes: List[DriftChange] = []
    _compare_recipient(old, current, changes)
    _compare_file(old, current, changes)

    # -----------------------------------------------------------------------
    # Case 4: Build verdict
    # -----------------------------------------------------------------------
    if not changes:
        return DriftResult(
            workflow_id=workflow.id,
            verdict="MATCH",
            reason="All modeled context fields match the current environment.",
            old_snapshot=old,
            current_context=current,
        )

    # One or more meaningful changes detected -> DRIFT
    suggested = _build_suggested_fix(changes)
    severity  = _highest_severity(changes)

    reason_lines = []
    for c in changes:
        reason_lines.append(f"• {c.reason}")
    reason_str = "\n".join(reason_lines)

    return DriftResult(
        workflow_id=workflow.id,
        verdict="DRIFT",
        changes=changes,
        reason=reason_str,
        suggested_fix=suggested,
        old_snapshot=old,
        current_context=current,
    )


# ===========================================================================
# DISPLAY HELPER
# ===========================================================================

def print_drift_result(result: DriftResult) -> None:
    """
    Pretty-print a DriftResult to the console for the CLI.
    Called by app.py before running a workflow.
    """
    VERDICT_LABEL = {
        "MATCH":   "MATCH   -- Context is compatible.",
        "DRIFT":   "DRIFT   -- Context has changed.",
        "UNKNOWN": "UNKNOWN -- Cannot verify context.",
    }
    VERDICT_BORDER = {
        "MATCH":   "-",
        "DRIFT":   "*",
        "UNKNOWN": "~",
    }

    border = VERDICT_BORDER.get(result.verdict, "-") * 56
    print()
    print(f"  {border}")
    print(f"  CONTEXT CHECK   ({result.workflow_id})")
    print(f"  {border}")
    print(f"  Verdict : {VERDICT_LABEL.get(result.verdict, result.verdict)}")
    print(f"  Reason  : {result.reason}")

    if result.changes:
        print()
        print("  Changes detected:")
        for c in result.changes:
            print(f"    [{c.severity}] {c.field}")
            print(f"           Was : {c.old_value}")
            print(f"           Now : {c.new_value}")
            print(f"           Why : {c.reason}")

    if result.suggested_fix:
        print()
        print(f"  Suggested fix: {result.suggested_fix}")

    print(f"  {border}")
    print()


# ===========================================================================
# SELF-TEST — Run: python core/drift.py
# ===========================================================================

if __name__ == "__main__":
    import json
    from pathlib import Path

    print("=" * 60)
    print("  RECALLIS -- Drift Detection Test")
    print("=" * 60)

    from schema import Workflow

    ROOT_DIR  = Path(__file__).parent.parent
    WORLD_FILE = ROOT_DIR / "data" / "world.json"

    def load_world_raw():
        return json.loads(WORLD_FILE.read_text(encoding="utf-8"))

    def save_world_raw(data):
        WORLD_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Helper: build a workflow with a specific snapshot already attached
    def make_wf(snapshot):
        wf = Workflow(
            id="wf_drift_test",
            goal="Test drift detection",
            inputs={"source_file": "report.csv", "recipient_role": "manager"},
            steps=[{"n": 1, "tool": "read_file", "args": {"path": "$source_file"}}],
            version=1,
            confidence=0.9,
            context_snapshot=snapshot,
        )
        return wf

    # Baseline snapshot (what was true when taught)
    BASELINE_SNAPSHOT = {
        "taught_on":        "2026-08-30",
        "recipient_role":   "manager",
        "recipient_name":   "Carol Singh",
        "recipient_email":  "carol@company.local",
        "recipient_status": "ACTIVE",
        "source_file":      "report.csv",
        "file_exists":      True,
        "file_size_kb":     4,
        "file_type":        "csv",
    }

    # -----------------------------------------------------------------------
    # TEST 1: MATCH — world unchanged
    # -----------------------------------------------------------------------
    print("\n[TEST 1] MATCH -- World unchanged -> Should be MATCH")
    print("-" * 40)
    result = check_drift(make_wf(BASELINE_SNAPSHOT))
    assert result.verdict == "MATCH", f"Expected MATCH, got {result.verdict}"
    print_drift_result(result)
    print(f"  TEST 1 PASSED: {result.verdict}")

    # -----------------------------------------------------------------------
    # TEST 2: RECIPIENT DRIFT — change manager name in world
    # -----------------------------------------------------------------------
    print("\n[TEST 2] DRIFT -- Manager changed -> Should be DRIFT")
    print("-" * 40)
    world = load_world_raw()
    world["contacts"]["manager"]["name"] = "Priya Sharma"
    world["contacts"]["manager"]["email"] = "priya@company.local"
    save_world_raw(world)

    result = check_drift(make_wf(BASELINE_SNAPSHOT))
    assert result.verdict == "DRIFT", f"Expected DRIFT, got {result.verdict}"
    assert any(c.field == "recipient_name" for c in result.changes)
    print_drift_result(result)
    print(f"  TEST 2 PASSED: {result.verdict}, changes: {[c.field for c in result.changes]}")

    # Restore world
    world["contacts"]["manager"]["name"] = "Carol Singh"
    world["contacts"]["manager"]["email"] = "carol@company.local"
    save_world_raw(world)

    # -----------------------------------------------------------------------
    # TEST 3: FILE DRIFT — mark report.csv as not existing
    # -----------------------------------------------------------------------
    print("\n[TEST 3] DRIFT -- File missing -> Should be DRIFT")
    print("-" * 40)
    world = load_world_raw()
    world["files"]["report.csv"]["exists"] = False
    save_world_raw(world)

    result = check_drift(make_wf(BASELINE_SNAPSHOT))
    assert result.verdict == "DRIFT", f"Expected DRIFT, got {result.verdict}"
    assert any(c.field == "file_exists" for c in result.changes)
    print_drift_result(result)
    print(f"  TEST 3 PASSED: {result.verdict}, changes: {[c.field for c in result.changes]}")

    # Restore
    world["files"]["report.csv"]["exists"] = True
    save_world_raw(world)

    # -----------------------------------------------------------------------
    # TEST 4: UNKNOWN — no snapshot
    # -----------------------------------------------------------------------
    print("\n[TEST 4] UNKNOWN -- No snapshot saved -> Should be UNKNOWN")
    print("-" * 40)
    wf_no_snapshot = make_wf(snapshot=None)
    result = check_drift(wf_no_snapshot)
    assert result.verdict == "UNKNOWN", f"Expected UNKNOWN, got {result.verdict}"
    print_drift_result(result)
    print(f"  TEST 4 PASSED: {result.verdict}")

    # -----------------------------------------------------------------------
    # TEST 5: File size changed only -> Should be MATCH (not flagged)
    # -----------------------------------------------------------------------
    print("\n[TEST 5] MATCH -- Only file size changed -> Should be MATCH")
    print("-" * 40)
    world = load_world_raw()
    world["files"]["report.csv"]["size_kb"] = 90  # Size went from 4 to 90
    save_world_raw(world)

    result = check_drift(make_wf(BASELINE_SNAPSHOT))
    assert result.verdict == "MATCH", f"Expected MATCH (size change not flagged), got {result.verdict}"
    print_drift_result(result)
    print(f"  TEST 5 PASSED: {result.verdict} (file size ignored, as designed)")

    # Restore
    world["files"]["report.csv"]["size_kb"] = 4
    save_world_raw(world)

    # -----------------------------------------------------------------------
    # TEST 6: MULTIPLE CHANGES — manager changed + file gone
    # -----------------------------------------------------------------------
    print("\n[TEST 6] DRIFT -- Manager changed + file missing -> Should be DRIFT with 2+ changes")
    print("-" * 40)
    world = load_world_raw()
    world["contacts"]["manager"]["name"] = "Priya Sharma"
    world["contacts"]["manager"]["email"] = "priya@company.local"
    world["files"]["report.csv"]["exists"] = False
    save_world_raw(world)

    result = check_drift(make_wf(BASELINE_SNAPSHOT))
    assert result.verdict == "DRIFT", f"Expected DRIFT, got {result.verdict}"
    assert len(result.changes) >= 2, f"Expected 2+ changes, got {len(result.changes)}"
    print_drift_result(result)
    print(f"  TEST 6 PASSED: {result.verdict}, {len(result.changes)} change(s) detected")

    # Restore world fully
    world["contacts"]["manager"]["name"] = "Carol Singh"
    world["contacts"]["manager"]["email"] = "carol@company.local"
    world["files"]["report.csv"]["exists"] = True
    save_world_raw(world)

    print("\n" + "=" * 60)
    print("  All 6 drift tests complete.")
    print("=" * 60)
