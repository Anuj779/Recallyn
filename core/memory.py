# -*- coding: utf-8 -*-
"""
core/memory.py
==============
Workflow Storage — Save, Load, List, Delete.

CONCEPT: Persistence / Memory
---------------------------------------------------------------------------
Right now, everything in a Python program lives in RAM.
When the program ends, it's all gone.

"Persistence" means saving data to disk so it survives between
program runs. This is what the word "Memory" means in Recallis —
not RAM, but long-term storage, like a notebook.

WHY IS THIS IMPORTANT?
---------------------------------------------------------------------------
If Recallis can't remember workflows between sessions, the user
has to re-teach it every single time. That defeats the purpose.

HOW WE DO IT:
---------------------------------------------------------------------------
We store all workflows in a single JSON file: data/workflows.json

Format:
{
    "wf_weekly_report": { ...workflow data... },
    "wf_daily_backup":  { ...workflow data... }
}

The workflow ID is the key. This makes it fast to look up any
workflow by its ID.

ARCHITECTURE RULE: Memory only accepts validated Workflow objects.
Raw dicts or LLM text are NEVER written directly to disk.
---------------------------------------------------------------------------
"""

import sys
import io
import json
from pathlib import Path
from typing import Dict, List, Optional

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Import our validated schema types
from schema import Workflow, parse_workflow
from pydantic import ValidationError


# ===========================================================================
# CONFIGURATION — where the workflow file lives
# ===========================================================================

# Path to the workspace root (the folder containing core/ and data/)
# __file__ is the path of this file (core/memory.py)
# .parent      = core/
# .parent.parent = Recallis/ (the root)
ROOT_DIR = Path(__file__).parent.parent
WORKFLOWS_FILE = ROOT_DIR / "data" / "workflows.json"
DEMO_WORKFLOWS_FILE = ROOT_DIR / "data" / "demo_workflows.json"


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

def _load_raw() -> Dict[str, dict]:
    """
    Read the raw JSON files from disk and return them as a combined Python dict.
    """
    combined = {}
    
    # Load demo workflows first
    if DEMO_WORKFLOWS_FILE.exists():
        try:
            content = DEMO_WORKFLOWS_FILE.read_text(encoding="utf-8").strip()
            if content:
                demo_data = json.loads(content)
                for k, v in demo_data.items():
                    v["is_demo"] = True
                    combined[k] = v
        except Exception as e:
            print(f"Warning: Failed to load demo_workflows.json: {e}")
            
    # Load user workflows
    if WORKFLOWS_FILE.exists():
        try:
            content = WORKFLOWS_FILE.read_text(encoding="utf-8").strip()
            if content:
                user_data = json.loads(content)
                for k, v in user_data.items():
                    v["is_demo"] = False
                    combined[k] = v
        except Exception as e:
            print(f"Warning: Failed to load workflows.json: {e}")
            
    return combined


def _save_raw(data: Dict[str, dict]) -> None:
    """
    Write the raw JSON back to disk, preserving the separation.
    User workflows go to workflows.json, demo workflows are NOT saved back here (read-only for demo).
    """
    WORKFLOWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    user_data = {k: v for k, v in data.items() if not v.get("is_demo", False)}
    
    with open(WORKFLOWS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, indent=2)


# ===========================================================================
# PUBLIC API
# ===========================================================================

def save_workflow(workflow: Workflow) -> None:
    """
    Save a validated Workflow object to persistent storage.

    If a workflow with the same ID already exists, it is OVERWRITTEN.
    The caller is responsible for incrementing version numbers before
    calling this function.

    Args:
        workflow: A validated Workflow object (from schema.py).

    Raises:
        TypeError: If something other than a Workflow object is passed.
    """
    # SAFETY CHECK: Only accept proper Workflow objects, never raw dicts.
    if not isinstance(workflow, Workflow):
        raise TypeError(
            f"[Memory] save_workflow() only accepts a Workflow object. "
            f"Got: {type(workflow).__name__}"
        )

    all_workflows = _load_raw()
    # .model_dump() converts the Pydantic object back into a plain dict
    all_workflows[workflow.id] = workflow.model_dump()
    _save_raw(all_workflows)


def load_workflow(workflow_id: str) -> Optional[Workflow]:
    """
    Load a single workflow by its ID.

    Returns a validated Workflow object, or None if not found.

    Args:
        workflow_id: The unique ID of the workflow (e.g., "wf_weekly_report").

    Returns:
        A validated Workflow object, or None.
    """
    all_workflows = _load_raw()
    raw = all_workflows.get(workflow_id)

    if raw is None:
        return None

    # Re-validate on load. This protects against manual edits to the JSON
    # file that might have introduced invalid data.
    try:
        return parse_workflow(raw)
    except ValidationError as e:
        raise RuntimeError(
            f"[Memory] Workflow '{workflow_id}' in workflows.json is invalid.\n"
            f"  It may have been manually edited incorrectly.\n"
            f"  Validation error: {e}"
        )


