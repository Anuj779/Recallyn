import requests
import time
import sys

API_URL = "http://localhost:8000"
report = []

def log(msg, status="PASS"):
    print(f"[{status}] {msg}")
    report.append(f"- **{status}**: {msg}")

try:
    # Test 1: API Health
    res = requests.get(f"{API_URL}/health")
    assert res.status_code == 200, "Health check failed"
    log("API Health Check /health returned 200 OK")

    # Test 2: Fetch Workflows
    res = requests.get(f"{API_URL}/workflows")
    assert res.status_code == 200, "Failed to fetch workflows"
    workflows = res.json()
    assert len(workflows) > 0, "Workflow list is empty"
    log(f"API /workflows returned {len(workflows)} workflows successfully")

    # Test 3: Initialize Run
    target_wf = "wf_demo_business_report"
    res = requests.post(f"{API_URL}/workflows/{target_wf}/run")
    assert res.status_code == 200, f"Failed to start workflow {target_wf}"
    run_id = res.json()["run_id"]
    log(f"Engine initialized execution state successfully (Run ID: {run_id})")

    # Test 4: Execution Loop (Step & Approve)
    while True:
        state = requests.get(f"{API_URL}/runs/{run_id}/status").json()
        if state["status"] not in ["RUNNING", "WAITING_FOR_APPROVAL"]:
            break
            
        if state["status"] == "WAITING_FOR_APPROVAL":
            log(f"Phase {state['phase']}: Successfully hit Approval Checkpoint")
            requests.post(f"{API_URL}/runs/{run_id}/approve", json={"decision": "APPROVE"})
        elif state["phase"] == "VERIFICATION":
            requests.post(f"{API_URL}/runs/{run_id}/verify")
        else:
            requests.post(f"{API_URL}/runs/{run_id}/step")
        time.sleep(0.2)
        
    final = requests.get(f"{API_URL}/runs/{run_id}/receipt").json()
    if final["status"] in ["COMPLETED", "WAITING_FOR_MOBILE_ACTION"]:
        log(f"End-to-End Execution verified. Final State: {final['status']}")
    else:
        log(f"Execution failed with state: {final['status']}", "FAIL")
        sys.exit(1)

    with open("test_results.md", "w") as f:
        f.write("\n".join(report))

except Exception as e:
    log(str(e), "FAIL")
    sys.exit(1)
