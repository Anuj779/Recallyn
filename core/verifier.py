import json
from pathlib import Path
from typing import Dict, Any, List

class VerificationStatus:
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

ROOT_DIR = Path(__file__).parent.parent
EMAIL_LOG_FILE = ROOT_DIR / "data" / "email_log.json"
OUTPUT_DIR = ROOT_DIR / "data" / "output"

def verify_email_log(expect: Dict[str, Any]) -> tuple[str, str]:
    if not EMAIL_LOG_FILE.exists():
        return VerificationStatus.FAILED, "email_log.json does not exist."
    try:
        logs = json.loads(EMAIL_LOG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return VerificationStatus.UNKNOWN, "Failed to parse email_log.json."
    
    for entry in reversed(logs):
        match = True
        for k, v in expect.items():
            if str(entry.get(k, "")) != str(v):
                match = False
                break
        if match:
            return VerificationStatus.VERIFIED, f"Found matching email to {expect.get('to')}."
    
    return VerificationStatus.FAILED, f"No matching email found in log for: {expect}"

def verify_file_exists(expect: Dict[str, Any]) -> tuple[str, str]:
    filename = expect.get("path")
    if not filename:
        return VerificationStatus.UNKNOWN, "No 'path' specified in postcondition."
    
    target = OUTPUT_DIR / Path(filename).name
    if target.exists():
        return VerificationStatus.VERIFIED, f"File {filename} exists."
    return VerificationStatus.FAILED, f"File {filename} does not exist."

def verify_postconditions(postconditions: List[Dict[str, Any]]) -> tuple[str, List[str]]:
    """
    Verify all postconditions.
    Returns: (overall_status, list_of_details)
    """
    if not postconditions:
        # Nothing to verify -> automatically VERIFIED for the sake of the workflow
        return VerificationStatus.VERIFIED, ["No postconditions to verify."]

    all_verified = True
    details = []

    for pc in postconditions:
        check_type = pc.get("check")
        expect = pc.get("expect", {})
        
        status = VerificationStatus.UNKNOWN
        detail = f"Unknown check type: {check_type}"
        
        if check_type in ["email_log_contains", "email_sent"]:
            status, detail = verify_email_log(expect)
        elif check_type == "file_exists":
            status, detail = verify_file_exists(expect)
            
        details.append(f"[{status}] {check_type}: {detail}")
        
        if status != VerificationStatus.VERIFIED:
            all_verified = False
            
    if all_verified:
        return VerificationStatus.VERIFIED, details
    else:
        return VerificationStatus.FAILED, details
