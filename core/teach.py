# -*- coding: utf-8 -*-
"""
core/teach.py
=============
The LLM Bridge — Converts plain English into a validated Workflow.

CONCEPT: LLM Structured Output
---------------------------------------------------------------------------
A Large Language Model (LLM) is great at understanding natural language.
But by default it gives back conversational text, like:

  "Sure! Here is a workflow for you: ..."

We can't feed that directly into our schema validator — it will crash.

So we use a technique called "structured output": we craft a very
specific prompt that says:

  "You are a JSON generator. Output ONLY valid JSON.
   No explanations. No extra text. Follow this exact schema."

When we also set temperature=0, the model becomes deterministic
(always picks the most likely token — less creative, more consistent).

CONCEPT: Prompt
---------------------------------------------------------------------------
A "prompt" is what we send to the LLM. Think of it as the instructions
we give to a very smart but very literal assistant. The quality of the
prompt directly determines the quality of the output.

CONCEPT: Temperature
---------------------------------------------------------------------------
Temperature controls how "random" or "creative" the LLM is.
- temperature = 0   -> very consistent, follows instructions closely
- temperature = 1   -> more creative, more varied answers
- temperature = 2   -> chaotic, often nonsensical

For structured output (like JSON generation), ALWAYS use temperature=0.

CONCEPT: API Call
---------------------------------------------------------------------------
We don't run the LLM locally. We send our prompt over the internet
to Groq's servers. They run the model and send back the response.
This is called an "API call" (Application Programming Interface).

ARCHITECTURE RULE: LLM output is UNTRUSTED until validated by schema.py.
---------------------------------------------------------------------------
"""

import sys
import io
import os
import json
import time

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import load_dotenv

# Load environment variables from .env file
# This reads GROQ_API_KEY into os.environ so we never hardcode keys
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from schema import Workflow, parse_workflow
from pydantic import ValidationError


# ===========================================================================
# THE PROMPT — This is the most important part of teach.py
# ===========================================================================

SYSTEM_PROMPT = """You are a workflow extraction assistant for Recallis, a personal workflow agent.

Your ONLY job is to convert a user's natural language description of a task
into a structured JSON workflow. You must output ONLY valid JSON — no prose,
no markdown fences, no explanation.

The JSON must follow this exact schema:
{
  "id": "wf_short_snake_case_name",
  "goal": "Plain English description of the workflow's purpose",
  "inputs": {
    "variable_name": "example_value"
  },
  "steps": [
    {
      "n": 1,
      "tool": "tool_name",
      "args": { "key": "$variable_name" }
    }
  ],
  "version": 1,
  "confidence": 0.9,
  "description": "Optional longer description"
}

RULES YOU MUST FOLLOW:
1. Output ONLY raw JSON. No markdown, no triple backticks, no explanation.
2. The "id" field must be snake_case, start with "wf_", contain only letters/digits/underscores.
3. Steps must be numbered sequentially starting from 1: [1, 2, 3...].
4. Use ONLY these tools in your steps:
   - read_file             -> reads a file from disk
   - summarize             -> summarizes a block of text
   - lookup_contact        -> looks up a person's contact info by their role
   - write_file            -> writes text to a file
   - send_email            -> sends an email
   - run_sql_query         -> simulate running a SQL database query
   - create_calendar_event -> simulate creating a calendar event
   - delete_file           -> delete a file inside the output directory
   - send_slack_message    -> send a message to a slack channel
   - read_latest_emails    -> read recent emails from a folder
   - create_jira_ticket    -> create a task/ticket in Jira
   - update_ticket_status  -> change the status of a Jira ticket
   - search_knowledge_base -> query the company wiki or Notion
   - convert_document      -> convert a file (e.g. CSV to PDF)
   - request_esignature    -> request a document signature via DocuSign
   - fetch_crm_record      -> lookup customer data from Salesforce/HubSpot
   - generate_chart        -> create a chart image from data
   - submit_expense_report -> file an expense report for approval
   - create_it_ticket      -> submit a helpdesk ticket to IT
   - search_web            -> query the public internet for information
   - fetch_api_data        -> fetch JSON data from an external REST API
5. Reference inputs and previous step outputs using "$variable_name" syntax.
   Example: "$step1.content" means the "content" output from step 1.
6. The "confidence" field is your estimate (0.0 to 1.0) of how well
   you understood the user's intent. Use 0.9 for clear requests.
7. If you genuinely cannot structure the request, output:
   {"error": "reason why this cannot be structured as a workflow"}
"""

USER_PROMPT_TEMPLATE = """Convert this task into a Recallis workflow JSON:

{user_input}

Remember: output ONLY raw JSON, nothing else."""


# ===========================================================================
# LLM CLIENTS
# ===========================================================================

