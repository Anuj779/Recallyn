import shutil
import uuid
from fastapi import UploadFile, File
import os
import sys
from typing import Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))
from teach import teach
from memory import list_workflows, load_workflow, save_workflow
from preflight import run_preflight
from agent import resolve_args
from verifier import verify_postconditions

app = FastAPI(title="Recallyn API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for runs (MVP level)
RUNS: Dict[str, dict] = {}

class TeachRequest(BaseModel):
    prompt: str

class RunRequest(BaseModel):
    workflow_id: str

class ApproveRequest(BaseModel):
    decision: str
    file_id: str = None
    original_file_id: str = None # "APPROVE" or "CANCEL"

@app.get("/health")
def health_check():
    return {"status": "ok"}


from pathlib import Path
ROOT_DIR = Path(__file__).parent
UPLOAD_DIR = ROOT_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = f"file_{uuid.uuid4().hex[:8]}"
    safe_filename = file.filename.replace(" ", "_")
    file_path = UPLOAD_DIR / f"{file_id}_{safe_filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "file_id": file_id,
        "filename": safe_filename,
        "size": file_path.stat().st_size,
        "source": "ANDROID_UPLOAD"
    }

@app.get("/workflows")
def get_workflows():
    wfs = list_workflows()
    result = []
    for w in wfs:
        recipient = w.inputs.get("recipient_role") or w.inputs.get("recipient_email") or "Unknown"
        source = w.inputs.get("source_file") or w.inputs.get("report_path") or "Data Stream"
        tools = " -> ".join([s.tool for s in w.steps])
        result.append({
            "id": w.id,
            "goal": w.goal,
            "steps": len(w.steps),
            "version": w.version,
            "recipient": recipient,
            "source": source,
            "trigger": "Manual / Ad-hoc",
            "risk": "Medium",
            "tools": tools,
            "last_run": "Verified",
            "is_demo": w.is_demo
        })
    return result

