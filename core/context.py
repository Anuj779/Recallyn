# -*- coding: utf-8 -*-
"""
core/context.py
===============
Context Intelligence — Build and capture environment snapshots.

CONCEPT: What is Context?
---------------------------------------------------------------------------
"Context" is the set of facts that matter for a specific workflow.

For the workflow "email the weekly report to the manager", the
context is:
  - Who is the manager RIGHT NOW?
  - Does report.csv still exist RIGHT NOW?

Context is NOT the entire computer. It is only the facts that
this specific workflow depends on.

CONCEPT: What is a Context Snapshot?
---------------------------------------------------------------------------
A snapshot is a "photo" of the context taken at a specific moment
in time — in our case, when the workflow was first taught.

When we teach Recallis:
  "Every Friday, email report.csv to my manager."

Recallis takes a snapshot:
  - manager_name = "Carol Singh"
  - manager_email = "carol@company.local"
  - manager_status = "ACTIVE"
  - file_exists (report.csv) = True

This snapshot is stored inside the workflow in workflows.json.

Later, when we want to run the workflow, we compare this old
snapshot against the CURRENT state of the world.

CONCEPT: The World
---------------------------------------------------------------------------
"The World" is our simplified model of the current environment.
In a real product this would query live systems.
For our demo, it reads from data/world.json.

Editing world.json = simulating what changed in the real world.
---------------------------------------------------------------------------
"""

import sys
import io
import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT_DIR = Path(__file__).parent.parent
WORLD_FILE = ROOT_DIR / "data" / "world.json"


# ===========================================================================
# WORLD ACCESS — read the current environment
# ===========================================================================

def load_world() -> Dict[str, Any]:
    """
    Load the current world state from data/world.json.

    This represents what is TRUE RIGHT NOW in the environment.
    In a real product this would call live APIs (LDAP, filesystem, etc.)
    For the demo we read from a JSON file that can be manually edited.

    Returns:
        A dictionary with 'contacts' and 'files' keys.

    Raises:
        RuntimeError: If world.json is missing or corrupted.
    """
    if not WORLD_FILE.exists():
        raise RuntimeError(
            f"[Context] world.json not found at {WORLD_FILE}.\n"
            "  This file defines the current environment for drift detection.\n"
            "  It should have been created during Phase 3 setup."
        )
    try:
        raw = WORLD_FILE.read_text(encoding="utf-8")
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"[Context] world.json is corrupted: {e}")


def get_contact(role: str) -> Optional[Dict[str, str]]:
    """
    Look up a contact in the current world by role (case-insensitive).

    Returns a dict with {name, email, status} or None if not found.
    """
    world = load_world()
    contacts = world.get("contacts", {})
    return contacts.get(role.strip().lower())


def get_file_info(filename: str) -> Optional[Dict[str, Any]]:
    """
    Look up a file's current status in the world.

    Returns a dict with {exists, size_kb, type} or None if not tracked.
    """
    world = load_world()
    files = world.get("files", {})
    name = Path(filename).name  # Strip any directory portion
    return files.get(name)


# ===========================================================================
# SNAPSHOT BUILDER
# ===========================================================================

def build_snapshot(workflow) -> Dict[str, Any]:
    """
    Build a context snapshot for a workflow by examining its inputs and steps,
    then looking up the relevant facts from the current world.

    This is called at TEACH time (not at run time).
    The snapshot records "what was true when this workflow was taught."

    What we capture:
        - For each input that looks like a file → check if it exists
        - For each input that looks like a role → look up the contact
        - The date the snapshot was taken

    Args:
        workflow: A validated Workflow object (from schema.py)

    Returns:
        A dictionary representing the context snapshot. Example:
        {
            "taught_on": "2026-08-30",
            "recipient_role": "manager",
            "recipient_name": "Carol Singh",
            "recipient_email": "carol@company.local",
            "recipient_status": "ACTIVE",
            "source_file": "report.csv",
            "file_exists": True,
            "file_size_kb": 4
        }
    """
    snapshot: Dict[str, Any] = {
        "taught_on": date.today().isoformat(),
    }

    inputs = workflow.inputs or {}

    # -----------------------------------------------------------------------
    # Build a unified scan dict: inputs + all step args (flattened)
    # We scan both so we capture things like lookup_contact(role="manager")
    # even if "manager" isn't listed in the workflow's top-level inputs.
    # -----------------------------------------------------------------------
    scan_dict = dict(inputs)  # Start with inputs

    # Add step args, prefixed with the tool name to avoid key collisions
    for step in workflow.steps:
        for k, v in (step.args or {}).items():
            # Skip variable references (they start with $) — resolve those at runtime
            if isinstance(v, str) and v.startswith("$"):
                continue
            # Use "step{n}_{tool}_{key}" as the key
            composite_key = f"{k}"  # Just use the arg key — duplicates get overwritten (OK)
            if composite_key not in scan_dict:
                scan_dict[composite_key] = v

    # -----------------------------------------------------------------------
    # Scan the combined dict for recognizable patterns
    # -----------------------------------------------------------------------
    for key, value in scan_dict.items():
        key_lower = key.lower()
        value_str = str(value).lower() if value else ""

        # Pattern 1: Looks like a file reference (key contains "file" or "path",
        # or value ends with a known extension)
        is_file_key = any(w in key_lower for w in ("file", "path", "csv", "report", "document"))
        is_file_value = any(value_str.endswith(ext) for ext in (".csv", ".txt", ".json", ".pdf", ".xlsx"))

        if is_file_key or is_file_value:
            filename = str(value)
            file_info = get_file_info(filename)
            snapshot[f"source_file"] = filename
            if file_info:
                snapshot["file_exists"]   = file_info.get("exists", False)
                snapshot["file_size_kb"]  = file_info.get("size_kb", 0)
                snapshot["file_type"]     = file_info.get("type", "unknown")
            else:
                # File not tracked in world — we record that we don't know
                snapshot["file_exists"] = None  # None = UNKNOWN

        # Pattern 2: Looks like a role/recipient reference
        is_role_key = any(w in key_lower for w in ("role", "recipient", "contact", "manager", "to"))

        if is_role_key:
            role = str(value)
            contact = get_contact(role)
            snapshot["recipient_role"] = role
            if contact:
                snapshot["recipient_name"]   = contact.get("name")
                snapshot["recipient_email"]  = contact.get("email")
                snapshot["recipient_status"] = contact.get("status", "UNKNOWN")
            else:
                # Role not in world — record as unknown
                snapshot["recipient_name"]   = None
                snapshot["recipient_email"]  = None
                snapshot["recipient_status"] = "UNKNOWN"

    return snapshot


