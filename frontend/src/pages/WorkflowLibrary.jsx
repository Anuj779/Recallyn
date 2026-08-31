import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchWorkflows } from '../api';
import StatusBadge from '../components/common/StatusBadge';
import { Play, Search, Filter, GitMerge, FileText, User, Clock, ArrowRight, Loader2 } from 'lucide-react';

const formatIdToName = (id) => {
  return id.replace('wf_demo_', '').replace('wf_', '').split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
};

const WorkflowCard = ({ workflow }) => {
  const navigate = useNavigate();
  const name = workflow.name || formatIdToName(workflow.id);
  
  return (
    <div className="glass-panel p-6 flex flex-col hover:-translate-y-1 hover:border-primary/50 transition-all duration-300 group shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <StatusBadge status="READY" />
        <span className="text-xs text-gray-500 font-mono bg-surface px-2 py-1 rounded-md border border-border/50">
          v{workflow.version || '1.0'}
        </span>
      </div>
      
      <h3 className="text-lg font-bold text-white mb-2 group-hover:text-primary transition-colors">{name}</h3>
      <p className="text-sm text-gray-400 mb-6 flex-1 line-clamp-2">{workflow.goal || workflow.description || 'No description provided.'}</p>
      
      <div className="flex flex-col gap-3 mb-6 p-4 rounded-lg bg-surface/50 border border-border/50">
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <FileText size={14} className="text-primary/70 shrink-0" />
          <span className="truncate">{workflow.source || workflow.expected_inputs?.[0] || 'Dynamic / No input file'}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <User size={14} className="text-primary/70 shrink-0" />
          <span className="truncate">{workflow.recipient || workflow.permissions?.target_entities?.[0] || 'Recallyn Engine'}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <GitMerge size={14} className="text-primary/70 shrink-0" />
          <span>{workflow.steps || workflow.execution_plan?.length || 0} modular steps</span>
        </div>
      </div>
      
      <div className="flex items-center gap-3">
        <button 
          onClick={() => navigate(`/run/${workflow.id}`)}
          className="btn-primary flex-1 py-2.5 text-sm shadow-lg hover:shadow-primary/20"
        >
          <Play size={16} fill="currentColor" /> Run Workflow
        </button>
      </div>
    </div>
  );
};

export default function WorkflowLibrary() {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchWorkflows()
      .then(data => {
        const list = Array.isArray(data) ? data : Object.values(data);
        setWorkflows(list);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch workflows:", err);
        setLoading(false);
      });
  }, []);

  const filtered = workflows.filter(w => {
    const textToSearch = (w.name || w.goal || w.id || '').toLowerCase();
    return textToSearch.includes(search.toLowerCase());
  });

  return (
    <div className="flex flex-col w-full animate-fade-in pb-20">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10 border-b border-border/50 pb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Workflow Library</h1>
          <p className="text-gray-400">Manage, inspect, and execute your taught workflows.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input 
              type="text" 
              placeholder="Search workflows..." 
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-surface/80 border border-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary/50 transition-colors w-64 md:w-80 shadow-inner"
            />
          </div>
          <button className="btn-secondary h-[42px] px-4 hover:text-white transition-colors">
            <Filter size={16} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <div className="relative">
            <Loader2 size={32} className="text-primary animate-spin" />
            <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full" />
          </div>
          <p className="text-gray-400 text-sm font-medium tracking-wide">Loading workflows from memory...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 glass-panel border-dashed text-center p-8 border-border/50">
          <div className="w-12 h-12 rounded-full bg-surface border border-border flex items-center justify-center mb-4 text-gray-500 shadow-inner">
            <Search size={20} />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">No workflows found</h3>
          <p className="text-sm text-gray-400 max-w-sm mb-6">We couldn't find any workflows matching your search criteria.</p>
          <Link to="/workflows/create" className="btn-primary shadow-lg hover:shadow-primary/20">Create Workflow</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filtered.map(wf => (
            <WorkflowCard key={wf.id} workflow={wf} />
          ))}
        </div>
      )}
    </div>
  );
}
