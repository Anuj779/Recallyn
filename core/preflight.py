# -*- coding: utf-8 -*-
"""
core/preflight.py
=================
Phase 6 (Preflight) — Unified Pre-execution Checks.

Run Workflow
   ↓
🧪 Preflight
   ├─ Inputs available?
   ├─ Dependencies available?
   ├─ Permissions valid?
   ├─ Target valid?
   └─ Context valid?
        ↓
   ✅ Proceed or ⚠️ Ask / Stop
"""

import sys
import io
import os

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))
from schema import Workflow
from permissions import is_tool_permitted
from drift import check_drift, DriftResult

class PreflightCheck:
    def __init__(self, name: str):
        self.name = name
        self.status = "PASS" # PASS, WARN, FAIL
        self.messages = []

class PreflightReport:
    def __init__(self):
        self.checks = {
            "inputs": PreflightCheck("Inputs available?"),
            "dependencies": PreflightCheck("Dependencies available?"),
            "permissions": PreflightCheck("Permissions valid?"),
            "targets": PreflightCheck("Target valid?"),
            "context": PreflightCheck("Context valid?")
        }
        self.drift_result: DriftResult = None
        self.can_proceed = True

def _check_inputs(workflow: Workflow, report: PreflightReport):
    inputs = workflow.inputs or {}
    missing_vars, missing_files = set(), set()
    from pathlib import Path
    UPLOAD_DIR = Path(__file__).parent.parent / 'data' / 'uploads'
    for step in workflow.steps:
        for val in step.args.values():
            if isinstance(val, str) and val.startswith('$') and '.' not in val:
                ref = val[1:]
                if not ref.startswith('step') and ref not in inputs:
                    missing_vars.add(ref)
    for key, value in inputs.items():
        if isinstance(value, str):
            if value.startswith('file_'):
                found = False
                if UPLOAD_DIR.exists():
                    for f in UPLOAD_DIR.iterdir():
                        if f.name.startswith(value + '_'):
                            found = True; break
                if not found: missing_files.add(value)
            elif 'file' in key or 'path' in key or value.endswith('.csv') or value.endswith('.pdf'):
                if not (Path(__file__).parent.parent / value).exists():
                    missing_files.add(value)
    if missing_vars:
        report.checks['inputs'].status = 'FAIL'
        report.checks['inputs'].messages.append(f'Missing required inputs: {missing_vars}')
        report.can_proceed = False
    if missing_files:
        report.checks['inputs'].status = 'MISSING_FILE'
        report.checks['inputs'].messages.append(f'REQUIRED FILE NOT FOUND: {missing_files}')
        report.can_proceed = False

def _check_dependencies(workflow: Workflow, report: PreflightReport):
    """Scan steps for $stepN.var references and ensure step N occurs before current step."""
    for step in workflow.steps:
        for val in step.args.values():
            if isinstance(val, str) and val.startswith("") and "." in val:
                ref = val[1:]
                parts = ref.split(".", 1)
                step_ref_str = parts[0].replace("step", "")
                if step_ref_str.isdigit():
                    step_ref_num = int(step_ref_str)
                    if step_ref_num >= step.n:
                        report.checks["dependencies"].status = "FAIL"
                        report.checks["dependencies"].messages.append(f"Step {step.n} references future/current Step {step_ref_num}.")
                        report.can_proceed = False

def _check_permissions(workflow: Workflow, report: PreflightReport):
    """Ensure all tools used in the workflow are permitted."""
    blocked = set()
    for step in workflow.steps:
        if not is_tool_permitted(step.tool, workflow):
            blocked.add(step.tool)
    
    if blocked:
        report.checks["permissions"].status = "FAIL"
        report.checks["permissions"].messages.append(f"Blocked tools detected: {', '.join(blocked)}")
        report.can_proceed = False

def _check_targets(workflow: Workflow, report: PreflightReport):
    """Static analysis of static targets like roles or files if they are hardcoded."""
    from context import load_world
    try:
        world = load_world()
    except Exception:
        report.checks["targets"].status = "WARN"
        report.checks["targets"].messages.append("Could not load world data for static target verification.")
        return
        
    for step in workflow.steps:
        if step.tool == "lookup_contact" and "role" in step.args:
            role = step.args["role"]
            if not isinstance(role, str) or role.startswith("$"): continue
            
            contacts = world.get("contacts", {})
            if role.lower() not in contacts:
                report.checks["targets"].status = "FAIL"
                report.checks["targets"].messages.append(f"Static target invalid: Role '{role}' not found in contacts.")
                report.can_proceed = False

def _check_context(workflow: Workflow, report: PreflightReport):
    """Run Phase 3 drift detection."""
    report.drift_result = check_drift(workflow)
    verdict = report.drift_result.verdict
    
    if verdict == "DRIFT":
        report.checks["context"].status = "DRIFT"
    elif verdict == "UNKNOWN":
        report.checks["context"].status = "WARN"

def run_preflight(workflow: Workflow) -> PreflightReport:
    """Execute all preflight checks."""
    report = PreflightReport()
    _check_inputs(workflow, report)
    _check_dependencies(workflow, report)
    _check_context(workflow, report)
    _check_permissions(workflow, report)
    _check_targets(workflow, report)
    return report

def print_preflight_report(report: PreflightReport):
    """Render the preflight UI."""
    print("\n  🧪 Preflight")
    checks_list = [
        ("inputs", report.checks["inputs"]),
        ("dependencies", report.checks["dependencies"]),
        ("context", report.checks["context"]),
        ("permissions", report.checks["permissions"]),
        ("targets", report.checks["targets"]),
    ]
    
    for i, (key, check) in enumerate(checks_list):
        is_last = (i == len(checks_list) - 1)
        branch = "└─" if is_last else "├─"
        
        status_color = check.status
        if status_color == "PASS":
            status_text = "PASS"
        elif status_color == "FAIL":
            status_text = "FAIL"
        elif status_color == "DRIFT":
            status_text = "DRIFT"
        else:
            status_text = f"{status_color}"
            
        print(f"   {branch} {check.name.ljust(25)} [{status_text}]")
        for msg in check.messages:
            print(f"      - {msg}")
            
    print()
