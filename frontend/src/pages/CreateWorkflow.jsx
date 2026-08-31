import React, { useState } from 'react';
import { Paperclip, Image as ImageIcon, Sparkles, Settings2, Loader2, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { teachWorkflow } from '../api';

export default function CreateWorkflow() {
  const [prompt, setPrompt] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleCreate = async () => {
    if (!prompt.trim()) {
      setError("Please describe a workflow before creating.");
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      await teachWorkflow(prompt);
      // On success, redirect to the library to see the new workflow
      navigate('/workflows');
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || "Failed to teach workflow. Check your backend/LLM configuration.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full animate-fade-in pb-20">
      <div className="mb-10 text-center">
        <h1 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">What should Recallyn remember?</h1>
        <p className="text-gray-400">Describe the workflow in plain English. Recallyn will automatically compile the modular steps, constraints, and necessary tools.</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-danger/10 border border-danger/30 rounded-lg flex items-start gap-3 text-danger text-sm">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      <div className="glass-panel p-2 mb-8 focus-within:border-primary/50 transition-colors shadow-xl">
        <textarea 
          className="w-full bg-transparent text-white placeholder-gray-500 p-4 resize-none focus:outline-none min-h-[160px] text-lg"
          placeholder='e.g. "Every Friday, read my sales_report.csv, summarize the key metrics, and send it safely to my manager..."'
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          disabled={loading}
        />
        
        <div className="flex items-center justify-between p-2 border-t border-border/50 bg-surface/30 rounded-b-xl">
          <div className="flex items-center gap-2">
            <button type="button" className="btn-secondary py-1.5 px-3 text-xs bg-surface hover:bg-white/10 text-gray-400 hover:text-white transition-colors" disabled={loading}>
              <Paperclip size={14} /> Add File
            </button>
            <button type="button" className="btn-secondary py-1.5 px-3 text-xs bg-surface hover:bg-white/10 text-gray-400 hover:text-white transition-colors" disabled={loading}>
              <ImageIcon size={14} /> Add Image
            </button>
          </div>
          <button 
            onClick={handleCreate} 
            disabled={loading}
            className="btn-primary py-2 px-5 shadow-[0_0_12px_rgba(99,102,241,0.3)] hover:shadow-[0_0_20px_rgba(99,102,241,0.5)] transition-all flex items-center gap-2"
          >
            {loading ? (
              <><Loader2 size={16} className="animate-spin" /> Compiling Engine...</>
            ) : (
              <><Sparkles size={16} /> Create Workflow</>
            )}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-6 cursor-pointer text-sm text-gray-400 hover:text-primary transition-colors select-none" onClick={() => setShowAdvanced(!showAdvanced)}>
        <Settings2 size={16} /> 
        <span className="font-medium">{showAdvanced ? 'Hide advanced settings' : 'Show advanced settings'}</span>
      </div>

      {showAdvanced && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-slide-up">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-300">Workflow Name (Optional)</label>
            <input type="text" disabled={loading} placeholder="e.g. Weekly Sales Summary" className="bg-surface/80 border border-border rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary/50 shadow-inner" />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-300">Target Entity / Recipient</label>
            <input type="text" disabled={loading} placeholder="e.g. Priya Sharma" className="bg-surface/80 border border-border rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary/50 shadow-inner" />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-300">Trigger Schedule</label>
            <input type="text" disabled={loading} placeholder="e.g. Every Friday at 5 PM" className="bg-surface/80 border border-border rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary/50 shadow-inner" />
          </div>
        </div>
      )}
    </div>
  );
}
