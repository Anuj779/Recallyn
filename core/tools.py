# -*- coding: utf-8 -*-
"""
core/tools.py
=============
The Tool Registry — all executable tools for Recallis Phase 2.

CONCEPT: What is a Tool?
---------------------------------------------------------------------------
A Tool is a Python function that does exactly ONE specific job.

Think of it like a physical tool in a toolbox:
  - A hammer ONLY drives nails.
  - A screwdriver ONLY turns screws.
  - read_file() ONLY reads a file.
  - send_email() ONLY sends an email.

Each tool:
  1. Accepts specific inputs (arguments)
  2. Does ONE thing
  3. Returns a structured result (always the same shape)
  4. Does NOT call other tools
  5. Does NOT make decisions

The AGENT decides which tool to call and when.
The TOOL just executes.

CONCEPT: Tool Registry
---------------------------------------------------------------------------
The registry is a simple Python dictionary:

    
# ===========================================================================
    

The agent looks up the tool name from the workflow step.
If the name is IN the registry -> call it.
If the name is NOT in the registry -> STOP SAFELY.

This is a critical security property:
  Arbitrary code cannot run. Only registered functions can.
  The LLM cannot invent a tool name and have it execute.

CONCEPT: Mock World
---------------------------------------------------------------------------
For the hackathon demo, we use a controlled "mock world" instead
of real files, real email servers, or real contact databases.

WHY?
  - Real email sends could fail, require passwords, or hit rate limits.
  - Real files may not exist on the demo machine.
  - The demo must be repeatable and reliable every time.

The mock world is defined as Python dicts inside this file.
"send_email" writes to data/email_log.json instead of actually sending.
"read_file" reads from the MOCK_FILES dict instead of from disk.

This is a standard technique in software engineering called "mocking".

RESULT FORMAT (every tool returns this exact shape):
---------------------------------------------------------------------------
    SUCCESS: {"success": True,  "data": {...}, "error": None}
    FAILURE: {"success": False, "data": None,  "error": "reason"}

The agent always checks ["success"] first before reading ["data"].
---------------------------------------------------------------------------
"""

import sys
import io
import json
from mobile_actions import build_maps_intent, build_share_intent
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Root of the project (parent of core/)
ROOT_DIR = Path(__file__).parent.parent
EMAIL_LOG_FILE = ROOT_DIR / "data" / "email_log.json"
OUTPUT_DIR = ROOT_DIR / "data" / "output"


# ===========================================================================
# MOCK WORLD — Controlled demo environment
# ===========================================================================

# Simulated file system.
# In a real product these would be actual files on disk.
# For Phase 2 we hardcode known files so the demo always works.
MOCK_FILES = {
    "report.csv": (
        "Name,Department,Sales\n"
        "Alice,Engineering,45000\n"
        "Bob,HR,32000\n"
        "Carol,Sales,67000\n"
        "David,Engineering,51000\n"
        "Eve,Marketing,38000"
    ),
    "user_data.csv": (
        "Name,Age,Role,Email\n"
        "Alice,30,Engineer,alice@company.local\n"
        "Bob,28,Designer,bob@company.local\n"
        "Carol,35,Manager,carol@company.local"
    ),
    "notes.txt": (
        "Meeting notes from Monday:\n"
        "- Discussed Q3 targets\n"
        "- Alice to lead the new API project\n"
        "- Budget review scheduled for Friday"
    ),
    "sales_data.csv": (
        "Month,Revenue,Units\n"
        "January,120000,450\n"
        "February,135000,510\n"
        "March,98000,390"
    ),
}

# Simulated contact book.
# Lookup by role name (case-insensitive).
MOCK_CONTACTS = {
    "manager":   {"name": "Carol Singh",  "email": "carol@company.local"},
    "hr":        {"name": "HR Team",      "email": "hr@company.local"},
    "ceo":       {"name": "Anil Kapoor",  "email": "ceo@company.local"},
    "developer": {"name": "Alice Sharma", "email": "alice@company.local"},
    "sales":     {"name": "David Khan",   "email": "david@company.local"},
    "marketing": {"name": "Eve Nair",     "email": "eve@company.local"},
}


# ===========================================================================
# HELPER — Standard result builders
# ===========================================================================

def _ok(data: dict) -> dict:
    """Build a standard success result."""
    return {"success": True, "data": data, "error": None}


def _fail(reason: str) -> dict:
    """Build a standard failure result."""
    return {"success": False, "data": None, "error": reason}


# ===========================================================================
# TOOL 1 — read_file
# ===========================================================================

