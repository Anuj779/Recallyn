# -*- coding: utf-8 -*-
"""
core/schema.py
==============
The Blueprint for a Recallis Workflow.

CONCEPT: Schema Validation
---------------------------------------------------------------------------
Think of a "schema" like a government form.
The form has boxes for "Name", "Date of Birth", "ID Number".
If someone submits a form without their Date of Birth, or puts
their name in the ID Number box, the form gets REJECTED.

Pydantic is our "form checker". We describe the rules in Python
classes, and Pydantic automatically checks that any incoming data
follows those rules exactly.

WHY IS THIS IMPORTANT?
---------------------------------------------------------------------------
The LLM will generate JSON text. But LLMs can make mistakes:
- Forget a required field
- Use the wrong data type (e.g., a string where we need a number)
- Invent a field that doesn't exist in our spec

We NEVER trust raw LLM output. This file is the deterministic
gatekeeper. If data doesn't match the schema -> it gets REJECTED.
The LLM does NOT make this decision. Python does.

ARCHITECTURE RULE: LLM = understands. Python = validates.
---------------------------------------------------------------------------
"""

import sys
import io
import re

# Ensure UTF-8 output on Windows so arrows/emojis print correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ===========================================================================
# PART 1 — Define what a single "step" inside a workflow looks like.
# ===========================================================================

