import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchHistory } from '../api';
import { FileText, CheckCircle, XCircle } from 'lucide-react';

export default function ActivityView() {
  const [history, setHistory] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchHistory().then(data => setHistory(data.reverse())).catch(console.error);
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold mb-6">Activity History</h2>
      
      {history.length === 0 ? (
        <div className="glass-card text-center py-12 text-gray-400">No execution history found.</div>
      ) : (
        <div className="space-y-4">
          {history.map((run) => (
            <div key={run.run_id} onClick={() => navigate(`/receipt/${run.run_id}`)} 
                 className="glass-card hover:bg-white/5 cursor-pointer transition-colors flex items-center justify-between p-4">
              <div className="flex items-center gap-4">
                {run.status === 'COMPLETED' ? <CheckCircle className="text-success" /> : <XCircle className="text-danger" />}
                <div>
                  <div className="font-bold text-white">{run.workflow_id}</div>
                  <div className="text-xs text-gray-400 font-mono mt-1">{run.run_id}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className={`text-sm font-medium ${run.status === 'COMPLETED' ? 'text-success' : 'text-danger'}`}>
                  {run.status}
                </span>
                <FileText className="text-gray-500" size={18} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
