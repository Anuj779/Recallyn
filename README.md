# RECALLYN

> **Teach once. Recall intelligently. Act safely.**

🌐 Live Demo: [http://recallyn.vercel.app](https://recallyn.vercel.app)
📦 **GitHub:** [https://github.com/Anuj779/Recallyn](https://github.com/Anuj779/Recallyn)
📌 **MVP Status:** Web Demonstration (Core Engine validation)

---

## What is Recallyn?
Recallyn is a context-aware personal workflow agent. It learns your tasks once, intelligently adapts to changing context, automatically controls consequential actions, and provides cryptographic verification of outcomes.

### The Problem
Traditional automation (like Zapier or cron jobs) is completely blind. If you tell an automation to "email the weekly report every Friday", it will blindly send an empty, broken, or inaccurate report even if the company went bankrupt on Thursday. Traditional AI agents, on the other hand, are highly capable but act as unpredictable "black boxes," taking high-risk actions without human verification.

### The Solution
Recallyn bridges the gap between rigid automation and unpredictable AI. By wrapping an intelligent LLM brain in a deterministic, strict state machine, Recallyn checks the current world context, assesses the risk of every tool, and automatically asks for human approval before executing anything dangerous. 

---

## How It Works: The 5 Phases

Recallyn's execution pipeline is divided into five strict phases to ensure absolute safety and traceability:

1. **🧠 Teach + Remember** - Describe your workflow in plain English. Recallyn compiles it into a rigid JSON schema and stores it in memory.
2. **🤖 Agent + Tools** - The agent dynamically selects the necessary tools (file readers, API callers) required to achieve the goal.
3. **🌍 Context + Drift** - Before executing, Recallyn compares the current state of the world to the original context when the workflow was taught. If things have drifted drastically, it halts.
4. **🔐 Trust + Risk** - Every tool is categorized by risk (e.g., `delete_file` is HIGH risk). Consequential actions always pause and trigger a Human-in-the-Loop (HITL) approval step.
5. **✅ Verify + Recover + Evolve** - Post-execution, the agent verifies the outcome, saves an immutable Cryptographic Receipt, and updates its memory for next time.

---

## MVP Status & Positioning

**Current: Web Demonstration**
This repository currently contains the **Recallyn Web MVP**. This React + FastAPI application is designed strictly as a visual demonstration of the Recallyn Core Engine. It allows users to visualize the state machine, interact with the risk modals, and view execution receipts.

**Future: Native Android Layer**
The Web MVP is *not* the final product. The next phase of the Recallyn roadmap is a **Native Android Application** (scaffolded in `android/`). This will provide mobile-native interactions, deep OS integration, and seamless handoffs via iQOO / Office Kit.

---

## Demo Workflows
The MVP ships with 6 Golden Scenarios showcasing the engine's capabilities:
1. **Weekly Business Report** (Standard execution)
2. **Meeting Preparation** (Data ingestion & summarization)
3. **Context Drift** (Catching outdated variables)
4. **Safety Check** (Intercepting dangerous instructions)
5. **Missing Input Recovery** (Handling missing files)
6. **Verification Failure** (Ensuring state consistency)

---

## Architecture & Tech Stack

**Core Engine:** Pure Python (State Machine, Risk Engine, Memory, Drift Detection)
**Backend Layer:** FastAPI
**Frontend Layer:** React 18, Vite, Tailwind CSS v3, Lucide Icons
**AI Integration:** Groq (LLaMA 3) / Google Gemini (via `langchain`)

### Repository Structure
```text
Recallyn/
├── core/                  # The Recallyn Brain (Logic, Risk, Memory)
├── data/                  # Local memory & history files
├── demo/                  # Fictional demo assets
├── frontend/              # React + Vite Web Demonstration UI
├── android/               # Future Native Mobile Layer
├── scripts/               # E2E Test suites
├── api.py                 # FastAPI layer
├── config.py              # Environment configuration
└── render.yaml            # Deployment specs
```

---

## Local Setup

### 1. Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Add your `GROQ_API_KEY` or `GEMINI_API_KEY`. (Note: Never commit your real API keys!)

### 2. Backend (FastAPI)
```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows
pip install -r requirements.txt
python -m uvicorn api:app --reload --port 8000
```

### 3. Frontend (React)
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173` in your browser.

---

## Deployment

We utilize a decoupled architecture to ensure the polling engine retains memory:
* **Frontend:** Deployed globally on [Vercel](https://vercel.com).
* **Backend:** Deployed as a persistent service on [Render](https://render.com) (configured via `render.yaml`).

---

## Security & Limitations
* **Security:** Recallyn is designed with a strict default-deny policy for high-risk tools.
* **Limitations:** The current MVP utilizes local JSON files (`run_history.json`, `workflows.json`) for memory persistence. In a production environment, this should be migrated to PostgreSQL/Redis.

---

## Roadmap
* [x] **Phase 1:** Core Logic Engine & Web Demonstration MVP
* [ ] **Phase 2:** Native Android Application Integration
* [ ] **Phase 3:** iQOO optimization & hardware acceleration
* [ ] **Phase 4:** Office Kit ecosystem integration
