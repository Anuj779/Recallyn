# -*- coding: utf-8 -*-
"""
core/agent.py
=============
The Workflow Execution Agent — Phase 2.

CONCEPT: What is an Agent?
---------------------------------------------------------------------------
An agent is a controller that:
  1. Observes the current state ("what step am I on?")
  2. Decides what to do next ("run step 2: summarize")
  3. Acts (calls the tool)
  4. Receives the result
  5. Updates its state ("step 2 done, store result")
  6. Repeats until finished or something goes wrong

Think of it like a kitchen chef following a recipe:
  - The RECIPE = the saved workflow (what steps to do)
  - The CHEF   = the agent (who actually does them)
  - The TOOLS  = knives, oven, pan (the Python tool functions)
  - The NOTES  = execution state (tracking what was done)

IMPORTANT DISTINCTION:
  - A CHATBOT responds to messages. It has no persistent task.
  - An AGENT works through a multi-step task, remembers intermediate
    results, and decides what to do next each iteration.

CONCEPT: What is State?
---------------------------------------------------------------------------
State is the agent's memory DURING a run. It answers:
  - Which workflow am I running?
  - What step am I currently on?
  - What did the previous steps return?
  - Did anything go wrong?
  - Am I done?

We keep state as a simple Python dataclass.
After the workflow finishes, the state contains the full history
of what happened — every step's result is stored.

CONCEPT: Variable Resolution
---------------------------------------------------------------------------
Workflow steps reference variables like:
    "$source_file"   → from workflow.inputs
    "$step1.content" → from the result of step 1

BEFORE calling a tool, we scan every argument value.
If the value starts with "$", we replace it with the real value.

Example:
    args = {"text": "$step1.content"}
    step1 result = {"content": "Name,Age,..."}
    resolved = {"text": "Name,Age,..."}

Only THEN do we call the tool.

CONCEPT: The Agent Loop
---------------------------------------------------------------------------
    LOAD workflow from memory
          ↓
    INIT state (status=READY)
          ↓
    FOR EACH step:
      ├── Is tool registered?   NO  → FAILED, STOP
      ├── Resolve $variables    ERR → FAILED, STOP
      ├── Call tool function
      ├── Store result
      └── Tool failed?          YES → FAILED, STOP
          ↓
    ALL DONE → COMPLETED

ARCHITECTURE RULE:
  The agent does NOT call the LLM.
  The workflow already specifies what to do.
  The agent just executes it deterministically.
---------------------------------------------------------------------------
"""

import re
import sys
import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ---- Imports from sibling modules ----
# memory.py: load_workflow()
# schema.py: Workflow object
# tools.py:  get_tool(), list_tools()
import os
sys.path.insert(0, os.path.dirname(__file__))

from memory import load_workflow
from tools import get_tool, list_tools
from schema import Workflow

# --- Phase 4 Imports ---
from decide import evaluate, print_decision_result, Decision
from provenance import classify_workflow_step


# ===========================================================================
# EXECUTION STATE
# ===========================================================================

@dataclass
class ExecutionState:
    """
    The agent's notebook during a workflow run.

    Tracks everything that happens so the agent (and user) can see
    exactly what happened, even after a failure.

    Fields:
        workflow_id  : ID of the workflow being executed.
        total_steps  : Total number of steps in the workflow.
        current_step : Which step is currently executing (1-indexed).
        status       : One of: READY, RUNNING, COMPLETED, FAILED, STOPPED
        results      : Dict mapping "step1" → tool result dict
        errors       : List of error strings collected during execution
        completed_steps: List of step numbers that finished successfully
    """
    workflow_id:      str
    total_steps:      int
    current_step:     int                    = 0
    status:           str                    = "READY"
    results:          Dict[str, Any]         = field(default_factory=dict)
    errors:           List[str]              = field(default_factory=list)
    completed_steps:  List[int]              = field(default_factory=list)


# ===========================================================================
# VARIABLE RESOLUTION
# ===========================================================================