def _call_groq(prompt: str) -> str:
    """
    Send a prompt to Groq's Llama model and return the raw text response.

    Uses temperature=0 for deterministic, structured output.

    Raises:
        ImportError: If the groq package is not installed.
        Exception: If the API call fails for any reason.
    """
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("Groq package not installed. Run: pip install groq")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is not set in your .env file.\n"
            "  1. Get a free key at: https://console.groq.com\n"
            "  2. Open .env and replace 'your_groq_api_key_here' with your key."
        )

    client = Groq(api_key=api_key)

    # Note: We import config to get the correct model
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    try:
        import config
        groq_model = config.GROQ_MODEL
    except ImportError:
        groq_model = "qwen/qwen3.8-27b"

    response = client.chat.completions.create(
        model=groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0,       # Deterministic output — critical for JSON generation
        max_tokens=1024,
    )

    return response.choices[0].message.content.strip()


def _call_gemini(prompt: str) -> str:
    """
    Fallback: call Google Gemini Flash if Groq is unavailable.

    Raises:
        ImportError: If google-generativeai is not installed.
        Exception: If the API call fails.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai package not installed. Run: pip install google-generativeai"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not set in your .env file.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    response = model.generate_content(
        full_prompt,
        generation_config={"temperature": 0, "max_output_tokens": 1024}
    )

    return response.text.strip()


# ===========================================================================
# JSON EXTRACTION + VALIDATION
# ===========================================================================

def _extract_json(raw_text: str) -> dict:
    """
    Parse the raw LLM response into a Python dictionary.

    LLMs sometimes wrap JSON in markdown code fences like:
        ```json
        { ... }
        ```
    We strip those before parsing.

    Args:
        raw_text: The raw string returned by the LLM.

    Returns:
        A Python dictionary.

    Raises:
        ValueError: If the text cannot be parsed as JSON.
    """
    text = raw_text.strip()

    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM output is not valid JSON.\n"
            f"  Parse error: {e}\n"
            f"  Raw output (first 300 chars): {raw_text[:300]}"
        )


# ===========================================================================
# MAIN PUBLIC FUNCTION
# ===========================================================================

def teach(user_input: str, max_retries: int = 2) -> Workflow:
    """
    Convert a natural language workflow description into a validated Workflow.

    Flow:
        user_input (English)
            -> LLM (Groq, fallback: Gemini, fallback: demo mode)
            -> raw JSON text
            -> parse to dict
            -> validate with schema.py
            -> return Workflow object

    Args:
        user_input : The user's plain English workflow description.
        max_retries: How many times to retry if the LLM gives invalid JSON.

    Returns:
        A validated Workflow object ready to be saved to memory.

    Raises:
        RuntimeError: If all LLM providers fail AND demo mode cannot handle input.
        ValueError: If LLM output fails schema validation after all retries.
    """
    if not user_input or not user_input.strip():
        raise ValueError("User input cannot be empty.")

    prompt = USER_PROMPT_TEMPLATE.format(user_input=user_input.strip())
    last_error = None

    # -----------------------------------------------------------------------
    # Attempt LLM calls: Groq first, then Gemini
    # -----------------------------------------------------------------------
    providers = [
        ("Groq", _call_groq),
        ("Gemini Flash (fallback)", _call_gemini),
    ]

    raw_response = None
    used_provider = None

    for provider_name, call_fn in providers:
        try:
            print(f"  [Teach] Calling {provider_name}...")
            raw_response = call_fn(prompt)
            used_provider = provider_name
            break
        except ValueError as e:
            # Config error (bad API key) — no point retrying with this provider
            print(f"  [Teach] Config error for {provider_name}: {e}")
            last_error = e
        except Exception as e:
            print(f"  [Teach] {provider_name} unavailable: {type(e).__name__}: {e}")
            last_error = e

    # -----------------------------------------------------------------------
    # If all APIs failed, use demo fallback
    # -----------------------------------------------------------------------
    if raw_response is None:
        print("  [Teach] All LLM providers failed. Using demo fallback.")
        raw_response = _demo_fallback(user_input)
        used_provider = "Demo Fallback"

    # -----------------------------------------------------------------------
    # Parse and validate with retries
    # -----------------------------------------------------------------------
    for attempt in range(1, max_retries + 2):  # +2: first attempt + max_retries
        try:
            data = _extract_json(raw_response)

            # Check if LLM returned an error response
            if "error" in data and len(data) == 1:
                raise ValueError(f"LLM could not structure this request: {data['error']}")

            workflow = parse_workflow(data)
            print(f"  [Teach] Workflow validated successfully via {used_provider}.")

            # --- Phase 3 & 4: Attach context snapshot and permissions ---
            try:
                from context import build_snapshot
                from permissions import build_permissions_for_workflow
                snapshot = build_snapshot(workflow)
                
                # Add Phase 4 permissions to the snapshot
                tools_used = [step.tool for step in workflow.steps]
                perms = build_permissions_for_workflow(tools_used)
                snapshot.update(perms)
                
                # Pydantic model is immutable after creation — use model_copy
                workflow = workflow.model_copy(update={"context_snapshot": snapshot})
                print(f"  [Teach] Context & permissions attached ({len(snapshot)} fields).")
            except Exception as snap_err:
                # Non-fatal: snapshot failure does not block teaching
                print(f"  [Teach] Warning: could not build snapshot: {snap_err}")

            return workflow

        except (ValueError, ValidationError) as e:
            print(f"  [Teach] Attempt {attempt} failed validation: {e}")
            last_error = e

            if attempt <= max_retries:
                # Retry: ask the LLM to fix its own output
                print(f"  [Teach] Retrying with correction prompt...")
                correction_prompt = (
                    f"{prompt}\n\n"
                    f"Your previous attempt produced invalid output.\n"
                    f"Error: {e}\n"
                    f"Please try again and output ONLY valid JSON."
                )
                try:
                    raw_response = _call_groq(correction_prompt)
                except Exception:
                    try:
                        raw_response = _call_gemini(correction_prompt)
                    except Exception:
                        break
                time.sleep(1)  # Brief pause before retry

    raise ValueError(
        f"Failed to generate a valid workflow after {max_retries + 1} attempts.\n"
        f"Last error: {last_error}"
    )


# ===========================================================================
# DEMO FALLBACK — Works when no API key is available
# ===========================================================================

def _demo_fallback(user_input: str) -> str:
    """
    When all LLM providers are unavailable, generate a deterministic
    demo workflow based on simple keyword matching.

    This is NOT an LLM. It is simple Python logic.
    It ensures the demo can run even without an internet connection
    or API key, which is important for a hackathon presentation.
    """
    user_lower = user_input.lower()

    # Keyword-based routing to pre-built demo workflows
    if any(w in user_lower for w in ["email", "send", "report", "summary"]):
        return json.dumps({
            "id": "wf_weekly_report",
            "goal": "Summarize a report file and email it to the manager",
            "inputs": {
                "source_file": "report.csv",
                "recipient_role": "Manager"
            },
            "steps": [
                {"n": 1, "tool": "read_file",     "args": {"path": "$source_file"}},
                {"n": 2, "tool": "summarize",      "args": {"text": "$step1.content"}},
                {"n": 3, "tool": "lookup_contact", "args": {"role": "$recipient_role"}},
                {"n": 4, "tool": "send_email",     "args": {
                    "to":      "$step3.email",
                    "subject": "Weekly Report",
                    "body":    "$step2.summary"
                }},
            ],
            "version": 1,
            "confidence": 0.7,
            "description": "Demo fallback: weekly report workflow"
        })

    elif any(w in user_lower for w in ["backup", "copy", "save file"]):
        return json.dumps({
            "id": "wf_daily_backup",
            "goal": "Read and back up a file",
            "inputs": {"source_file": "data.csv", "backup_path": "backup.csv"},
            "steps": [
                {"n": 1, "tool": "read_file",  "args": {"path": "$source_file"}},
                {"n": 2, "tool": "write_file", "args": {
                    "path":    "$backup_path",
                    "content": "$step1.content"
                }},
            ],
            "version": 1,
            "confidence": 0.7,
            "description": "Demo fallback: file backup workflow"
        })

    else:
        # Generic single-step fallback
        return json.dumps({
            "id": "wf_generic_task",
            "goal": user_input[:200],
            "inputs": {"source_file": "input.txt"},
            "steps": [
                {"n": 1, "tool": "read_file", "args": {"path": "$source_file"}},
            ],
            "version": 1,
            "confidence": 0.4,
            "description": "Demo fallback: generic single-step workflow"
        })


# ===========================================================================
# SELF-TEST
# Usage:  python core/teach.py
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  RECALLIS -- Teach Module Test")
    print("=" * 60)

    test_inputs = [
        "Every Friday, summarize report.csv and email my manager.",
        "Back up data.csv to backup.csv every day.",
    ]

    for i, user_text in enumerate(test_inputs, 1):
        print(f"\n[TEST {i}] Input: \"{user_text}\"")
        print("-" * 40)
        try:
            workflow = teach(user_text)
            print(f"  PASSED -- Workflow '{workflow.id}' created.")
            print(f"     Goal       : {workflow.goal}")
            print(f"     Steps      : {len(workflow.steps)}")
            print(f"     Confidence : {workflow.confidence}")
            print(f"     Provider   : LLM or demo fallback")
        except Exception as e:
            print(f"  ERROR -- {e}")

    print("\n" + "=" * 60)
    print("  Teach module test complete.")
    print("=" * 60)
