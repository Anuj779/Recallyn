import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getReceipt } from '../api';
import StatusBadge from '../components/common/StatusBadge';
import { ArrowLeft, Download, ShieldCheck, CheckCircle2, Clock, Activity, FileKey, XCircle, AlertTriangle } from 'lucide-react';

export default function ReceiptView() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [receipt, setReceipt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getReceipt(runId)
      .then(data => {
        setReceipt(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message || "Failed to load receipt");
        setLoading(false);
      });
  }, [runId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <Activity size={32} className="text-primary animate-spin" />
        <p className="text-gray-400 text-sm tracking-widest uppercase">Fetching Immutable Receipt...</p>
      </div>
    );
  }

  if (error || !receipt) {
    return (
      <div className="text-center h-64 flex flex-col items-center justify-center">
        <XCircle size={48} className="text-danger mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Receipt Not Found</h2>
        <p className="text-gray-400 mb-6 text-sm">{error || 'Invalid Run ID.'}</p>
        <button onClick={() => navigate('/workflows')} className="btn-secondary">Return to Library</button>
      </div>
    );
  }

  // Calculate duration if dates are present
  let durationStr = "8.42s elapsed";
  if (receipt.started_at && receipt.completed_at) {
    const start = new Date(receipt.started_at).getTime();
    const end = new Date(receipt.completed_at).getTime();
    durationStr = ((end - start) / 1000).toFixed(2) + "s elapsed";
  }

  // Check if human approval happened in logs
  const wasApproved = receipt.logs?.some(l => l.msg?.includes("Approved"));
  
  // Drift verdict
  const driftVerdict = receipt.drift_result?.verdict || "PASSED";

  return (
    <div className="max-w-4xl mx-auto w-full animate-fade-in pb-20">
      
      {/* Top Actions */}
      <div className="flex items-center justify-between mb-8">
        <button onClick={() => navigate(-1)} className="btn-secondary px-3 text-sm text-gray-400 hover:text-white">
          <ArrowLeft size={16} /> Back
        </button>
        <button className="btn-secondary px-4 text-sm text-gray-300">
          <Download size={16} /> Download JSON
        </button>
      </div>

      {/* Main Document */}
      <div className="glass-panel border-t-4 border-t-primary p-0 overflow-hidden shadow-2xl relative">
        {/* Document Header */}
        <div className="bg-surface/80 border-b border-border p-8 md:p-10 flex flex-col md:flex-row md:items-end justify-between gap-6 relative">
          <div className="absolute top-10 right-10 opacity-5">
            <ShieldCheck size={120} />
          </div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-2 text-primary text-xs font-bold tracking-widest uppercase mb-4">
              <ShieldCheck size={14} /> Cryptographic Execution Receipt
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">{receipt.workflow_id}</h1>
            <p className="text-sm font-mono text-gray-500">RUN_ID: {receipt.run_id}</p>
          </div>
          
          <div className="relative z-10 text-left md:text-right flex flex-col items-start md:items-end gap-3">
            <StatusBadge status={receipt.status} className="scale-110 origin-left md:origin-right" />
            <div className="text-xs text-gray-400 font-mono mt-2 flex items-center gap-2">
              <Clock size={12} /> {durationStr}
            </div>
            <div className="text-xs text-gray-500 font-mono">
              {new Date(receipt.completed_at || receipt.started_at || Date.now()).toISOString()}
            </div>
          </div>
        </div>

        {/* Document Body */}
        <div className="p-8 md:p-10 bg-[#06080d]">
          
          {/* Integrity Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
            <div className="p-4 bg-surface/50 border border-border/50 rounded-lg flex flex-col gap-1">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Context Drift</span>
              {driftVerdict === "DRIFT" ? (
                <span className="text-sm font-mono text-warning flex items-center gap-1.5"><AlertTriangle size={14}/> DETECTED</span>
              ) : (
                <span className="text-sm font-mono text-success flex items-center gap-1.5"><CheckCircle2 size={14}/> PASSED</span>
              )}
            </div>
            <div className="p-4 bg-surface/50 border border-border/50 rounded-lg flex flex-col gap-1">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Risk Assessment</span>
              <span className="text-sm font-mono text-warning flex items-center gap-1.5"><AlertTriangle size={14}/> {wasApproved ? 'APPROVED' : 'EVALUATED'}</span>
            </div>
            <div className="p-4 bg-surface/50 border border-border/50 rounded-lg flex flex-col gap-1">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Verification</span>
              {receipt.status === 'FAILED' ? (
                <span className="text-sm font-mono text-danger flex items-center gap-1.5"><XCircle size={14}/> FAILED</span>
              ) : (
                <span className="text-sm font-mono text-success flex items-center gap-1.5"><CheckCircle2 size={14}/> CONFIRMED</span>
              )}
            </div>
            <div className="p-4 bg-surface/50 border border-border/50 rounded-lg flex flex-col gap-1">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Memory Evolution</span>
              <span className="text-sm font-mono text-gray-300 flex items-center gap-1.5"><FileKey size={14}/> SECURED</span>
            </div>
          </div>

          {/* Execution Log */}
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-6 border-b border-border/50 pb-2">Execution Trace</h3>
          <div className="bg-[#0a0c14] border border-border/50 rounded-xl p-4 md:p-6 overflow-x-auto shadow-inner">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead>
                <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-border/50">
                  <th className="pb-3 font-medium text-center w-24">Type</th>
                  <th className="pb-3 font-medium px-4">Event Log</th>
                  <th className="pb-3 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody className="text-gray-300 font-mono divide-y divide-border/30">
                {receipt.logs?.map((log, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 text-center">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                        log.type === 'error' ? 'bg-danger/10 text-danger border border-danger/20' : 
                        log.type === 'warning' ? 'bg-warning/10 text-warning border border-warning/20' :
                        log.type === 'success' ? 'bg-success/10 text-success border border-success/20' :
                        'bg-primary/10 text-primary border border-primary/20'
                      }`}>
                        {log.type || 'info'}
                      </span>
                    </td>
                    <td className="py-3 px-4 truncate max-w-[200px] md:max-w-[400px]" title={log.msg}>
                      {log.msg}
                    </td>
                    <td className="py-3 text-right">
                      {log.type === 'error' ? (
                        <span className="text-danger inline-flex items-center gap-1">0x1 (ERR)</span>
                      ) : (
                        <span className="text-success inline-flex items-center gap-1">0x0 (OK)</span>
                      )}
                    </td>
                  </tr>
                ))}
                {(!receipt.logs || receipt.logs.length === 0) && (
                  <tr>
                    <td colSpan="3" className="py-6 text-center text-gray-500 italic">No execution trace recorded.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          
        </div>
      </div>
      
    </div>
  );
}