def list_workflows() -> List[Workflow]:
    """
    Return all saved workflows as a list of validated Workflow objects.

    Returns an empty list if no workflows are saved yet.
    """
    all_workflows = _load_raw()
    result = []
    for wf_id, raw in all_workflows.items():
        try:
            result.append(parse_workflow(raw))
        except ValidationError as e:
            # Don't crash the whole list if one workflow is corrupt.
            # Warn and skip it.
            print(f"  [Memory] WARNING: Skipping corrupt workflow '{wf_id}': {e}")
    return result


def delete_workflow(workflow_id: str) -> bool:
    """
    Delete a workflow by its ID.

    Args:
        workflow_id: The ID of the workflow to delete.

    Returns:
        True if the workflow was found and deleted.
        False if no workflow with that ID existed.
    """
    all_workflows = _load_raw()

    if workflow_id not in all_workflows:
        return False

    del all_workflows[workflow_id]
    _save_raw(all_workflows)
    return True


def workflow_exists(workflow_id: str) -> bool:
    """Check if a workflow with the given ID exists in storage."""
    return workflow_id in _load_raw()


# ===========================================================================
# SELF-TEST
# Usage:  python core/memory.py
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  RECALLIS -- Memory (Save/Load) Test")
    print("=" * 60)

    # Use a test-only workflow ID so we don't pollute real data
    TEST_ID = "wf_memory_test"

    # -- CLEANUP: remove any leftover test data from a previous run --
    if workflow_exists(TEST_ID):
        delete_workflow(TEST_ID)
        print(f"  (Cleaned up leftover test workflow '{TEST_ID}')")

    # -----------------------------------------------------------------------
    # TEST 1: Save a workflow
    # -----------------------------------------------------------------------
    print("\n[TEST 1] Save a workflow -> Should write to disk")
    print("-" * 40)

    test_wf = Workflow(
        id=TEST_ID,
        goal="Test save and load in memory module",
        inputs={"source_file": "test.csv"},
        steps=[
            {"n": 1, "tool": "read_file", "args": {"path": "$source_file"}},
            {"n": 2, "tool": "summarize", "args": {"text": "$step1.content"}},
        ],
        version=1,
        confidence=0.95,
    )

    save_workflow(test_wf)
    print(f"  Saved workflow '{TEST_ID}' to {WORKFLOWS_FILE}")

    # -----------------------------------------------------------------------
    # TEST 2: Load it back and verify
    # -----------------------------------------------------------------------
    print("\n[TEST 2] Load the workflow back -> Should match original")
    print("-" * 40)

    loaded = load_workflow(TEST_ID)

    if loaded is None:
        print("  FAILED -- Workflow not found after saving!")
    else:
        assert loaded.id == test_wf.id, "ID mismatch!"
        assert loaded.goal == test_wf.goal, "Goal mismatch!"
        assert loaded.version == test_wf.version, "Version mismatch!"
        assert len(loaded.steps) == len(test_wf.steps), "Steps count mismatch!"
        print(f"  PASSED -- Loaded '{loaded.id}' successfully.")
        print(f"     Goal    : {loaded.goal}")
        print(f"     Steps   : {len(loaded.steps)}")
        print(f"     Version : {loaded.version}")

    # -----------------------------------------------------------------------
    # TEST 3: Load a non-existent workflow -> Should return None
    # -----------------------------------------------------------------------
    print("\n[TEST 3] Load non-existent ID -> Should return None")
    print("-" * 40)

    missing = load_workflow("wf_does_not_exist_xyz")
    if missing is None:
        print("  PASSED -- Returned None as expected.")
    else:
        print("  FAILED -- Should have returned None but got something!")

    # -----------------------------------------------------------------------
    # TEST 4: List all workflows
    # -----------------------------------------------------------------------
    print("\n[TEST 4] List all workflows -> Should include our test workflow")
    print("-" * 40)

    all_wfs = list_workflows()
    ids = [w.id for w in all_wfs]
    if TEST_ID in ids:
        print(f"  PASSED -- Found {len(all_wfs)} workflow(s) in storage: {ids}")
    else:
        print(f"  FAILED -- Test workflow not found in list: {ids}")

    # -----------------------------------------------------------------------
    # TEST 5: Delete the workflow
    # -----------------------------------------------------------------------
    print("\n[TEST 5] Delete the test workflow -> Should be gone")
    print("-" * 40)

    deleted = delete_workflow(TEST_ID)
    still_there = workflow_exists(TEST_ID)

    if deleted and not still_there:
        print(f"  PASSED -- Workflow '{TEST_ID}' deleted successfully.")
    else:
        print(f"  FAILED -- deleted={deleted}, still_there={still_there}")

    # -----------------------------------------------------------------------
    # TEST 6: Reject a raw dict (not a Workflow object)
    # -----------------------------------------------------------------------
    print("\n[TEST 6] Pass a raw dict to save_workflow -> Should FAIL")
    print("-" * 40)

    try:
        save_workflow({"id": "wf_raw", "goal": "this is not a Workflow object"})
        print("  FAILED -- Should have been rejected!")
    except TypeError:
        print(f"  CORRECTLY REJECTED -- TypeError raised as expected.")

    print("\n" + "=" * 60)
    print("  All memory tests complete.")
    print("=" * 60)
