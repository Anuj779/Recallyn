from datetime import datetime
from typing import List, Any
import copy

def propose_memory_update(drift_changes: List[Any]) -> str:
    """
    Generate a summary of the proposed memory update based on user-approved drift.
    """
    if not drift_changes:
        return ""
        
    proposal = []
    for change in drift_changes:
        proposal.append(f"Update {change.field} from '{change.old_value}' to '{change.new_value}'")
        
    return " and ".join(proposal)

def create_new_version(workflow: Any, reason: str, apply_changes: dict = None) -> Any:
    """
    Safely create a new version of the workflow, apply changes to inputs/context, 
    and append the previous state to history.
    """
    # Record current state in history before modifying
    history_entry = {
        "version": workflow.version,
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "inputs": copy.deepcopy(workflow.inputs)
    }
    
    if not hasattr(workflow, 'history') or workflow.history is None:
        workflow.history = []
        
    workflow.history.append(history_entry)
    
    # Apply changes to inputs
    if apply_changes:
        for k, v in apply_changes.items():
            workflow.inputs[k] = v
            
    # Bump version
    workflow.version += 1
    return workflow

def rollback(workflow_id: str) -> bool:
    """
    Roll back to the previous version based on history.
    """
    from memory import load_workflow, save_workflow
    wf = load_workflow(workflow_id)
    if not wf or not getattr(wf, 'history', None):
        return False
        
    # Get last history entry
    last_state = wf.history.pop()
    wf.version = last_state["version"]
    wf.inputs = last_state.get("inputs", wf.inputs)
    
    save_workflow(wf)
    return True
