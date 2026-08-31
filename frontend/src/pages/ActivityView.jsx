import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchHistory } from '../api';
import StatusBadge from '../components/common/StatusBadge';
import { Clock, ArrowRight, ShieldCheck, FileText } from 'lucide-react';

export default function ActivityView() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHistory()
      .then(data => {
        // data might be a dict mapped by run_id, or an array depending on api implementation
        // Assuming the current api returns a dict of run_ids -> receipt
        const list = Array.isArray(data) ? data : Object.values(data);
        // Sort by end_time descending
        list.sort((a, b) => new Date(b.end_time || 0) - new Date(a.end_time || 0));
        setHistory(list);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="flex flex-col w-full animate-fade-in">
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-white mb-2">Activity History</h1>
        <p className="text-gray-400">Immutable ledger of all verified engine executions.</p>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <Clock size={32} className="text-primary animate-spin" />
          <p className="text-gray-400 text-sm">Loading activity ledger...</p>
        </div>
      ) : history.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 glass-panel border-dashed text-center p-8">
          <div className="w-12 h-12 rounded-full bg-surface border border-border flex items-center justify-center mb-4 text-gray-500">
            <ShieldCheck size={20} />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">No activity recorded</h3>
          <p className="text-sm text-gray-400 max-w-sm mb-6">The engine has not executed any workflows yet.</p>
          <Link to="/demo" className="btn-primary">Run a Demo</Link>
        </div>
      ) : (
        <div className="flex flex-col gap-3 max-w-5xl">
          {history.map((run) => (
            <div 
              key={run.run_id} 
              onClick={() => navigate(`/receipt/${run.run_id}`)}
              className="glass-panel p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:border-primary/40 hover:bg-white/[0.03] transition-all group"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="hidden sm:flex w-10 h-10 rounded-full bg-surface border border-border items-center justify-center text-gray-500 group-hover:text-primary transition-colors">
                  <FileText size={16} />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-white font-medium truncate pr-4">{run.workflow_id}</span>
                  <span className="text-xs font-mono text-gray-500 truncate">{run.run_id}</span>
                </div>
              </div>
              
              <div className="flex items-center justify-between md:justify-end gap-6 shrink-0">
                <div className="text-xs font-mono text-gray-400 hidden md:block">
                  {new Date(run.end_time || Date.now()).toLocaleString()}
                </div>
                <StatusBadge status={run.status} />
                <ArrowRight size={16} className="text-gray-600 group-hover:text-primary transition-colors hidden sm:block" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
