import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { runWorkflow, stepRun, verifyRun, approveRun, getRunStatus } from '../api';
import StatusBadge from '../components/common/StatusBadge';
import { Loader2, CheckCircle, AlertTriangle, ShieldAlert, XCircle, ArrowRight, FileText, ArrowLeft, Zap, Terminal } from 'lucide-react';

const PHASES = [
  'PREFLIGHT', 'CONTEXT', 'TRUST', 'RISK', 'DECISION', 'EXECUTION', 'VERIFICATION'
];

export default function ExecutionView() {
  const { workflowId } = useParams();
  const navigate = useNavigate();
  
  const [runId, setRunId] = useState(null);
  const [runState, setRunState] = useState(null);
  const [error, setError] = useState(null);
  
  const logsEndRef = useRef(null);
  const initialized = useRef(false);
  const processingRef = useRef(false);

  // 1. Initialize Run
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    
    runWorkflow(workflowId)
      .then(data => setRunId(data.run_id))
      .catch(err => setError(err.message || 'Failed to initialize workflow'));
  }, [workflowId]);

  // 2. State Machine Polling & Execution
  useEffect(() => {
    if (!runId || error) return;

    let mounted = true;
    
    const checkStateAndAdvance = async () => {
      if (processingRef.current) return;
      try {
        const state = await getRunStatus(runId);
        if (!mounted) return;
        setRunState(state);
        
        // Auto-navigate to receipt if completed
        if (state.status === 'COMPLETED' || state.status === 'WAITING_FOR_MOBILE_ACTION') {
          setTimeout(() => {
            if (mounted) navigate(`/receipt/${runId}`);
          }, 3000);
        }
        
        if (state.status === 'RUNNING') {
          processingRef.current = true;
          // Advance the state machine
          if (state.phase === 'VERIFICATION') {
            await verifyRun(runId);
          } else {
            await stepRun(runId);
          }
          // The next polling cycle will pick up the new state/logs
          processingRef.current = false;
        }
      } catch (err) {
        if (mounted) setError(err.message);
        processingRef.current = false;
      }
    };

    const interval = setInterval(checkStateAndAdvance, 500);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [runId, error, navigate]);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [runState?.logs]);

  const handleApprove = async () => {
    try {
      await approveRun(runId, 'APPROVE');
      setRunState(prev => ({ ...prev, status: 'RUNNING' }));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCancel = async () => {
    try {
      await approveRun(runId, 'REJECT');
      setRunState(prev => ({ ...prev, status: 'CANCELLED' }));
    } catch (err) {
      setError(err.message);
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center animate-fade-in">
        <XCircle size={48} className="text-danger mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Execution Failed</h2>
        <p className="text-gray-400 mb-6">{error}</p>
        <button onClick={() => navigate('/workflows')} className="btn-secondary">Return to Library</button>
      </div>
    );
  }

  if (!runState) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4 animate-fade-in">
        <Loader2 size={32} className="text-primary animate-spin" />
        <p className="text-gray-400 font-medium tracking-wide">Initializing Recallyn Engine...</p>
      </div>
    );
  }

  const isTerminal = ['COMPLETED', 'FAILED', 'BLOCKED', 'CANCELLED', 'WAITING_FOR_MOBILE_ACTION'].includes(runState.status);
  
  const currentPhaseIndex = PHASES.indexOf(runState.phase);
  const displayPhaseIndex = currentPhaseIndex === -1 ? PHASES.length : currentPhaseIndex;

  // Extract the most recent log for the live heading animation
  const logs = runState.logs || [];
  const latestLog = logs.length > 0 ? logs[logs.length - 1].msg : "Initializing sandbox...";

  return (
    <div className="max-w-4xl mx-auto w-full animate-fade-in pb-20">
      
      <div className="flex items-center justify-between mb-8 pb-6 border-b border-border/50">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2 tracking-tight">Workflow Execution</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm font-mono text-gray-500">{runId}</span>
            <StatusBadge status={runState.status} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Left Column: Timeline */}
        <div className="md:col-span-1 border-r border-border/30 pr-6">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-6">Engine State</h3>
          <div className="flex flex-col gap-6">
            {PHASES.map((phase, i) => {
              const isCompleted = isTerminal ? true : i < displayPhaseIndex;
              const isActive = !isTerminal && i === displayPhaseIndex;
              
              let Icon = isCompleted ? CheckCircle : (isActive ? Loader2 : null);
              
              return (
                <div key={phase} className="flex items-center gap-4 relative group transition-transform hover:translate-x-1 duration-200">
                  {i !== PHASES.length - 1 && (
                    <div className={`absolute top-6 left-2.5 w-px h-8 transition-colors duration-500 ${isCompleted ? 'bg-primary' : 'bg-border'}`} />
                  )}
                  
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center z-10 transition-all duration-300
                    ${isCompleted ? 'bg-primary text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]' : isActive ? 'bg-primary/20 text-primary border border-primary/50 scale-110' : 'bg-surface border border-border text-transparent'}
                  `}>
                    {Icon ? <Icon size={12} className={isActive ? 'animate-spin' : ''} /> : <div className="w-1.5 h-1.5 rounded-full bg-gray-600" />}
                  </div>
                  <span className={`text-sm font-medium transition-colors duration-300 ${isCompleted ? 'text-gray-300' : isActive ? 'text-white font-bold' : 'text-gray-600'}`}>
                    {phase}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Dynamic View */}
        <div className="md:col-span-2 relative min-h-[400px]">
          
          {/* Running State: Live Logs */}
          {!isTerminal && runState.status !== 'WAITING_FOR_APPROVAL' && (
            <div className="glass-panel h-full flex flex-col p-6 animate-fade-in hover:-translate-y-1 transition-transform duration-300">
              <div className="flex items-center gap-3 mb-6 bg-surface/50 p-4 rounded-xl border border-primary/20 shadow-[0_0_15px_rgba(99,102,241,0.1)]">
                <div className="relative flex items-center justify-center w-8 h-8 rounded-full bg-primary/10">
                  <Loader2 size={16} className="text-primary animate-spin absolute" />
                  <div className="w-2 h-2 rounded-full bg-primary animate-ping" />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-gray-400 font-mono uppercase tracking-wider mb-0.5">Live Execution</span>
                  <h3 className="text-sm font-semibold text-white truncate max-w-[250px] md:max-w-[350px]">
                    {latestLog}
                  </h3>
                </div>
              </div>
              
              <div className="flex-1 bg-[#0a0c14] border border-border/50 rounded-xl p-4 overflow-y-auto font-mono text-xs text-gray-400 space-y-3 relative shadow-inner scroll-smooth custom-scrollbar max-h-[350px]">
                <div className="flex items-center gap-2 text-primary/50 border-b border-border/30 pb-2 mb-2 sticky top-0 bg-[#0a0c14] z-10">
                  <Terminal size={12} /> Console Output
                </div>
                
                {logs.length === 0 ? (
                  <span className="opacity-50 flex items-center gap-2"><Loader2 size={12} className="animate-spin"/> Initializing context...</span>
                ) : (
                  logs.map((log, i) => (
                    <div key={i} className="flex gap-3 animate-slide-up hover:bg-white/5 p-1.5 rounded transition-colors duration-200">
                      <span className={`font-bold w-[4.5rem] shrink-0 ${log.type === 'error' ? 'text-danger' : log.type === 'warning' ? 'text-warning' : log.type === 'success' ? 'text-success' : 'text-primary/70'}`}>
                        [{log.type || 'info'}]
                      </span>
                      <span className="text-gray-300 break-words">{log.msg}</span>
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            </div>
          )}

          {/* Approval Modal */}
          {runState.status === 'WAITING_FOR_APPROVAL' && (
            <div className="glass-panel border-warning/50 h-full flex flex-col items-center justify-center p-8 text-center animate-fade-in shadow-[0_0_40px_rgba(245,158,11,0.15)] relative overflow-hidden hover:-translate-y-1 transition-transform duration-300">
              <div className="absolute top-0 left-0 w-full h-1 bg-warning animate-pulse" />
              <ShieldAlert size={48} className="text-warning mb-6 animate-[pulseSlow_2s_ease-in-out_infinite]" />
              <h2 className="text-2xl font-bold text-white mb-2">Action Requires Approval</h2>
              <p className="text-gray-400 mb-8 max-w-md">
                The engine has paused execution because this task involves high-risk actions. Please verify before continuing.
              </p>
              
              <div className="w-full bg-surface border border-border rounded-lg p-5 text-left mb-8 hover:border-warning/30 transition-colors duration-300">
                <div className="flex items-center justify-between border-b border-border/50 pb-3 mb-3">
                  <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Exact Task</span>
                  <span className="text-xs font-mono text-white bg-white/10 px-2 py-1 rounded flex items-center gap-2">
                    <Zap size={12} className="text-primary" />
                    {runState.pending_action?.tool || 'System Action'}
                  </span>
                </div>
                <div className="flex flex-col gap-3">
                  <div>
                    <span className="text-xs text-gray-500 uppercase block mb-1">Risk Level</span>
                    <span className={`text-sm font-bold flex items-center gap-1.5 ${runState.pending_action?.risk === 'HIGH' ? 'text-danger' : 'text-warning'}`}>
                      <AlertTriangle size={14} /> {runState.pending_action?.risk || 'HIGH'}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 uppercase block mb-1">Why approval is needed</span>
                    <p className="text-sm text-gray-200 bg-white/5 p-3 rounded-md border border-white/5 leading-relaxed">
                      {runState.pending_action?.reason || 'This action has high consequences and requires human-in-the-loop authorization.'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-4 w-full">
                <button onClick={handleCancel} className="btn-secondary flex-1 py-3 hover:bg-danger/10 hover:text-danger hover:border-danger/30 transition-colors">Reject Task</button>
                <button onClick={handleApprove} className="btn bg-warning text-black hover:bg-yellow-400 flex-1 py-3 font-bold shadow-[0_0_16px_rgba(245,158,11,0.4)] transition-all active:scale-95">
                  Approve Action
                </button>
              </div>
            </div>
          )}

          {/* Terminal / Success State */}
          {isTerminal && (
            <div className="glass-panel h-full flex flex-col p-8 items-center justify-center text-center animate-fade-in relative overflow-hidden hover:-translate-y-1 transition-transform duration-300">
              <div className={`absolute top-0 left-0 w-full h-2 ${runState.status === 'FAILED' || runState.status === 'BLOCKED' ? 'bg-danger' : 'bg-success'}`} />
              
              {runState.status === 'FAILED' || runState.status === 'BLOCKED' ? (
                <XCircle size={56} className="text-danger mb-6" />
              ) : (
                <CheckCircle size={56} className="text-success mb-6" />
              )}
              
              <h2 className="text-3xl font-bold text-white mb-2">
                {runState.status === 'COMPLETED' ? 'Workflow Completed' : runState.status === 'WAITING_FOR_MOBILE_ACTION' ? 'Handoff Completed' : runState.status}
              </h2>
              <p className="text-gray-400 mb-8">The engine has reached a terminal state and secured the memory context.</p>
              
              {(runState.status === 'COMPLETED' || runState.status === 'WAITING_FOR_MOBILE_ACTION') && (
                <div className="flex items-center gap-3 text-sm text-gray-400 mb-10 bg-surface/50 py-2 px-4 rounded-full border border-border/50 animate-pulse">
                  <Loader2 size={14} className="animate-spin text-primary" />
                  Opening cryptographic receipt...
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-4 w-full">
                <button onClick={() => navigate(`/workflows`)} className="btn-secondary flex-1 py-3 hover:bg-white/10 transition-colors">
                  <ArrowLeft size={16} /> Back to Library
                </button>
                <button onClick={() => navigate(`/receipt/${runId}`)} className="btn-primary flex-[2] py-3 shadow-lg hover:shadow-primary/40 transition-shadow">
                  <FileText size={16} /> View Execution Receipt
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