def build_current_context(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a previously saved snapshot, rebuild the SAME fields using
    the CURRENT world state.

    This is called at RUN time to get the "current photo" to compare
    against the "old photo" (the saved snapshot).

    We only look up the same fields that are in the snapshot, so we
    compare apples to apples.

    Args:
        snapshot: The saved context_snapshot from the workflow.

    Returns:
        A new dictionary with the same structure as the snapshot,
        but populated with current world values.
    """
    current: Dict[str, Any] = {
        "taught_on": snapshot.get("taught_on"),  # Same — date doesn't drift
    }

    # Re-resolve recipient if snapshot captured one
    if "recipient_role" in snapshot:
        role = snapshot["recipient_role"]
        contact = get_contact(role)
        current["recipient_role"] = role
        if contact:
            current["recipient_name"]   = contact.get("name")
            current["recipient_email"]  = contact.get("email")
            current["recipient_status"] = contact.get("status", "UNKNOWN")
        else:
            current["recipient_name"]   = None
            current["recipient_email"]  = None
            current["recipient_status"] = "UNKNOWN"

    # Re-resolve file if snapshot captured one
    if "source_file" in snapshot:
        filename = snapshot["source_file"]
        file_info = get_file_info(filename)
        current["source_file"] = filename
        if file_info:
            current["file_exists"]  = file_info.get("exists", False)
            current["file_size_kb"] = file_info.get("size_kb", 0)
            current["file_type"]    = file_info.get("type", "unknown")
        else:
            current["file_exists"]  = None
            current["file_size_kb"] = None
            current["file_type"]    = None

    return current


# ===========================================================================
# SELF-TEST — Run: python core/context.py
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  RECALLIS -- Context Module Test")
    print("=" * 60)

    # Import here to avoid circular import at module level
    sys.path.insert(0, os.path.dirname(__file__))
    from schema import Workflow

    # -----------------------------------------------------------------------
    # TEST 1: Load the world
    # -----------------------------------------------------------------------
    print("\n[TEST 1] Load world.json")
    print("-" * 40)
    try:
        world = load_world()
        contacts = world.get("contacts", {})
        files = world.get("files", {})
        print(f"  Contacts : {list(contacts.keys())}")
        print(f"  Files    : {list(files.keys())}")
        print(f"  PASSED")
    except Exception as e:
        print(f"  FAILED: {e}")

    # -----------------------------------------------------------------------
    # TEST 2: Build a snapshot for wf_weekly_report
    # -----------------------------------------------------------------------
    print("\n[TEST 2] Build snapshot for weekly report workflow")
    print("-" * 40)

    test_wf = Workflow(
        id="wf_context_test",
        goal="Read report.csv and email manager",
        inputs={
            "source_file":    "report.csv",
            "recipient_role": "manager",
        },
        steps=[
            {"n": 1, "tool": "read_file",  "args": {"path": "$source_file"}},
            {"n": 2, "tool": "send_email", "args": {
                "to": "$step1.content", "subject": "Report", "body": "test"
            }},
        ],
        version=1,
        confidence=0.9,
    )

    snapshot = build_snapshot(test_wf)
    print(f"  Snapshot:")
    for k, v in snapshot.items():
        print(f"    {k}: {v}")
    assert "recipient_name" in snapshot, "Should have captured recipient"
    assert "source_file" in snapshot, "Should have captured file"
    assert "taught_on" in snapshot, "Should have captured date"
    print(f"  PASSED")

    # -----------------------------------------------------------------------
    # TEST 3: Build current context from that snapshot
    # -----------------------------------------------------------------------
    print("\n[TEST 3] Build current context from snapshot")
    print("-" * 40)
    current = build_current_context(snapshot)
    print(f"  Current context:")
    for k, v in current.items():
        print(f"    {k}: {v}")
    assert current["recipient_name"] == snapshot["recipient_name"], "Should match (world unchanged)"
    print(f"  PASSED - Context matches snapshot (world unchanged)")

    # -----------------------------------------------------------------------
    # TEST 4: Contact lookup
    # -----------------------------------------------------------------------
    print("\n[TEST 4] Direct contact lookup")
    print("-" * 40)
    c = get_contact("manager")
    assert c is not None
    print(f"  Manager: {c}")
    none_c = get_contact("janitor")
    assert none_c is None
    print(f"  Janitor: {none_c} (correctly None)")
    print(f"  PASSED")

    print("\n" + "=" * 60)
    print("  All context tests complete.")
    print("=" * 60)
