import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getReceipt } from '../api';
import { ArrowLeft, CheckCircle, XCircle } from 'lucide-react';

export default function ReceiptView() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [receipt, setReceipt] = useState(null);

  useEffect(() => {
    getReceipt(runId).then(setReceipt).catch(console.error);
  }, [runId]);

  if (!receipt) return <div className="text-center p-12">Loading receipt...</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-white flex items-center gap-2 mb-6">
        <ArrowLeft size={16} /> Back
      </button>

      <div className="glass-card">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">Execution Receipt</h2>
          {receipt.status === 'COMPLETED' ? 
            <span className="px-3 py-1 bg-success/20 text-success rounded-full flex items-center gap-2 font-medium">
              <CheckCircle size={16} /> VERIFIED
            </span>
            :
            <span className="px-3 py-1 bg-danger/20 text-danger rounded-full flex items-center gap-2 font-medium">
              <XCircle size={16} /> {receipt.status}
            </span>
          }
        </div>
        
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-black/20 p-4 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Workflow</div>
            <div className="font-medium text-white">{receipt.workflow_id}</div>
          </div>
          <div className="bg-black/20 p-4 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Run ID</div>
            <div className="font-mono text-xs text-white break-all">{receipt.run_id}</div>
          </div>
        </div>

        <h3 className="text-lg font-bold mb-4 border-b border-white/10 pb-2">Execution Logs</h3>
        <div className="space-y-3">
          {receipt.logs?.map((log, i) => (
            <div key={i} className={`p-3 rounded-lg border ${log.type === 'error' ? 'border-danger/30 bg-danger/10 text-danger' : 'border-white/5 bg-black/20 text-gray-300'}`}>
              <div className="font-mono text-sm">{log.msg}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