def read_file(path: str) -> dict:
    """
    Read a file and return its text content.

    Looks up the filename in the MOCK_FILES world first.
    If not found there, tries to read from disk (real file).

    Args:
        path: The filename or path to read (e.g., "report.csv")

    Returns:
        Success: {"content": "...file text...", "filename": path}
        Failure: {"error": "File not found: report.csv"}
    """
    if not path or not isinstance(path, str):
        return _fail("read_file: 'path' argument is required and must be a string.")

    filename = Path(path).name  # Strip any directory prefix for mock lookup

    # 0. Check world.json for simulated file existence
    world_file = ROOT_DIR / "data" / "world.json"
    if world_file.exists():
        try:
            world_data = json.loads(world_file.read_text(encoding="utf-8"))
            files_dict = world_data.get("files", {})
            if filename in files_dict and files_dict[filename].get("exists") is False:
                return _fail(f"read_file: File '{filename}' not found (simulated missing).")
        except Exception:
            pass

    # 1. Check mock world first
    if filename in MOCK_FILES:
        content = MOCK_FILES[filename]
        return _ok({"content": content, "filename": filename, "source": "mock"})

    
    # 2. Try real disk as fallback
    real_path = ROOT_DIR / path
    if real_path.exists() and real_path.is_file():
        try:
            content = real_path.read_text(encoding="utf-8")
            return _ok({"content": content, "filename": str(path), "source": "disk"})
        except Exception as e:
            return _fail(f"read_file: Could not read '{path}': {e}")
            
    # 2.5 Try uploads folder if it's a file ID
    uploads_dir = ROOT_DIR / "data" / "uploads"
    if uploads_dir.exists():
        matches = list(uploads_dir.glob(f"*{path}*"))
        if matches:
            try:
                try: content = matches[0].read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = f"Binary content of {matches[0].name}"
                return _ok({"content": content, "filename": matches[0].name, "source": "upload"})
            except Exception as e:
                return _fail(f"read_file: Could not read uploaded file '{matches[0].name}': {e}")


    # 3. Not found anywhere
    return _fail(
        f"read_file: File '{filename}' not found.\n"
        f"  Available mock files: {list(MOCK_FILES.keys())}"
    )


# ===========================================================================
# TOOL 2 — summarize
# ===========================================================================

def summarize(text: str) -> dict:
    """
    Summarize a block of text.

    For Phase 2 this uses a simple deterministic approach:
    - Extract the first line as a title hint
    - Count lines and words
    - Build a brief structured summary

    We deliberately avoid calling the LLM here to keep Phase 2
    fast, offline-capable, and reliably testable.

    A real Phase 5 enhancement could swap this for an LLM summary.

    Args:
        text: The text to summarize.

    Returns:
        Success: {"summary": "...", "word_count": N, "line_count": N}
        Failure: {"error": "..."}
    """
    if not text or not isinstance(text, str):
        return _fail("summarize: 'text' argument is required and must be a non-empty string.")

    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    words = text.split()
    word_count = len(words)
    line_count = len(lines)

    # Build a deterministic summary based on the content shape
    if line_count == 0:
        return _fail("summarize: Input text is empty after stripping.")

    first_line = lines[0]
    lines[-1] if len(lines) > 1 else ""

    # Check if it looks like a CSV (contains commas + header row)
    is_csv = "," in first_line and len(lines) > 1
    data_rows = line_count - 1  # Subtract header row

    if is_csv:
        columns = [c.strip() for c in first_line.split(",")]
        summary = (
            f"This dataset contains {data_rows} record(s) "
            f"with {len(columns)} column(s): {', '.join(columns)}. "
            f"First data row: {lines[1] if len(lines) > 1 else 'N/A'}."
        )
    else:
        # Plain text: show truncated content
        preview = " ".join(words[:20])
        if word_count > 20:
            preview += "..."
        summary = (
            f"Document with {line_count} line(s) and {word_count} word(s). "
            f"Preview: {preview}"
        )

    return _ok({
        "summary":    summary,
        "word_count": word_count,
        "line_count": line_count,
        "first_line": first_line,
    })


# ===========================================================================
# TOOL 3 — lookup_contact
# ===========================================================================