class WorkflowStep(BaseModel):
    """
    A single action in the workflow.

    Example step:
        {
            "n": 1,
            "tool": "read_file",
            "args": { "path": "$source_file" }
        }

    Think of this like one instruction in a recipe:
        Step 1: Chop the onions.

    FIELDS:
        n     : The step number (1, 2, 3...). Must be >= 1.
        tool  : The name of the tool to call (e.g., "read_file", "send_email").
        args  : A dictionary of arguments to pass to that tool.
                Arguments can reference previous step outputs or workflow
                inputs using the "$variable_name" convention.
    """

    n: int = Field(..., ge=1, description="Step number, must be 1 or greater")
    tool: str = Field(..., min_length=1, description="Name of the tool to execute")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")

    @field_validator("tool")
    @classmethod
    def tool_name_must_not_be_blank(cls, value: str) -> str:
        """Strip whitespace and ensure tool name is not empty."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Tool name cannot be blank or only whitespace.")
        return cleaned


# ===========================================================================
# PART 2 — Define what a complete Workflow looks like.
# ===========================================================================

class Workflow(BaseModel):
    """
    The complete, structured representation of a user's workflow.

    This is what gets saved to memory (data/workflows.json).

    FIELDS:
        id          : A unique identifier (e.g., "wf_weekly_report").
        goal        : Plain English description of what the workflow achieves.
        inputs      : Named input values the workflow needs.
                      These become "$variable_name" placeholders in steps.
        steps       : An ordered list of WorkflowStep objects.
        version     : Starts at 1. Increases each time the workflow is updated.
        confidence  : LLM confidence score from 0.0 to 1.0.
        description : Optional longer human-readable explanation.
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique workflow ID in snake_case, e.g. 'wf_weekly_report'"
    )
    goal: str = Field(
        ...,
        min_length=5,
        description="Plain English goal of this workflow"
    )
    inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Named inputs this workflow requires"
    )
    steps: List[WorkflowStep] = Field(
        ...,
        min_length=1,
        description="Ordered list of steps. Must have at least 1 step."
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Version number. Starts at 1, increments on each update."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="LLM confidence score, between 0.0 and 1.0"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional longer description of the workflow"
    )
    context_snapshot: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Snapshot of the world context captured when this workflow was taught. "
            "Used by drift detection to compare against the current environment. "
            "None means no snapshot has been taken yet (UNKNOWN verdict)."
        )
    )
    postconditions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of expected postconditions to verify after execution."
    )
    is_demo: bool = Field(default=False, description="Flag indicating if this is a seeded demo workflow.")
    history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Audit log of version history and rollback states."
    )

    @field_validator("id")
    @classmethod
    def id_must_be_valid(cls, value: str) -> str:
        """
        The workflow ID must:
        - Not be blank
        - Contain only letters, digits, underscores, and hyphens
        - No spaces, no special characters

        Good:  "wf_weekly_report", "daily-backup-1"
        Bad:   "my workflow!", "wf weekly", ""
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Workflow ID cannot be blank.")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
            raise ValueError(
                f"Workflow ID '{cleaned}' contains invalid characters. "
                "Use only letters, digits, underscores, or hyphens."
            )
        return cleaned

    @model_validator(mode="after")
    def steps_must_be_numbered_correctly(self) -> "Workflow":
        """
        After the whole model is built, check that step numbers are
        sequential starting from 1: [1, 2, 3, ...] — no gaps, no repeats.

        Bad: [1, 3, 4]  <- step 2 is missing
        Bad: [1, 1, 2]  <- step 1 is duplicated
        """
        step_numbers = [step.n for step in self.steps]
        expected = list(range(1, len(self.steps) + 1))
        if step_numbers != expected:
            raise ValueError(
                f"Step numbers must be sequential starting from 1. "
                f"Got: {step_numbers}, expected: {expected}"
            )
        return self


# ===========================================================================
# PART 3 — Helper to parse a raw dictionary into a validated Workflow.
# ===========================================================================

def parse_workflow(data: dict) -> Workflow:
    """
    Takes a raw Python dictionary (e.g., parsed from LLM JSON output)
    and returns a validated Workflow object.

    If the data doesn't match the schema, raises pydantic.ValidationError
    with a clear explanation of what went wrong.

    Args:
        data: A Python dictionary representing a workflow.

    Returns:
        A validated Workflow object.

    Raises:
        pydantic.ValidationError: If data doesn't match the schema.
    """
    return Workflow.model_validate(data)


# ===========================================================================
# SELF-TEST — Run this file directly to test valid and invalid data.
# Usage:  python core/schema.py
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  RECALLIS -- Schema Validation Test")
    print("=" * 60)

    # -----------------------------------------------------------------------
    # TEST 1: A perfectly valid workflow. This MUST PASS.
    # -----------------------------------------------------------------------
    print("\n[TEST 1] Valid workflow -> Should PASS")
    print("-" * 40)

    valid_data = {
        "id": "wf_weekly_report",
        "goal": "Email the weekly sales summary to my manager",
        "inputs": {
            "source_file": "report.csv",
            "recipient_role": "Manager"
        },
        "steps": [
            {"n": 1, "tool": "read_file",     "args": {"path": "$source_file"}},
            {"n": 2, "tool": "summarize",      "args": {"text": "$step1.content"}},
            {"n": 3, "tool": "lookup_contact", "args": {"role": "$recipient_role"}},
            {"n": 4, "tool": "send_email",     "args": {
                "to": "$step3.email",
                "subject": "Weekly Report",
                "body": "$step2.summary"
            }},
        ],
        "version": 1,
        "confidence": 0.9,
    }

    try:
        workflow = parse_workflow(valid_data)
        print(f"  PASSED  -- Workflow '{workflow.id}' accepted.")
        print(f"     Goal    : {workflow.goal}")
        print(f"     Steps   : {len(workflow.steps)}")
        print(f"     Version : {workflow.version}")
        print(f"     Confidence: {workflow.confidence}")
    except Exception as e:
        print(f"  FAILED (unexpected) -- {e}")

    # -----------------------------------------------------------------------
    # TEST 2: Missing 'goal' field. This MUST FAIL.
    # -----------------------------------------------------------------------
    print("\n[TEST 2] Missing 'goal' field -> Should FAIL")
    print("-" * 40)

    missing_goal = {
        "id": "wf_no_goal",
        "steps": [
            {"n": 1, "tool": "read_file", "args": {"path": "test.csv"}},
        ],
    }

    try:
        parse_workflow(missing_goal)
        print("  PROBLEM -- This should have been rejected but wasn't!")
    except Exception as e:
        print(f"  CORRECTLY REJECTED -- {type(e).__name__}")

    # -----------------------------------------------------------------------
    # TEST 3: Step numbers are not sequential. This MUST FAIL.
    # -----------------------------------------------------------------------
    print("\n[TEST 3] Non-sequential step numbers [1, 3] -> Should FAIL")
    print("-" * 40)

    bad_steps = {
        "id": "wf_bad_steps",
        "goal": "A workflow with broken step numbering",
        "steps": [
            {"n": 1, "tool": "read_file", "args": {}},
            {"n": 3, "tool": "send_email", "args": {}},  # Gap! Should be 2.
        ],
    }

    try:
        parse_workflow(bad_steps)
        print("  PROBLEM -- This should have been rejected but wasn't!")
    except Exception as e:
        print(f"  CORRECTLY REJECTED -- {type(e).__name__}: Step numbering check fired.")

    # -----------------------------------------------------------------------
    # TEST 4: A workflow ID with invalid characters. This MUST FAIL.
    # -----------------------------------------------------------------------
    print("\n[TEST 4] Invalid workflow ID 'my workflow!' -> Should FAIL")
    print("-" * 40)

    bad_id = {
        "id": "my workflow!",
        "goal": "Testing bad IDs",
        "steps": [
            {"n": 1, "tool": "read_file", "args": {}},
        ],
    }

    try:
        parse_workflow(bad_id)
        print("  PROBLEM -- This should have been rejected but wasn't!")
    except Exception as e:
        print(f"  CORRECTLY REJECTED -- {type(e).__name__}: Bad ID check fired.")

    # -----------------------------------------------------------------------
    # TEST 5: Confidence value out of range (> 1.0). This MUST FAIL.
    # -----------------------------------------------------------------------
    print("\n[TEST 5] Confidence = 1.5 (out of 0.0-1.0 range) -> Should FAIL")
    print("-" * 40)

    bad_confidence = {
        "id": "wf_bad_confidence",
        "goal": "Testing confidence validation",
        "steps": [
            {"n": 1, "tool": "read_file", "args": {}},
        ],
        "confidence": 1.5,
    }

    try:
        parse_workflow(bad_confidence)
        print("  PROBLEM -- This should have been rejected but wasn't!")
    except Exception as e:
        print(f"  CORRECTLY REJECTED -- {type(e).__name__}: Confidence range check fired.")

    # -----------------------------------------------------------------------
    # SUMMARY: Show the full JSON of our valid workflow
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Valid Workflow JSON (what gets saved to memory):")
    print("=" * 60)
    workflow = parse_workflow(valid_data)
    print(workflow.model_dump_json(indent=2))
    print("=" * 60)
    print("  All schema tests complete.")
    print("=" * 60)
