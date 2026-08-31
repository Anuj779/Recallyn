# -*- coding: utf-8 -*-
"""
core/permissions.py
===================
Workflow Permission Checker — Capability Authorization.

CONCEPT: What are Permissions?
---------------------------------------------------------------------------
A permission system answers: "Is this workflow ALLOWED to use this tool?"

Even if a tool is safe and the source is trusted, a workflow should
only be able to call the tools it was originally designed to use.

Example:

    Workflow "Weekly Report":
        Allowed tools: read_file, summarize, lookup_contact, send_email

    If the agent tries to run:
        delete_file("important_data.csv")

    Even if the risk engine says HIGH (not CRITICAL), the permission
    system BLOCKS it because delete_file is not in the allowed set.

WHY PERMISSIONS?
---------------------------------------------------------------------------
Permissions enforce the PRINCIPLE OF LEAST PRIVILEGE:

    "A workflow should only have access to the minimum set of
     capabilities required to complete its intended task."

This is a standard security principle used everywhere:
  - Operating systems (user cannot write to system32)
  - Cloud services (IAM roles grant specific capabilities)
  - Mobile apps (camera permission must be explicitly granted)

Recallyn applies this same idea to workflow tool access.

HOW WE IMPLEMENT IT:
---------------------------------------------------------------------------
We add an optional "allowed_tools" list to each workflow.
If the list is present: only listed tools may execute.
If the list is absent: we use the Phase 2 tool registry as the default.

This keeps Phase 2 workflows working without requiring migration.
New workflows taught in Phase 4+ automatically get permissions set.

DESIGN PRINCIPLE:
    If allowed_tools is missing → use default (all Phase 2 tools).
    If allowed_tools is present → only those tools may run.
    Unknown tool not in registry → BLOCK regardless of permissions.
---------------------------------------------------------------------------
"""

import sys
import io
import os
from typing import List

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))
from tools import list_tools  # Phase 2 tool registry


# ===========================================================================
# DEFAULT PERMISSIONS
# ===========================================================================

# The full set of registered Phase 2 tools.
# Workflows without an explicit allowed_tools list get these defaults.
# This ensures backward compatibility — Phase 2 workflows run as-is.
DEFAULT_ALLOWED_TOOLS: List[str] = list_tools()


# ===========================================================================
# SCHEMA EXTENSION — get_allowed_tools
# ===========================================================================

def get_allowed_tools(workflow) -> List[str]:
    """
    Get the set of tools this workflow is allowed to use.

    Priority:
        1. If workflow has context_snapshot with "allowed_tools" → use those
        2. If workflow object has an "allowed_tools" attribute → use that
        3. Otherwise → use DEFAULT_ALLOWED_TOOLS (all Phase 2 tools)

    Args:
        workflow: A Workflow object (from schema.py).

    Returns:
        A list of allowed tool name strings.
    """
    # Check for allowed_tools in context_snapshot (stored in workflow JSON)
    if workflow.context_snapshot and "allowed_tools" in workflow.context_snapshot:
        return workflow.context_snapshot["allowed_tools"]

    # Check for direct attribute (future schema extension)
    if hasattr(workflow, "allowed_tools") and workflow.allowed_tools:
        return workflow.allowed_tools

    # Default: all Phase 2 registered tools
    return DEFAULT_ALLOWED_TOOLS


# ===========================================================================
# PERMISSION CHECKER
# ===========================================================================

def is_tool_permitted(tool_name: str, workflow) -> bool:
    """
    Check if a tool is permitted for the given workflow.

    Args:
        tool_name: The name of the tool the agent wants to call.
        workflow:  The Workflow object being executed.

    Returns:
        True if the tool is permitted, False otherwise.
    """
    allowed = get_allowed_tools(workflow)
    return tool_name in allowed