def lookup_contact(role: str) -> dict:
    """
    Look up a person's contact information by their role.

    Searches the MOCK_CONTACTS directory (case-insensitive).

    Args:
        role: The role to look up (e.g., "HR", "Manager", "CEO")

    Returns:
        Success: {"name": "...", "email": "...", "role": role}
        Failure: {"error": "Contact not found for role: ..."}
    """
    if not role or not isinstance(role, str):
        return _fail("lookup_contact: 'role' argument is required and must be a string.")

    role_key = role.strip().lower()

    # 1. Try to load from world.json first (dynamic environment)
    contact = None
    world_file = ROOT_DIR / "data" / "world.json"
    if world_file.exists():
        try:
            world_data = json.loads(world_file.read_text(encoding="utf-8"))
            contacts = world_data.get("contacts", {})
            contact = contacts.get(role_key)
        except Exception:
            pass

    # 2. Fallback to MOCK_CONTACTS if not found in world.json
    if contact is None:
        contact = MOCK_CONTACTS.get(role_key)

    if contact is None:
        available = list(MOCK_CONTACTS.keys())
        return _fail(
            f"lookup_contact: No contact found for role '{role}'.\n"
            f"  Available roles: {available}"
        )

    return _ok({
        "name":  contact["name"],
        "email": contact["email"],
        "role":  role,
    })


# ===========================================================================
# TOOL 4 — write_file
# ===========================================================================

def write_file(path: str, content: str) -> dict:
    """
    Write text content to a file inside data/output/.

    The path is sandboxed — it always writes inside data/output/
    to prevent writing to arbitrary locations on the filesystem.

    Args:
        path:    Filename to write (e.g., "summary.txt")
        content: Text content to write

    Returns:
        Success: {"path": "data/output/summary.txt", "bytes_written": N}
        Failure: {"error": "..."}
    """
    if not path or not isinstance(path, str):
        return _fail("write_file: 'path' argument is required.")
    if content is None:
        return _fail("write_file: 'content' argument is required.")

    # Sandbox: only write inside data/output/
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = Path(path).name  # Strip directory portion — sandboxed
    target = OUTPUT_DIR / filename

    try:
        target.write_text(str(content), encoding="utf-8")
        return _ok({
            "path":          str(target.relative_to(ROOT_DIR)),
            "bytes_written": len(content.encode("utf-8")),
        })
    except Exception as e:
        return _fail(f"write_file: Failed to write '{filename}': {e}")


# ===========================================================================
# TOOL 5 — send_email
# ===========================================================================

def send_email(to: str, subject: str, body: str) -> dict:
    if not to: return _fail('to required')
    return _ok({'status': 'Prepared', 'action_type': 'OPEN_EMAIL_COMPOSE', 'payload': {'to': [to], 'subject': subject, 'body': body}})


# ===========================================================================
# TOOL 6 — run_sql_query
# ===========================================================================

def run_sql_query(query: str) -> dict:
    """
    Simulate running a SQL database query. Returns mocked rows.
    """
    if not query or not isinstance(query, str):
        return _fail("run_sql_query: 'query' argument is required.")
        
    # Return some mock data based on keywords
    query_lower = query.lower()
    
    if "users" in query_lower or "employees" in query_lower:
        rows = [
            {"id": 1, "name": "Alice", "role": "Engineering"},
            {"id": 2, "name": "Bob", "role": "HR"}
        ]
    elif "sales" in query_lower or "revenue" in query_lower:
        rows = [
            {"region": "North America", "revenue": 150000},
            {"region": "Europe", "revenue": 120000}
        ]
    else:
        rows = [{"result": "mock_data", "count": 10}]
        
    return _ok({"query": query, "rows": rows, "count": len(rows)})


# ===========================================================================
# TOOL 7 — create_calendar_event
# ===========================================================================

