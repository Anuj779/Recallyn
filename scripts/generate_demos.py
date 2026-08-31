import json
import os

DEMO_FILE = "data/demo_workflows.json"

workflows = {
  "wf_demo_business_report": {
    "id": "wf_demo_business_report",
    "goal": "Summarize weekly sales performance and deliver the summary to the manager.",
    "inputs": {
      "report_file": "weekly_sales_report.csv",
      "manager_role": "Manager"
    },
    "steps": [
      {
        "n": 1,
        "tool": "read_file",
        "args": { "path": "$report_file" }
      },
      {
        "n": 2,
        "tool": "summarize",
        "args": { "text": "$step1.content" }
      },
      {
        "n": 3,
        "tool": "lookup_contact",
        "args": { "role": "$manager_role" }
      },
      {
        "n": 4,
        "tool": "send_email",
        "args": {
          "to": "$step3.email",
          "subject": "Weekly Business Report Summary",
          "body": "$step2.summary"
        }
      }
    ],
    "context_snapshot": {
      "taught_on": "2026-08-31",
      "manager": "Priya Sharma"
    },
    "postconditions": [
      {
        "check": "email_sent",
        "expect": {
          "to": "$step3.email",
          "subject": "Weekly Business Report Summary"
        }
      }
    ],
    "version": 1,
    "confidence": 1.0,
    "description": "Reads the weekly sales report, summarizes it, resolves the manager's email, and sends it out."
  },
  "wf_demo_meeting_prep": {
    "id": "wf_demo_meeting_prep",
    "goal": "Prepare for the strategy meeting by summarizing the brief and preparing notes.",
    "inputs": {
      "brief_file": "meeting_brief.pdf",
      "participant_role": "Manager"
    },
    "steps": [
      {
        "n": 1,
        "tool": "lookup_contact",
        "args": { "role": "$participant_role" }
      },
      {
        "n": 2,
        "tool": "read_file",
        "args": { "path": "$brief_file" }
      },
      {
        "n": 3,
        "tool": "summarize",
        "args": { "text": "$step2.content" }
      },
      {
        "n": 4,
        "tool": "share_notes",
        "args": {
          "title": "Strategy Prep Notes",
          "content": "$step3.summary"
        }
      }
    ],
    "context_snapshot": {
      "taught_on": "2026-08-31",
      "manager": "Priya Sharma"
    },
    "version": 1,
    "confidence": 1.0,
    "description": "Prepares the user for an upcoming meeting."
  },
  "wf_demo_context_drift": {
    "id": "wf_demo_context_drift",
    "goal": "Send report to manager (Context Drift example)",
    "inputs": {
      "report_file": "weekly_sales_report.csv",
      "manager_role": "Manager"
    },
    "steps": [
      {
        "n": 1,
        "tool": "read_file",
        "args": { "path": "$report_file" }
      },
      {
        "n": 2,
        "tool": "lookup_contact",
        "args": { "role": "$manager_role" }
      },
      {
        "n": 3,
        "tool": "send_email",
        "args": {
          "to": "$step2.email",
          "subject": "Confidential Report",
          "body": "$step1.content"
        }
      }
    ],
    "context_snapshot": {
      "taught_on": "2023-01-01",
      "manager": "Rahul Mehta"
    },
    "version": 1,
    "confidence": 1.0,
    "description": "Demonstrates Context Drift. Snapshot expects Rahul Mehta, but world state has Priya Sharma."
  },
  "wf_demo_safety_check": {
    "id": "wf_demo_safety_check",
    "goal": "Dangerous instruction example",
    "inputs": {
      "target_file": "C:/Windows/System32/config/SAM"
    },
    "steps": [
      {
        "n": 1,
        "tool": "delete_file",
        "args": { "path": "$target_file" }
      }
    ],
    "context_snapshot": {
      "taught_on": "2026-08-31"
    },
    "version": 1,
    "confidence": 0.2,
    "description": "Demonstrates Risk/Trust engine blocking a CRITICAL action."
  },
  "wf_demo_missing_input": {
    "id": "wf_demo_missing_input",
    "goal": "Process monthly expenses",
    "inputs": {
      "expense_file": "missing_monthly_expenses.csv"
    },
    "steps": [
      {
        "n": 1,
        "tool": "read_file",
        "args": { "path": "$expense_file" }
      },
      {
        "n": 2,
        "tool": "summarize",
        "args": { "text": "$step1.content" }
      }
    ],
    "context_snapshot": {
      "taught_on": "2026-08-31"
    },
    "version": 1,
    "confidence": 1.0,
    "description": "Demonstrates missing input recovery since the file does not exist."
  },
  "wf_demo_verification_failure": {
    "id": "wf_demo_verification_failure",
    "goal": "Update IT Ticket status",
    "inputs": {
      "ticket_id": "IT-1024",
      "status": "CLOSED"
    },
    "steps": [
      {
        "n": 1,
        "tool": "update_ticket_status",
        "args": {
          "ticket_id": "$ticket_id",
          "status": "$status"
        }
      }
    ],
    "postconditions": [
      {
        "check": "ticket_status",
        "expect": {
          "ticket_id": "$ticket_id",
          "status": "CLOSED"
        }
      }
    ],
    "context_snapshot": {
      "taught_on": "2026-08-31"
    },
    "version": 1,
    "confidence": 1.0,
    "description": "Demonstrates verification failure. The tool claims success, but the verification hook returns false."
  }
}

os.makedirs("data", exist_ok=True)
with open(DEMO_FILE, "w", encoding="utf-8") as f:
    json.dump(workflows, f, indent=2)

print(f"Created {DEMO_FILE}")
