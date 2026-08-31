import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { stepRun, verifyRun, approveRun } from '../api';
import { Check, Loader, AlertTriangle, XCircle, Slash, FileText } from 'lucide-react';

const STAGES = [
  { id: 'PREFLIGHT', label: 'Pre-flight' },
  { id: 'CONTEXT', label: 'Context' },
  { id: 'TRUST', label: 'Trust' },
  { id: 'RISK', label: 'Risk' },
  { id: 'DECISION', label: 'Decision' },
  { id: 'EXECUTION', label: 'Execution' },
  { id: 'VERIFICATION', label: 'Verification' }
];

export default function ExecutionView() {
  const { workflowId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [runState, setRunState] = useState(location.state?.initialRunState || null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!runState) {
      navigate('/');
      return;
    }

    let isMounted = true;
    const tick = async () => {
      try {
        const { status, phase, run_id } = runState;
        
        if (status === 'RUNNING') {
          if (phase === 'VERIFICATION') {
            const nextState = await verifyRun(run_id);
            if (isMounted) setRunState(nextState);
          } else {
            const nextState = await stepRun(run_id);
            if (isMounted) setRunState(nextState);
          }
        }
      } catch (err) {
        if (isMounted) setError(err.toString());
      }
    };

    if (runState.status === 'RUNNING') {
      const timeout = setTimeout(tick, 500);
      return () => clearTimeout(timeout);
    }
    
    return () => { isMounted = false; };
  }, [runState, navigate]);

  if (!runState) return null;

  const { status, phase, run_id, workflow } = runState;
  const isTerminal = ['COMPLETED', 'FAILED', 'BLOCKED', 'CANCELLED', 'UNKNOWN'].includes(status);
  
  // Pipeline UI calculation
  let activeIndex = STAGES.findIndex(s => s.id === phase);
  if (isTerminal || phase === 'COMPLETED') activeIndex = STAGES.length;

  const handleApprove = async (decision) => {
    const nextState = await approveRun(run_id, decision);
    setRunState(nextState);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2">Executing: {workflowId}</h1>
        <p className="text-gray-400">{workflow?.goal}</p>
      </div>

      {/* PIPELINE */}
      <div className="glass-card mb-8">
        <div className="flex justify-between items-center mb-4 relative">
          <div className="absolute top-1/2 left-4 right-4 h-1 bg-white/10 -z-10 rounded"></div>
          {STAGES.map((s, i) => {
            let state = 'pending';
            if (i < activeIndex) state = 'completed';
            else if (i === activeIndex) state = 'active';
            
            return (
              <div key={s.id} className="flex flex-col items-center gap-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300
                  ${state === 'completed' ? 'bg-success text-white' : ''}
                  ${state === 'active' ? 'bg-primary ring-4 ring-primary/30 animate-pulse text-white' : ''}
                  ${state === 'pending' ? 'bg-gray-800 text-gray-500' : ''}
                `}>
                  {state === 'completed' ? <Check size={16} /> : (i + 1)}
                </div>
                <span className={`text-xs ${state === 'active' ? 'text-primary font-bold' : 'text-gray-500'}`}>
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* APPROVAL CARD */}
      {status === 'WAITING_FOR_APPROVAL' && (
        <div className="glass-card border-warning/50 bg-warning/10">
          <h3 className="text-xl font-bold text-warning flex items-center gap-2 mb-4">
            <AlertTriangle /> Action Requires Approval
          </h3>
          <p className="mb-6">{runState.pending_action?.details || 'Please confirm the next step.'}</p>
          <div className="flex gap-4">
            <button onClick={() => handleApprove('APPROVE')} className="btn-primary flex-1 bg-success hover:bg-success/80">Approve</button>
            <button onClick={() => handleApprove('CANCEL')} className="btn-secondary flex-1">Cancel</button>
          </div>
        </div>
      )}

      {/* TERMINAL RESULT CARD */}
      {isTerminal && (
        <div className={`glass-card text-center py-12 ${status === 'COMPLETED' ? 'border-success/30' : 'border-danger/30'}`}>
          <div className="flex justify-center mb-4">
            {status === 'COMPLETED' && <Check size={64} className="text-success" />}
            {status === 'FAILED' && <XCircle size={64} className="text-danger" />}
            {status === 'BLOCKED' && <Slash size={64} className="text-danger" />}
            {status === 'CANCELLED' && <AlertTriangle size={64} className="text-gray-400" />}
          </div>
          <h2 className="text-3xl font-bold mb-6 tracking-wide">
            {status === 'COMPLETED' && '✅ WORKFLOW COMPLETED'}
            {status === 'FAILED' && '❌ WORKFLOW FAILED'}
            {status === 'BLOCKED' && '🚫 ACTION BLOCKED'}
            {status === 'CANCELLED' && '⛔ WORKFLOW CANCELLED'}
          </h2>
          
          {status === 'COMPLETED' && (
            <div className="max-w-md mx-auto text-left bg-black/20 p-6 rounded-xl space-y-3 mb-8">
              <div className="flex justify-between">
                <span className="text-gray-400">Steps Completed:</span>
                <span className="font-medium text-white">{runState.step_idx} / {workflow?.steps?.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Target:</span>
                <span className="font-medium text-white">{Object.values(workflow?.inputs || {})[0] || 'Unknown'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Decision:</span>
                <span className="font-medium text-white">Approved</span>
              </div>
              <div className="flex justify-between border-t border-white/10 pt-3 mt-3">
                <span className="text-gray-400">Verification:</span>
                <span className="font-bold text-success">✅ VERIFIED</span>
              </div>
            </div>
          )}
          
          <div className="flex gap-4 justify-center">
            <button onClick={() => navigate(`/receipt/${run_id}`)} className="btn-primary">
              <FileText size={18} /> View Execution Receipt
            </button>
            <button onClick={() => navigate('/')} className="btn-secondary">
              Back to Workflows
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