def create_calendar_event(title: str, date: str, attendees: list) -> dict:
    """
    Simulate creating a calendar event by logging it to data/calendar_log.json.
    """
    if not title:
        return _fail("create_calendar_event: 'title' is required.")
    if not date:
        return _fail("create_calendar_event: 'date' is required.")
        
    log_file = ROOT_DIR / "data" / "calendar_log.json"
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "title": title,
        "date": date,
        "attendees": attendees if isinstance(attendees, list) else [attendees]
    }
    
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if log_file.exists():
        try:
            existing = json.loads(log_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    else:
        existing = []
        
    existing.append(entry)
    log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    
    return _ok({
        "event_created": True,
        "title": title,
        "date": date,
        "attendees": entry["attendees"]
    })


# ===========================================================================
# TOOL 8 — delete_file
# ===========================================================================

def delete_file(path: str) -> dict:
    """
    Delete a file inside the sandboxed data/output/ directory.
    """
    if not path:
        return _fail("delete_file: 'path' argument is required.")
        
    filename = Path(path).name
    target = OUTPUT_DIR / filename
    
    if not target.exists():
        return _fail(f"delete_file: File '{filename}' not found in output directory.")
        
    try:
        target.unlink()
        return _ok({"deleted": True, "path": str(target.relative_to(ROOT_DIR))})
    except Exception as e:
        return _fail(f"delete_file: Failed to delete '{filename}': {e}")


# ===========================================================================

# ===========================================================================
# NEW OFFICE TOOLS (Phase 5 Expansion)
# ===========================================================================

def send_slack_message(channel: str, message: str) -> dict:
    if not channel or not message: return _fail("channel and message required")
    return _ok({"sent": True, "channel": channel, "message": message, "platform": "Slack"})

def read_latest_emails(folder: str, count: int) -> dict:
    return _ok({"folder": folder, "emails": [{"from": "ceo@company.local", "subject": "Urgent Update"}]})

def create_jira_ticket(project: str, title: str, description: str) -> dict:
    if not title: return _fail("title required")
    return _ok({"ticket_id": f"{project}-101", "status": "created", "title": title})

def update_ticket_status(ticket_id: str, status: str) -> dict:
    return _ok({"ticket_id": ticket_id, "new_status": status})

def search_knowledge_base(query: str) -> dict:
    return _ok({"query": query, "results": ["Found 1 matching article in Confluence."]})

def convert_document(path: str, target_format: str) -> dict:
    return _ok({"source": path, "format": target_format, "status": "converted"})

def request_esignature(document_path: str, signer_email: str) -> dict:
    return _ok({"document": document_path, "signer": signer_email, "status": "sent_for_signature"})

def fetch_crm_record(record_type: str, search_term: str) -> dict:
    return _ok({"record_type": record_type, "term": search_term, "data": {"status": "Active Client"}})

def generate_chart(data_source: str, chart_type: str) -> dict:
    return _ok({"chart_type": chart_type, "source": data_source, "path": f"data/output/chart_{chart_type}.png"})

def submit_expense_report(amount: float, category: str, receipt_path: str = "") -> dict:
    return _ok({"amount": amount, "category": category, "status": "submitted_for_approval"})

def create_it_ticket(issue_type: str, description: str) -> dict:
    return _ok({"ticket_id": "IT-992", "issue_type": issue_type, "status": "open"})

def search_web(query: str) -> dict:
    return _ok({"query": query, "results": ["Simulated web search result 1", "Simulated web search result 2"]})

def fetch_api_data(endpoint: str) -> dict:
    return _ok({"endpoint": endpoint, "status_code": 200, "data": {"mock": "api response"}})
# ===========================================================================

# ===========================================================================
# NEW OFFICE TOOLS (Phase 5 Expansion)
# ===========================================================================


# ===========================================================================
# TOOL REGISTRY - The security gatekeeper
# ===========================================================================
def open_maps(location: str) -> dict:
    intent_url = build_maps_intent(location)
    return _ok({
        "location": location,
        "status": "Prepared",
        "handoff_url": intent_url,
        "handoff_type": "maps"
    })

def share_notes(title: str, content: str) -> dict:
    if not title: return _fail("title required")
    if not content: return _fail("content required")
    return _ok({"status": "Shared", "title": title, "content_length": len(content)})

# ===========================================================================
# THE REGISTRY
# ===========================================================================

TOOL_REGISTRY = {
    "read_file":      read_file,
    "summarize":      summarize,
    "lookup_contact": lookup_contact,
    "write_file":     write_file,
    "send_email":     send_email,
    "run_sql_query":  run_sql_query,
    "create_calendar_event": create_calendar_event,
    "delete_file":    delete_file,
    "send_slack_message": send_slack_message,
    "read_latest_emails": read_latest_emails,
    "create_jira_ticket": create_jira_ticket,
    "update_ticket_status": update_ticket_status,
    "search_knowledge_base": search_knowledge_base,
    "convert_document": convert_document,
    "request_esignature": request_esignature,
    "fetch_crm_record": fetch_crm_record,
    "generate_chart": generate_chart,
    "submit_expense_report": submit_expense_report,
    "create_it_ticket": create_it_ticket,
    "search_web": search_web,
    "fetch_api_data": fetch_api_data,
    "open_maps": open_maps,
    "share_notes": share_notes,
}

def list_tools() -> list:
    return list(TOOL_REGISTRY.keys())


def get_tool(name: str):
    return TOOL_REGISTRY.get(name)
