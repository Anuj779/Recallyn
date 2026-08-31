# -*- coding: utf-8 -*-
"""
core/recovery.py
================
Phase 5 — Failure Classification & Safe Controlled Recovery.
"""

from typing import Any, Tuple

class FailureType:
    TRANSIENT = "TRANSIENT"
    MISSING_INPUT = "MISSING_INPUT"
    WRONG_TARGET = "WRONG_TARGET"
    NOT_PERMITTED = "NOT_PERMITTED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    UNKNOWN = "UNKNOWN"

def classify_failure(error_msg: str) -> str:
    """
    Deterministically classify a failure message into a FailureType category.
    """
    err = str(error_msg).lower()
    
    if "permission denied" in err or "blocked" in err:
        return FailureType.NOT_PERMITTED
        
    if "no contact found" in err or "unknown role" in err or "invalid address" in err or "wrong target" in err or "recipient" in err:
        return FailureType.WRONG_TARGET
        
    if "does not exist" in err or "missing" in err or "not found" in err or "no such" in err:
        return FailureType.MISSING_INPUT
        
    if "timeout" in err or "connection" in err or "temporary" in err or "transient" in err:
        return FailureType.TRANSIENT
        
    if "verification failed" in err or "no matching" in err or "does not match" in err:
        return FailureType.VERIFICATION_FAILED
        
    return FailureType.UNKNOWN

def attempt_recovery(failure_type: str, state: Any) -> Tuple[bool, str]:
    """
    Attempt safe recovery based on failure type.
    Enforces strict safety boundaries:
      - Only TRANSIENT errors are allowed limited retries (max 2).
      - WRONG_TARGET, MISSING_INPUT, NOT_PERMITTED, and VERIFICATION_FAILED stop for human safety.
    """
    if failure_type == FailureType.TRANSIENT:
        retries = getattr(state, "retry_count", 0)
        if retries < 2:
            state.retry_count = retries + 1
            return True, f"Retrying transient failure (attempt {state.retry_count}/2)..."
        return False, "Max retries (2) exceeded for transient failure."
        
    if failure_type == FailureType.WRONG_TARGET:
        return False, "Wrong or unknown target detected. Cannot auto-recover unknown recipient safely."

    if failure_type == FailureType.MISSING_INPUT:
        return False, "Missing input detected. Cannot safely auto-recover without user intervention."
        
    if failure_type == FailureType.NOT_PERMITTED:
        return False, "Permission denied. Safety boundary prevents recovery."
        
    if failure_type == FailureType.VERIFICATION_FAILED:
        return False, "Postcondition verification failed. Manual diagnosis required."
        
    return False, f"No safe automatic recovery defined for failure type: {failure_type}."
