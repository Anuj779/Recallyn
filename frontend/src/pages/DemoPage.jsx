import React from 'react';
import { Link } from 'react-router-dom';
import { Target, ArrowRight } from 'lucide-react';

export default function DemoPage() {
  const demos = [
    { id: 'wf_demo_business_report', title: 'Weekly Business Report', desc: 'Standard execution. Summarize a file and send it safely.', tag: 'Normal' },
    { id: 'wf_demo_context_drift', title: 'Context Drift', desc: 'The target manager changed since Recallyn last ran.', tag: 'Drift' },
    { id: 'wf_demo_safety_check', title: 'Safety Check', desc: 'Malicious instructions injected into a document.', tag: 'Blocked' },
    { id: 'wf_demo_missing_input', title: 'Missing Input', desc: 'Required input file was moved or deleted.', tag: 'Preflight' },
    { id: 'wf_demo_verification_failure', title: 'Verification Failure', desc: 'Action completes but post-condition is missing.', tag: 'Recovery' },
    { id: 'wf_demo_meeting_prep', title: 'Meeting Preparation', desc: 'Multi-tool planning combining Calendar, Contacts, and Maps.', tag: 'Complex' }
  ];

  return (
    <div className="flex flex-col w-full animate-fade-in pb-20">
      <div className="text-center mb-16">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">Try Recallyn</h1>
        <p className="text-gray-400 text-lg">See how the engine thinks, validates, and acts across different scenarios.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
        {demos.map(demo => (
          <div key={demo.id} className="glass-panel p-6 flex flex-col hover:border-primary/50 transition-colors group">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold px-2 py-1 rounded bg-white/5 text-gray-300">{demo.tag}</span>
              <Target size={16} className="text-gray-500 group-hover:text-primary transition-colors" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">{demo.title}</h3>
            <p className="text-sm text-gray-400 mb-8 flex-1 leading-relaxed">{demo.desc}</p>
            <Link to={`/run/${demo.id}`} className="btn-secondary w-full group-hover:bg-primary group-hover:text-white group-hover:border-primary">
              Run Demo <ArrowRight size={16} />
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