def resolve_args(
    args: Dict[str, Any],
    inputs: Dict[str, Any],
    results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Replace all $variable references in step args with real values, supporting nested dicts, lists, and string interpolation.
    """
    def _resolve(val):
        if isinstance(val, dict):
            return {k: _resolve(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_resolve(v) for v in val]
        elif isinstance(val, str):
            # If the string is EXACTLY a single variable, return the raw object (could be list/dict)
            exact_match = re.fullmatch(r'\$([a-zA-Z0-9_.]+)|\$\{([a-zA-Z0-9_.]+)\}', val)
            if exact_match:
                ref = exact_match.group(1) or exact_match.group(2)
                if ref.startswith("step") and "." in ref:
                    parts = ref.split(".", 1)
                    step_key, field_name = parts[0], parts[1]
                    if step_key not in results: raise KeyError(f"Variable refers to '{step_key}' but it has not completed.")
                    if not results[step_key].get("success"): raise KeyError(f"Variable refers to '{step_key}' but that step failed.")
                    if field_name not in results[step_key].get("data", {}): raise KeyError(f"Variable '{ref}': step '{step_key}' has no field '{field_name}'.")
                    return results[step_key]["data"][field_name]
                else:
                    if ref not in inputs: raise KeyError(f"Variable '{ref}' not found in inputs.")
                    return inputs[ref]

            # Otherwise, do string interpolation
            def repl(match):
                ref = match.group(1) or match.group(2)
                if ref.startswith("step") and "." in ref:
                    parts = ref.split(".", 1)
                    step_key, field_name = parts[0], parts[1]
                    if step_key not in results: raise KeyError(f"Missing {step_key}")
                    if not results[step_key].get("success"): raise KeyError(f"Failed {step_key}")
                    if field_name not in results[step_key].get("data", {}): raise KeyError(f"Missing {field_name} in {step_key}")
                    return str(results[step_key]["data"][field_name])
                else:
                    if ref not in inputs: raise KeyError(f"Missing {ref}")
                    return str(inputs[ref])
            return re.sub(r'\$([a-zA-Z0-9_.]+)|\$\{([a-zA-Z0-9_.]+)\}', repl, val)
        else:
            return val

    resolved = {}
    for k, v in args.items():
        resolved[k] = _resolve(v)
    return resolved


# ===========================================================================
# PROGRESS DISPLAY
# ===========================================================================

def _print_step_start(step_n: int, total: int, tool_name: str, args: dict) -> None:
    """Print the step header before execution."""
    print(f"\n  [{step_n}/{total}] {tool_name}")
    for k, v in args.items():
        # Truncate long values for display
        display_v = str(v)
        if len(display_v) > 60:
            display_v = display_v[:57] + "..."
        print(f"         {k} = {display_v}")


def _print_step_result(success: bool, data: Optional[dict], error: Optional[str]) -> None:
    """Print the result after a step executes."""
    if success:
        print(f"         OK")
        # Print a brief summary of what the tool returned
        if data:
            for k, v in data.items():
                display_v = str(v)
                if len(display_v) > 70:
                    display_v = display_v[:67] + "..."
                print(f"         -> {k}: {display_v}")
    else:
        print(f"         FAILED: {error}")


def _print_workflow_header(workflow: Workflow) -> None:
    print()
    print("=" * 60)
    print(f"  Recallyn Agent -- Running Workflow")
    print("=" * 60)
    print(f"  ID    : {workflow.id}")
    print(f"  Goal  : {workflow.goal}")
    print(f"  Steps : {workflow.total_steps if hasattr(workflow, 'total_steps') else len(workflow.steps)}")
    print()


def _print_completion(state: ExecutionState) -> None:
    print()
    print("=" * 60)
    if state.status == "COMPLETED":
        print(f"  Workflow COMPLETED successfully!")
        print(f"  All {state.total_steps} step(s) executed.")
    elif state.status == "CANCELLED":
        print(f"  Workflow CANCELLED.")
        print(f"  Completed {len(state.completed_steps)}/{state.total_steps} step(s).")
        if state.errors:
            print(f"  Errors:")
            for err in state.errors:
                print(f"    - {err}")
    else:
        print(f"  Workflow FAILED.")
        print(f"  Completed {len(state.completed_steps)}/{state.total_steps} step(s).")
        if state.errors:
            print(f"  Errors:")
            for err in state.errors:
                print(f"    - {err}")
    print("=" * 60)
    print()


# ===========================================================================
# THE AGENT LOOP
# ===========================================================================

def run_workflow(workflow_id: str) -> ExecutionState:
    """
    Load a saved workflow and execute every step in order.

    This IS the agent. It drives the entire execution from start to finish.

    Flow:
        1. Load the workflow from memory.
        2. Initialize ExecutionState.
        3. For each step:
           a. Validate tool name is in TOOL_REGISTRY.
           b. Resolve $variable arguments.
           c. Call the tool function.
           d. Store the result.
           e. If tool failed → mark FAILED, stop.
        4. After all steps → mark COMPLETED.

    Args:
        workflow_id: The ID of a saved workflow (from memory.py).

    Returns:
        The final ExecutionState (always returned, even on failure).
        The caller can inspect state.status, state.results, state.errors.
    """

    # ------------------------------------------------------------------
    # STEP 1: Load workflow from persistent memory
    # ------------------------------------------------------------------
    workflow = load_workflow(workflow_id)

    if workflow is None:
        # Can't even start — no such workflow
        state = ExecutionState(
            workflow_id=workflow_id,
            total_steps=0,
            status="FAILED"
        )
        state.errors.append(f"Workflow '{workflow_id}' not found in memory.")
        print(f"\n  ERROR: Workflow '{workflow_id}' not found.")
        return state

    # ------------------------------------------------------------------
    # STEP 2: Initialize execution state
    # ------------------------------------------------------------------
    state = ExecutionState(
        workflow_id=workflow.id,
        total_steps=len(workflow.steps),
        status="READY",
    )

    _print_workflow_header(workflow)

    # ------------------------------------------------------------------
    # STEP 2.5: PREFLIGHT CHECK (Phase 6 Unified Gate)
    # ------------------------------------------------------------------
    from preflight import run_preflight, print_preflight_report
    report = run_preflight(workflow)
    print_preflight_report(report)
    
    if not report.can_proceed:
        state.status = "FAILED"
        state.errors.append("Workflow failed preflight checks.")
        # Need to implement _print_completion if not called, or just print
        print("\n  ❌ PREFLIGHT FAILED. Aborting execution.")
        return state

    drift_result = report.drift_result
    context_verdict = drift_result.verdict
    
    if drift_result.verdict == "DRIFT" and drift_result.changes:
        # Dependency check
        affected_tools = set()
        for c in drift_result.changes:
            if c.severity in ["HIGH", "CRITICAL"]:
                if "recipient" in c.field:
                    affected_tools.update(["lookup_contact", "send_email"])
                elif "file" in c.field:
                    affected_tools.update(["read_file", "write_file", "delete_file", "summarize"])
                    
        workflow_tools = {step.tool for step in workflow.steps}
        if affected_tools.intersection(workflow_tools):
            print("\n  ⚠️ CONTEXT CHANGED")
            
            for c in drift_result.changes:
                if c.severity in ["HIGH", "CRITICAL"]:
                    print(f"\n  Remembered:")
                    print(f"  {c.field} = {c.old_value}")
                    print(f"\n  Current:")
                    print(f"  {c.field} = {c.new_value}")
                    print(f"\n  Suggested fix:")
                    print(f"  Use '{c.new_value}' as {c.field}?")
                    
            ans = input("\n  [Approve] or [Cancel] (y/n): ").strip().lower()
            if ans != 'y':
                state.status = "CANCELLED"
                state.errors.append("Cancelled by user at pre-execution context gate.")
                _print_completion(state)
                return state
                
            # Runtime resolution approved -> treat as MATCH for the execution rules downstream
            context_verdict = "MATCH"
            print("  -> Context correction approved. Continuing execution...")

    # ------------------------------------------------------------------
    # STEP 3: The Agent Loop — execute each step
    # ------------------------------------------------------------------
    state.status = "RUNNING"

    for step in workflow.steps:
        state.current_step = step.n
        step_key = f"step{step.n}"

        # ---- 3a. Validate tool name is registered ----
        tool_fn = get_tool(step.tool)
        if tool_fn is None:
            error_msg = (
                f"Step {step.n}: Unknown tool '{step.tool}'.\n"
                f"  Registered tools: {list_tools()}\n"
                f"  Only registered tools may execute. Stopping safely."
            )
            state.errors.append(error_msg)
            state.status = "FAILED"
            print(f"\n  [{step.n}/{state.total_steps}] {step.tool}")
            print(f"         BLOCKED: Tool '{step.tool}' is not registered.")
            break

        # ---- 3b. Resolve $variable arguments ----
        try:
            resolved = resolve_args(step.args, workflow.inputs, state.results)
        except KeyError as e:
            error_msg = f"Step {step.n} ({step.tool}): Variable resolution failed. {e}"
            state.errors.append(error_msg)
            state.status = "FAILED"
            print(f"\n  [{step.n}/{state.total_steps}] {step.tool}")
            print(f"         FAILED: {e}")
            break

        # ---- 3c. Display step start ----
        _print_step_start(step.n, state.total_steps, step.tool, resolved)

        # ---- PHASE 4: TRUST + RISK + PERMISSION CHECK ----
        source = classify_workflow_step(workflow.id)
        
        decision_result = evaluate(
            tool_name=step.tool,
            source=source,
            context_verdict=context_verdict,
            workflow=workflow,
            args=resolved
        )
        
        # Only print the decision if it's not a basic EXECUTE, to avoid UI spam,
        # OR if it's blocked/asking.
        if decision_result.decision != Decision.EXECUTE:
            print_decision_result(decision_result)
            
        if decision_result.decision == Decision.BLOCK:
            error_msg = f"Step {step.n} ({step.tool}) BLOCKED: {decision_result.reason}"
            state.errors.append(error_msg)
            state.status = "FAILED"
            break
            
        elif decision_result.decision == Decision.ASK:
            print(f"\n  ⚠️ ACTION REQUIRES APPROVAL")
            print(f"  Tool: {step.tool}")
            print(f"  Reason: {decision_result.reason}")
            ans = input("  Approve execution? [y/N]: ").strip().lower()
            if ans != 'y':
                error_msg = f"Step {step.n} ({step.tool}) CANCELLED by user."
                state.errors.append(error_msg)
                state.status = "FAILED"
                print(f"  -> Cancelled.")
                break
            print(f"  -> Approved. Executing...")

        # ---- 3d. Call the tool ----
        try:
            result = tool_fn(**resolved)
        except TypeError as e:
            # Wrong arguments passed to the tool function
            error_msg = (
                f"Step {step.n} ({step.tool}): "
                f"Wrong arguments passed to tool. {e}"
            )
            state.errors.append(error_msg)
            state.status = "FAILED"
            print(f"         FAILED: Wrong arguments -- {e}")
            break
        except Exception as e:
            # Unexpected tool crash
            error_msg = f"Step {step.n} ({step.tool}): Unexpected error -- {e}"
            state.errors.append(error_msg)
            state.status = "FAILED"
            print(f"         FAILED: Unexpected error -- {e}")
            break

        # ---- 3e. Display and store result ----
        _print_step_result(result["success"], result.get("data"), result.get("error"))
        state.results[step_key] = result

        # ---- 3f. If tool failed → stop ----
        if not result["success"]:
            error_msg = f"Step {step.n} ({step.tool}): {result.get('error', 'Unknown error')}"
            state.errors.append(error_msg)
            state.status = "FAILED"
            break

        # ---- 3g. Step succeeded → record and continue ----
        state.completed_steps.append(step.n)

    else:
        # The for loop completed without hitting a break → all steps succeeded
        state.status = "COMPLETED"

    from recovery import classify_failure, attempt_recovery
    from verifier import verify_postconditions, VerificationStatus
    from evolution import create_new_version, propose_memory_update
    from memory import save_workflow

    # ------------------------------------------------------------------
    # STEP 4: Tool-Level Failure Recovery Loop
    # ------------------------------------------------------------------
    # If the workflow broke early due to a tool failure, we try to classify and recover.
    if state.status == "FAILED" and state.errors:
        err_msg = state.errors[-1]
        fail_type = classify_failure(err_msg)
        
        print(f"\n  [PHASE 5] Failure Detected: {fail_type}")
        can_recover, rec_msg = attempt_recovery(fail_type, state)
        print(f"  Recovery check: {rec_msg}")
        
        # In a full implementation we would loop back and retry the step.
        # For the hackathon MVP, if it's transient, we could loop, but for now we just log it and stop.
        # Let's just print the recovery decision. 
        if can_recover:
            print("  (Auto-retry would happen here...)")

    # ------------------------------------------------------------------
    # STEP 5: Postcondition Verification
    # ------------------------------------------------------------------
    if state.status == "COMPLETED" and hasattr(workflow, "postconditions") and workflow.postconditions:
        print("\n  [PHASE 5] Verifying Workflow Outcomes...")
        
        # Resolve variables in postconditions
        resolved_pcs = []
        for pc in workflow.postconditions:
            try:
                resolved_expect = resolve_args(pc.get("expect", {}), workflow.inputs, state.results)
                resolved_pcs.append({
                    "check": pc.get("check"),
                    "expect": resolved_expect
                })
            except Exception as e:
                state.status = "FAILED"
                state.errors.append(f"Failed to resolve postcondition variables: {e}")
                print(f"  ❌ FAILED: Could not resolve postcondition variables.")
                break
                
        if state.status == "COMPLETED":
            v_status, v_details = verify_postconditions(resolved_pcs)
            
            for d in v_details:
                print(f"    - {d}")
                
            if v_status == VerificationStatus.VERIFIED:
                print("  ✅ VERIFIED: All postconditions met.")
            else:
                print("  ❌ VERIFICATION FAILED: Workflow did not achieve intended outcome.")
                state.status = "FAILED"
                state.errors.append("Postcondition verification failed.")
                
                fail_type = classify_failure("verification failed")
                can_recover, rec_msg = attempt_recovery(fail_type, state)
                print(f"\n  [PHASE 5] Recovery check: {rec_msg}")

    # ------------------------------------------------------------------
    # STEP 6: Safe Memory Evolution
    # ------------------------------------------------------------------
    if state.status == "COMPLETED" and drift_result.verdict == "DRIFT" and drift_result.changes:
        # If we successfully completed the workflow AND the user had approved context drift,
        # we can propose evolving the workflow permanently.
        proposal = propose_memory_update(drift_result.changes)
        if proposal:
            print("\n  [PHASE 5] Safe Memory Evolution")
            print(f"  Proposed update: {proposal}")
            ans = input("  Would you like to permanently update this workflow? [y/N]: ").strip().lower()
            if ans == 'y':
                reason = f"User approved context updates: {proposal}"
                
                # We need to find the specific inputs that changed to apply them.
                # Since the Pre-Execution Gate only gave us `drift_result.changes`, we can apply them directly.
                apply_changes = {}
                for c in drift_result.changes:
                    # In a real system, c.field maps directly to an input or context key.
                    # For simplicity, if it matches an input, update it.
                    if c.field in workflow.inputs:
                        apply_changes[c.field] = c.new_value
                
                workflow = create_new_version(workflow, reason, apply_changes)
                save_workflow(workflow)
                print(f"  ✅ Workflow updated to version {workflow.version}.")

    # ------------------------------------------------------------------
    # STEP 7: Print final summary
    # ------------------------------------------------------------------
    _print_completion(state)
    return state


# ===========================================================================
# SELF-TEST — Run: python core/agent.py
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  RECALLIS -- Agent Execution Test")
    print("=" * 60)

    # We need at least one real workflow in memory to test.
    # We'll create a temporary one for testing purposes.
    from memory import save_workflow, delete_workflow
    from schema import Workflow

    # -----------------------------------------------------------------------
    # TEST 1: Normal execution — all 4 steps should complete
    # -----------------------------------------------------------------------
    print("\n[TEST 1] Normal 4-step workflow -> Should COMPLETE")
    print("-" * 40)

    normal_wf = Workflow(
        id="wf_agent_test_normal",
        goal="Read a file, summarize it, find HR contact, and email them",
        inputs={
            "source_file": "report.csv",
            "recipient_role": "hr"
        },
        steps=[
            {"n": 1, "tool": "read_file",     "args": {"path": "$source_file"}},
            {"n": 2, "tool": "summarize",      "args": {"text": "$step1.content"}},
            {"n": 3, "tool": "lookup_contact", "args": {"role": "$recipient_role"}},
            {"n": 4, "tool": "send_email",     "args": {
                "to":      "$step3.email",
                "subject": "Weekly Report Summary",
                "body":    "$step2.summary"
            }},
        ],
        version=1,
        confidence=0.95,
    )
    save_workflow(normal_wf)

    state = run_workflow("wf_agent_test_normal")
    assert state.status == "COMPLETED", f"Expected COMPLETED, got {state.status}"
    assert len(state.completed_steps) == 4
    print(f"  TEST 1 RESULT: {state.status} -- {len(state.completed_steps)}/4 steps done")

    # -----------------------------------------------------------------------
    # TEST 2: Missing file — step 1 should FAIL
    # -----------------------------------------------------------------------
    print("\n[TEST 2] Missing file -> Should FAIL at step 1")
    print("-" * 40)

    missing_file_wf = Workflow(
        id="wf_agent_test_missing_file",
        goal="Read a file that does not exist",
        inputs={"source_file": "does_not_exist.csv"},
        steps=[
            {"n": 1, "tool": "read_file", "args": {"path": "$source_file"}},
            {"n": 2, "tool": "summarize",  "args": {"text": "$step1.content"}},
        ],
        version=1,
        confidence=0.9,
    )
    save_workflow(missing_file_wf)

    state = run_workflow("wf_agent_test_missing_file")
    assert state.status == "FAILED", f"Expected FAILED, got {state.status}"
    assert len(state.completed_steps) == 0, "No steps should have completed"
    print(f"  TEST 2 RESULT: {state.status} -- {len(state.completed_steps)}/2 steps done")

    # -----------------------------------------------------------------------
    # TEST 3: Unknown tool — should FAIL immediately
    # -----------------------------------------------------------------------
    print("\n[TEST 3] Unknown tool 'hack_system' -> Should FAIL immediately")
    print("-" * 40)

    unknown_tool_wf = Workflow(
        id="wf_agent_test_unknown_tool",
        goal="Test what happens when an unknown tool appears in a workflow",
        inputs={},
        steps=[
            {"n": 1, "tool": "hack_system", "args": {"target": "database"}},
        ],
        version=1,
        confidence=0.5,
    )
    save_workflow(unknown_tool_wf)

    state = run_workflow("wf_agent_test_unknown_tool")
    assert state.status == "FAILED", f"Expected FAILED, got {state.status}"
    print(f"  TEST 3 RESULT: {state.status} -- Tool correctly blocked")

    # -----------------------------------------------------------------------
    # TEST 4: Missing variable — should FAIL at resolve stage
    # -----------------------------------------------------------------------
    print("\n[TEST 4] Missing $variable -> Should FAIL at resolution")
    print("-" * 40)

    missing_var_wf = Workflow(
        id="wf_agent_test_missing_var",
        goal="Test missing variable resolution",
        inputs={},  # Inputs is EMPTY — so $source_file will fail to resolve
        steps=[
            {"n": 1, "tool": "read_file", "args": {"path": "$source_file"}},
        ],
        version=1,
        confidence=0.5,
    )
    save_workflow(missing_var_wf)

    state = run_workflow("wf_agent_test_missing_var")
    assert state.status == "FAILED", f"Expected FAILED, got {state.status}"
    print(f"  TEST 4 RESULT: {state.status} -- Missing variable caught correctly")

    # -----------------------------------------------------------------------
    # TEST 5: Failure in middle step — steps 1 visible, step 2 fails
    # -----------------------------------------------------------------------
    print("\n[TEST 5] Failure at step 2 -> Steps 1 complete, FAILED at step 2")
    print("-" * 40)

    mid_fail_wf = Workflow(
        id="wf_agent_test_mid_fail",
        goal="Read a file OK, then fail on lookup of unknown contact",
        inputs={
            "source_file":    "report.csv",
            "recipient_role": "janitor"       # Not in MOCK_CONTACTS
        },
        steps=[
            {"n": 1, "tool": "read_file",     "args": {"path": "$source_file"}},
            {"n": 2, "tool": "summarize",      "args": {"text": "$step1.content"}},
            {"n": 3, "tool": "lookup_contact", "args": {"role": "$recipient_role"}},
            {"n": 4, "tool": "send_email",     "args": {
                "to":      "$step3.email",
                "subject": "Report",
                "body":    "$step2.summary"
            }},
        ],
        version=1,
        confidence=0.7,
    )
    save_workflow(mid_fail_wf)

    state = run_workflow("wf_agent_test_mid_fail")
    assert state.status == "FAILED", f"Expected FAILED, got {state.status}"
    assert 1 in state.completed_steps, "Step 1 (read_file) should have succeeded"
    assert 2 in state.completed_steps, "Step 2 (summarize) should have succeeded"
    assert 3 not in state.completed_steps, "Step 3 (lookup_contact) should have failed"
    print(f"  TEST 5 RESULT: {state.status} -- Completed {state.completed_steps} of 4 steps")
    print(f"                Step 3 failed as expected: {state.errors}")

    # -----------------------------------------------------------------------
    # Cleanup test workflows
    # -----------------------------------------------------------------------
    for test_id in [
        "wf_agent_test_normal", "wf_agent_test_missing_file",
        "wf_agent_test_unknown_tool", "wf_agent_test_missing_var",
        "wf_agent_test_mid_fail"
    ]:
        delete_workflow(test_id)

    print("\n" + "=" * 60)
    print("  All 5 agent tests complete.")
    print("=" * 60)