def get_permission_verdict(tool_name: str, workflow) -> dict:
    """
    Return a structured permission verdict for a tool + workflow.

    Returns:
        A dict with keys:
            permitted (bool): Whether the tool is allowed.
            allowed_tools (list): All allowed tools for this workflow.
            reason (str): Human-readable explanation.
    """
    allowed = get_allowed_tools(workflow)
    permitted = tool_name in allowed

    if permitted:
        reason = f"Tool '{tool_name}' is in this workflow's allowed toolset."
    else:
        reason = (
            f"Tool '{tool_name}' is NOT permitted for workflow '{workflow.id}'.\n"
            f"  Allowed tools: {allowed}"
        )

    return {
        "permitted":     permitted,
        "allowed_tools": allowed,
        "reason":        reason,
    }


def build_permissions_for_workflow(step_tools: List[str]) -> dict:
    """
    Build a permissions policy dict for a new workflow being taught.

    Called by teach.py to generate the allowed_tools list based
    on the tools actually used in the workflow's steps.

    Only includes tools from the Phase 2 registry.
    Unknown tools are excluded (they'll be blocked by the risk engine anyway).

    Args:
        step_tools: List of tool names from workflow steps.

    Returns:
        A dict with "allowed_tools" key, suitable for storing in context_snapshot.
    """
    registered = set(list_tools())
    # Only permit tools that are both in the workflow AND registered
    permitted = [t for t in step_tools if t in registered]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in permitted:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return {"allowed_tools": unique}


# ===========================================================================
# SELF-TEST — Run: python core/permissions.py
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  RECALLYN -- Permissions Module Test")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    def chk(label, condition):
        global tests_passed, tests_failed
        if condition:
            tests_passed += 1
            print(f"  [PASSED] {label}")
        else:
            tests_failed += 1
            print(f"  [FAILED] {label}")

    from schema import Workflow

    # Workflow WITH explicit allowed_tools in snapshot
    restricted_wf = Workflow(
        id="wf_restricted",
        goal="Read and summarize only",
        inputs={},
        steps=[{"n": 1, "tool": "read_file", "args": {"path": "report.csv"}}],
        version=1,
        confidence=0.9,
        context_snapshot={"allowed_tools": ["read_file", "summarize"]},
    )

    # Workflow WITHOUT explicit allowed_tools (uses defaults)
    default_wf = Workflow(
        id="wf_default",
        goal="Standard workflow with all tools",
        inputs={"source_file": "report.csv"},
        steps=[{"n": 1, "tool": "read_file", "args": {"path": "$source_file"}}],
        version=1,
        confidence=0.9,
    )

    print("\n-- Restricted Workflow (allowed: read_file, summarize) --")
    chk("read_file permitted",    is_tool_permitted("read_file",    restricted_wf))
    chk("summarize permitted",    is_tool_permitted("summarize",    restricted_wf))
    chk("send_email NOT permitted", not is_tool_permitted("send_email", restricted_wf))
    chk("delete_file NOT permitted", not is_tool_permitted("delete_file", restricted_wf))
    chk("lookup_contact NOT permitted", not is_tool_permitted("lookup_contact", restricted_wf))

    print("\n-- Default Workflow (all Phase 2 tools allowed) --")
    chk("read_file permitted",       is_tool_permitted("read_file",    default_wf))
    chk("send_email permitted",      is_tool_permitted("send_email",   default_wf))
    chk("lookup_contact permitted",  is_tool_permitted("lookup_contact", default_wf))
    chk("hack_system NOT permitted", not is_tool_permitted("hack_system", default_wf))

    print("\n-- Permission Verdicts --")
    v = get_permission_verdict("send_email", restricted_wf)
    chk("Verdict for denied tool shows NOT permitted", not v["permitted"])
    chk("Verdict includes reason",                     len(v["reason"]) > 10)

    print("\n-- build_permissions_for_workflow --")
    policy = build_permissions_for_workflow(["read_file", "summarize", "send_email", "hack_system"])
    chk("Builds policy with registered tools only",
        "read_file" in policy["allowed_tools"] and "hack_system" not in policy["allowed_tools"])
    chk("No duplicates in policy",
        len(policy["allowed_tools"]) == len(set(policy["allowed_tools"])))

    print(f"\n  Default allowed tools: {DEFAULT_ALLOWED_TOOLS}")
    print(f"  Policy for ['read_file','summarize','send_email','hack_system']: "
          f"{policy['allowed_tools']}")

    print()
    print("=" * 60)
    print(f"  Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