@app.get("/workflows/{wf_id}")
def get_workflow(wf_id: str):
    wf = load_workflow(wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf

@app.post("/workflows/teach")
def teach_workflow(req: TeachRequest):
    try:
        wf = teach(req.prompt)
        save_workflow(wf)
        return {"status": "success", "workflow": wf}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/workflows/{wf_id}/run")
def start_run(wf_id: str):
    wf = load_workflow(wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    run_id = str(uuid.uuid4())
    run_state = {
        "run_id": run_id,
        "workflow_id": wf_id,
        "workflow": wf,
        "phase": "PREFLIGHT",
        "step_idx": 0,
        "results": {},
        "status": "RUNNING",
        "logs": [],
        "pending_action": None,
        "drift_result": None,
        "current_eval": None,
        "resolved_args": None,
        "retry_count": 0,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "completed_at": None
    }
    RUNS[run_id] = run_state
    
    # Automatically execute preflight
    report = run_preflight(wf)
    run_state["drift_result"] = report.drift_result
    if not report.can_proceed:
        if report.checks["inputs"].status == "MISSING_FILE":
            run_state["status"] = "WAITING_FOR_FILE_REPLACEMENT"
            run_state["logs"].append({"type": "error", "msg": report.checks["inputs"].messages[0]})
        else:
            run_state["status"] = "FAILED"
            run_state["logs"].append({"type": "error", "msg": "Preflight failed."})
    else:
        run_state["phase"] = "EXECUTION"
        run_state["logs"].append({"type": "info", "msg": "Preflight passed."})
        
    return _serialize_run(run_state)

@app.post("/runs/{run_id}/approve")
def approve_run(run_id: str, req: ApproveRequest):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
        
    rs = RUNS[run_id]
    
    if rs["status"] == "WAITING_FOR_FILE_REPLACEMENT":
        if req.decision == "CANCEL":
            rs["status"] = "FAILED"
            rs["logs"].append({"type": "error", "msg": "Action denied by user."})
            return _serialize_run(rs)
            
        if req.file_id and req.original_file_id:
            # Inject new file into workflow memory for this run
            wf = rs["workflow"]
            if req.original_file_id in wf.inputs.values():
                for k, v in wf.inputs.items():
                    if v == req.original_file_id:
                        wf.inputs[k] = req.file_id
            else:
                # If not mapped cleanly, just append
                wf.inputs["replacement"] = req.file_id
                
            rs["logs"].append({"type": "info", "msg": f"File replaced with {req.file_id}"})
            
            # Re-run preflight
            rs["status"] = "RUNNING"
            report = run_preflight(wf)
            rs["drift_result"] = report.drift_result
            if not report.can_proceed:
                if report.checks["inputs"].status == "MISSING_FILE":
                    rs["status"] = "WAITING_FOR_FILE_REPLACEMENT"
                    rs["logs"].append({"type": "error", "msg": report.checks["inputs"].messages[0]})
                else:
                    rs["status"] = "FAILED"
                    rs["logs"].append({"type": "error", "msg": "Preflight failed after replacement."})
            else:
                rs["phase"] = "EXECUTION"
                rs["logs"].append({"type": "info", "msg": "Preflight passed."})
        return _serialize_run(rs)

    if rs["status"] != "WAITING_FOR_APPROVAL":
        return _serialize_run(rs)
        
    if req.decision == "CANCEL":
        rs["status"] = "FAILED"
        rs["logs"].append({"type": "error", "msg": "Action denied by user."})
        rs["pending_action"] = None
        return _serialize_run(rs)
        
    rs["status"] = "RUNNING"
    pending_type = rs["pending_action"]["type"]
    rs["pending_action"] = None
    
    if pending_type == "DRIFT":
        rs["phase"] = "EXECUTION"
        rs["logs"].append({"type": "info", "msg": "Context drift approved."})
        return _serialize_run(rs)
    elif pending_type == "RISK":
        rs["logs"].append({"type": "info", "msg": "Security action approved."})
        return _execute_current_tool(rs)
        
    return _serialize_run(rs)

class MobileActionResultRequest(BaseModel):
    status: str
    action_type: str

@app.post("/runs/{run_id}/mobile-action-result")
def submit_mobile_action_result(run_id: str, req: MobileActionResultRequest):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
        
    rs = RUNS[run_id]
    
    if rs["status"] != "WAITING_FOR_MOBILE_ACTION":
        return _serialize_run(rs)
        
    rs["logs"].append({"type": "info", "msg": f"Mobile action '{req.action_type}' finished with status: {req.status}"})
    
    if req.status == "HANDOFF_COMPLETED":
        rs["status"] = "RUNNING"
        rs["pending_action"] = None
        rs["step_idx"] += 1
    else:
        rs["status"] = "FAILED"
        rs["pending_action"] = None
        rs["logs"].append({"type": "error", "msg": f"Mobile action failed: {req.status}"})
        
    return _serialize_run(rs)

@app.post("/runs/{run_id}/step")
def step_run(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
        
    rs = RUNS[run_id]
    
    if rs["status"] != "RUNNING" or rs["phase"] != "EXECUTION":
        return _serialize_run(rs)
        
    wf = rs["workflow"]
    if rs["step_idx"] >= len(wf.steps):
        rs["phase"] = "VERIFICATION"
        return _serialize_run(rs)
        
    step = wf.steps[rs["step_idx"]]
    
    # 1. Resolve arguments
    try:
        resolved_args = resolve_args(step.args, wf.inputs or {}, rs["results"])
        rs["resolved_args"] = resolved_args
    except Exception as e:
        rs["status"] = "FAILED"
        rs["logs"].append({"type": "error", "msg": f"Argument resolution failed: {e}"})
        return _serialize_run(rs)
        
    # 2. Evaluate Trust and Risk
    from core.provenance import classify_workflow_step
    from core.decide import evaluate, Decision
    
    source = classify_workflow_step(wf.id)
    verdict = rs["drift_result"].verdict if rs["drift_result"] else "UNKNOWN"
    
    decision_result = evaluate(step.tool, source, verdict, wf, resolved_args)
    
    if decision_result.decision == Decision.BLOCK:
        rs["status"] = "BLOCKED"
        rs["logs"].append({"type": "error", "msg": f"Action blocked: {decision_result.reason}"})
        return _serialize_run(rs)
        
    elif decision_result.decision == Decision.ASK:
        rs["status"] = "WAITING_FOR_APPROVAL"
        rs["pending_action"] = {
            "type": "RISK",
            "tool": step.tool,
            "risk": decision_result.risk_level,
            "reason": decision_result.reason
        }
        return _serialize_run(rs)
        
    # 3. If EXECUTE, run the tool
    return _execute_current_tool(rs)

def _save_receipt(rs):
    import json
    from pathlib import Path
    history_file = Path("data/run_history.json")
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except:
            pass
    history.append(_serialize_run(rs))
    history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

@app.post("/runs/{run_id}/verify")
def verify_run(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
        
    rs = RUNS[run_id]
    if rs["phase"] != "VERIFICATION":
        return _serialize_run(rs)
        
    wf = rs["workflow"]
    
    # Mark complete time
    rs["completed_at"] = datetime.utcnow().isoformat() + "Z"
    
    if not wf.postconditions:
        rs["status"] = "COMPLETED"
        _save_receipt(rs)
        return _serialize_run(rs)
        
    resolved_pcs = []
    for pc in wf.postconditions:
        exp = resolve_args(pc.get("expect", {}), wf.inputs or {}, rs["results"])
        resolved_pcs.append({"check": pc.get("check"), "expect": exp})
        
    v_status, v_details = verify_postconditions(resolved_pcs)
    if v_status == "VERIFIED":
        rs["status"] = "COMPLETED"
        rs["logs"].append({"type": "success", "msg": "Verified successfully."})
    else:
        rs["status"] = "FAILED"
        rs["logs"].append({"type": "error", "msg": "Verification failed."})
        
    _save_receipt(rs)
    return _serialize_run(rs)

def _serialize_run(rs):
    drift_val = None
    if rs.get("drift_result"):
        drift_val = {
            "verdict": rs["drift_result"].verdict,
            "details": rs["drift_result"].reason
        }
    return {
        "run_id": rs["run_id"],
        "workflow_id": rs["workflow_id"],
        "workflow": rs["workflow"].model_dump(),
        "phase": rs["phase"],
        "status": rs["status"],
        "step_idx": rs["step_idx"],
        "logs": rs["logs"],
        "pending_action": rs["pending_action"],
        "results": rs.get("results", {}),
        "started_at": rs.get("started_at"),
        "completed_at": rs.get("completed_at"),
        "drift_result": drift_val
    }


def _execute_current_tool(rs):
    wf = rs["workflow"]
    step = wf.steps[rs["step_idx"]]
    from core.tools import get_tool
    fn = get_tool(step.tool)
    
    try:
        result = fn(**rs["resolved_args"])
        if result["success"]:
            rs["results"][f"step{step.n}"] = result
            
            data = result.get("data", {})
            if "action_type" in data:
                # New mobile action contract
                rs["status"] = "WAITING_FOR_MOBILE_ACTION"
                rs["pending_action"] = {
                    "type": "MOBILE_ACTION",
                    "action_type": data["action_type"],
                    "payload": data.get("payload", {})
                }
                rs["logs"].append({"type": "info", "msg": f"Waiting for mobile handoff: {data['action_type']}"})
                return _serialize_run(rs)
            elif "handoff_url" in data:
                # Old mobile action contract
                rs["logs"].append({
                    "type": "handoff",
                    "tool": step.tool,
                    "url": data["handoff_url"],
                    "handoff_type": data.get("handoff_type", "action")
                })
                rs["step_idx"] += 1
            else:
                rs["logs"].append({"type": "success", "msg": f"Completed {step.tool}"})
                rs["step_idx"] += 1
        else:
            # Recovery logic
            from core.recovery import attempt_recovery, classify_failure
            err = result["error"]
            failure_type = classify_failure(err)
            class DummyState: pass
            ds = DummyState()
            ds.retry_count = rs.get("retry_count", 0)
            can_recover, action = attempt_recovery(failure_type, ds)
            rs["retry_count"] = getattr(ds, "retry_count", 0)
            
            if can_recover:
                rs["logs"].append({"type": "warning", "msg": f"Recovering: {action}"})
            else:
                rs["status"] = "FAILED"
                rs["logs"].append({"type": "error", "msg": f"Failed: {err}"})
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        rs["status"] = "FAILED"
        rs["logs"].append({"type": "error", "msg": f"Tool execution failed: {str(e)}"})
        
    return _serialize_run(rs)

@app.get("/history")
def get_history():
    history_file = Path("data/run_history.json")
    if history_file.exists():
        try:
            return json.loads(history_file.read_text(encoding="utf-8"))
        except:
            return []
    return []

@app.get("/runs/{run_id}/status")
def get_run_status(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(RUNS[run_id])

@app.get("/runs/{run_id}/receipt")
def get_run_receipt(run_id: str):
    if run_id in RUNS:
        return _serialize_run(RUNS[run_id])
    history_file = Path("data/run_history.json")
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
            for r in history:
                if r["run_id"] == run_id:
                    return r
        except:
            pass
    raise HTTPException(status_code=404, detail="Receipt not found")
