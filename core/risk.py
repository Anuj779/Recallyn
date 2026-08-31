# -*- coding: utf-8 -*-
from typing import Optional

class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

RISK_RANK = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}

TOOL_RISK_TABLE = {
    "read_file":             RiskLevel.LOW,
    "summarize":             RiskLevel.LOW,
    "lookup_contact":        RiskLevel.LOW,
    "run_sql_query":         RiskLevel.LOW,
    "write_file":            RiskLevel.MEDIUM,
    "create_calendar_event": RiskLevel.MEDIUM,
    "send_email":            RiskLevel.HIGH,
    "delete_file":           RiskLevel.CRITICAL,
    "execute_command":       RiskLevel.CRITICAL,
    "run_script":            RiskLevel.CRITICAL,
    "modify_database":       RiskLevel.CRITICAL,
    "send_slack_message":    RiskLevel.HIGH,
    "read_latest_emails":    RiskLevel.LOW,
    "create_jira_ticket":    RiskLevel.MEDIUM,
    "update_ticket_status":  RiskLevel.MEDIUM,
    "search_knowledge_base": RiskLevel.LOW,
    "convert_document":      RiskLevel.MEDIUM,
    "request_esignature":    RiskLevel.HIGH,
    "fetch_crm_record":      RiskLevel.LOW,
    "generate_chart":        RiskLevel.MEDIUM,
    "submit_expense_report": RiskLevel.HIGH,
    "create_it_ticket":      RiskLevel.MEDIUM,
    "search_web":            RiskLevel.LOW,
    "fetch_api_data":        RiskLevel.LOW,
    "open_maps":             RiskLevel.LOW,
    "share_notes":           RiskLevel.MEDIUM,
}

_UNKNOWN_TOOL_RISK = RiskLevel.CRITICAL

def is_unknown_tool(tool_name: str) -> bool:
    return tool_name not in TOOL_RISK_TABLE

def _detect_data_sensitivity(args: Optional[dict]) -> str:
    if not args:
        return "NORMAL"
    sensitive_keywords = ["confidential", "financial", "private", "secret", "salary", "password"]
    for v in args.values():
        val_str = str(v).lower()
        if any(kw in val_str for kw in sensitive_keywords):
            return "SENSITIVE"
    return "NORMAL"

def _get_target_sensitivity(tool_name: str, args: Optional[dict]) -> str:
    if tool_name in ["send_email", "request_esignature"] and args:
        recipient = str(args.get("to", args.get("signer_email", ""))).lower()
        if recipient.endswith("@company.local"):
            return "TRUSTED_INTERNAL"
        elif recipient:
            return "UNKNOWN_EXTERNAL"
    if tool_name == "send_slack_message" and args:
        channel = str(args.get("channel", "")).lower()
        if channel.startswith("#"):
            return "TRUSTED_INTERNAL"
    return "LOCAL"

def _bump_risk(current_risk: str) -> str:
    if current_risk == RiskLevel.LOW: return RiskLevel.MEDIUM
    if current_risk == RiskLevel.MEDIUM: return RiskLevel.HIGH
    return current_risk

def get_risk_evaluation(tool_name: str, args: Optional[dict] = None, context_verdict: str = "MATCH") -> tuple[str, str]:
    if is_unknown_tool(tool_name):
        return RiskLevel.CRITICAL, f"Unknown tool '{tool_name}' encountered. Safety block applied."
        
    base_risk = TOOL_RISK_TABLE[tool_name]
    scope = "EXTERNAL communication" if tool_name in ["send_email", "send_slack_message", "request_esignature"] else "LOCAL operation"
    reversibility = "IRREVERSIBLE" if tool_name in ["send_email", "delete_file", "send_slack_message", "request_esignature"] else "REVERSIBLE"
    
    target = _get_target_sensitivity(tool_name, args)
    data_sens = _detect_data_sensitivity(args)

    final_risk = base_risk
    reasons = []

    if tool_name in ["send_email", "send_slack_message"]:
        reasons.append(f"Action sends an {scope} and is {reversibility}")
    else:
        reasons.append(f"Action is a {scope} and is {reversibility}")

    if target == "TRUSTED_INTERNAL":
        reasons.append("Target is a trusted internal entity")
    elif target == "UNKNOWN_EXTERNAL":
        reasons.append(f"Target is an unexpected external address")
        final_risk = RiskLevel.HIGH if final_risk in [RiskLevel.LOW, RiskLevel.MEDIUM] else final_risk

    if data_sens == "SENSITIVE":
        reasons.append("Data contains sensitive keywords")
        final_risk = _bump_risk(final_risk)
    else:
        reasons.append("No sensitive data detected")
        
    if context_verdict == "DRIFT":
        reasons.append("Context drift detected - bumping risk level")
        final_risk = _bump_risk(final_risk)

    return final_risk, ". ".join(reasons)
