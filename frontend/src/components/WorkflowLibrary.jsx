import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchWorkflows, runWorkflow } from '../api';
import { Play } from 'lucide-react';

export default function WorkflowLibrary() {
  const [workflows, setWorkflows] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchWorkflows().then(setWorkflows).catch(console.error);
  }, []);

  const handleRun = async (id) => {
    try {
      const runState = await runWorkflow(id);
      navigate(`/run/${id}`, { state: { initialRunState: runState } });
    } catch (e) {
      alert("Failed to start workflow");
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Workflow Library</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {workflows.map(w => (
          <div key={w.id} className="glass-card flex flex-col justify-between">
            <div>
              <h2 className="text-xl font-bold text-white mb-2">{w.id}</h2>
              <p className="text-gray-400 text-sm mb-4">{w.goal}</p>
            </div>
            <button 
              onClick={() => handleRun(w.id)}
              className="btn-primary w-full mt-4"
            >
              <Play size={18} /> RUN WORKFLOW
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
