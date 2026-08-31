import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Play, Plus, Brain, Shield, CheckCircle, ArrowRight, Zap, Target, Activity, FileSearch } from 'lucide-react';

const Hero = () => {
  return (
    <section className="relative pt-20 pb-32 flex flex-col items-center justify-center text-center">
      {/* Background ambient glow specific to hero */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />
      
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-gray-300 mb-8 animate-fade-in">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
        Recallyn MVP 1.0 is Live
      </div>
      
      <h1 className="text-5xl md:text-7xl font-bold text-white tracking-tight leading-tight mb-6 animate-slide-up" style={{animationDelay: '0.1s'}}>
        Teach once.<br />
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-primaryHover">
          Recall intelligently.
        </span><br />
        Act safely.
      </h1>
      
      <p className="max-w-2xl text-lg md:text-xl text-gray-400 mb-10 leading-relaxed animate-slide-up" style={{animationDelay: '0.2s'}}>
        Recallyn remembers how you work, checks whether your context has changed, controls consequential actions, and verifies what actually happened.
      </p>
      
      <div className="flex flex-col sm:flex-row items-center gap-4 animate-slide-up" style={{animationDelay: '0.3s'}}>
        <Link to="/demo" className="btn-primary px-8 py-3 text-base">
          <Play size={18} fill="currentColor" /> Try Demo
        </Link>
        <Link to="/workflows/create" className="btn-secondary px-8 py-3 text-base bg-surface hover:bg-surfaceHover">
          <Plus size={18} /> Create Workflow
        </Link>
      </div>

      {/* Abstract Animated Workflow Visual */}
      <div className="mt-20 relative w-full max-w-4xl h-32 flex items-center justify-between px-8 glass-panel animate-fade-in" style={{animationDelay: '0.5s'}}>
        <div className="absolute top-1/2 left-8 right-8 h-[2px] bg-border -translate-y-1/2 overflow-hidden">
          <div className="w-1/3 h-full bg-gradient-to-r from-transparent via-primary to-transparent animate-[gradientFlow_3s_linear_infinite]" />
        </div>
        
        {['Memory', 'Context', 'Decision', 'Action', 'Verification'].map((step, i) => (
          <div key={step} className="relative z-10 flex flex-col items-center gap-3">
            <div className="w-4 h-4 rounded-full bg-surface border-2 border-primary flex items-center justify-center shadow-[0_0_12px_rgba(99,102,241,0.5)]">
              <div className="w-1.5 h-1.5 bg-white rounded-full" />
            </div>
            <span className="text-xs font-semibold tracking-wider text-gray-400 uppercase">{step}</span>
          </div>
        ))}
      </div>
    </section>
  );
};

const HowItWorks = () => {
  const phases = [
    { num: '01', title: 'Teach + Remember', icon: <Brain size={20}/>, desc: 'Provide instructions once. Recallyn commits the goal, steps, and targets to memory.' },
    { num: '02', title: 'Agent + Tools', icon: <Zap size={20}/>, desc: 'The engine autonomously plans and executes using standard modular tools.' },
    { num: '03', title: 'Context + Drift', icon: <Activity size={20}/>, desc: 'Continuously detects if the real-world state has shifted since you taught it.' },
    { num: '04', title: 'Trust + Risk', icon: <Shield size={20}/>, desc: 'Evaluates the blast radius of actions and pauses for cryptographic human approval if needed.' },
    { num: '05', title: 'Verify + Evolve', icon: <CheckCircle size={20}/>, desc: 'Deterministically proves the action succeeded and updates memory for next time.' }
  ];

  const [active, setActive] = useState(0);

  return (
    <section className="py-24 border-t border-border/50">
      <div className="text-center mb-16">
        <h2 className="text-3xl font-bold mb-4">How Recallyn Works</h2>
        <p className="text-gray-400">A strict deterministic state machine protecting autonomous execution.</p>
      </div>

      <div className="flex flex-col md:flex-row gap-4 max-w-5xl mx-auto">
        {phases.map((phase, i) => (
          <div 
            key={phase.num}
            onMouseEnter={() => setActive(i)}
            className={`relative p-6 rounded-2xl transition-all duration-300 cursor-pointer overflow-hidden
              ${active === i ? 'bg-surface/80 border-primary/50 shadow-[0_0_30px_rgba(99,102,241,0.1)] flex-[2]' : 'bg-surface/30 border-border/50 flex-1 hover:bg-surface/50'}
              border border-solid backdrop-blur-sm
            `}
          >
            <div className={`text-sm font-bold mb-4 transition-colors ${active === i ? 'text-primary' : 'text-gray-500'}`}>
              {phase.num}
            </div>
            <div className={`flex items-center gap-3 mb-2 font-semibold ${active === i ? 'text-white' : 'text-gray-300'}`}>
              {phase.icon} <span className="whitespace-nowrap">{phase.title}</span>
            </div>
            <div className={`text-sm text-gray-400 mt-4 leading-relaxed transition-all duration-300 ${active === i ? 'opacity-100 h-auto' : 'opacity-0 h-0 overflow-hidden md:opacity-100 md:h-auto md:max-h-0'}`}>
              {phase.desc}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

const Capabilities = () => {
  const caps = [
    { title: 'Memory', desc: 'Immutable knowledge graph of organizational workflows.' },
    { title: 'Context-Aware', desc: 'Detects semantic shifts in data before acting blindly.' },
    { title: 'Trust-Aware', desc: 'Validates origin and provenance of every instruction.' },
    { title: 'Risk-Aware', desc: 'Calculates consequence severity and invokes Human-in-the-loop.' },
    { title: 'Outcome Verification', desc: 'Does not trust LLM outputs; deterministically checks API state.' },
    { title: 'Safe Evolution', desc: 'Learns from failures and human corrections automatically.' }
  ];

  return (
    <section className="py-24 border-t border-border/50">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {caps.map(cap => (
          <div key={cap.title} className="p-6 rounded-xl bg-white/[0.02] border border-border hover:bg-white/[0.04] transition-colors">
            <h3 className="text-lg font-semibold text-white mb-2">{cap.title}</h3>
            <p className="text-sm text-gray-400 leading-relaxed">{cap.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

const DemoShowcase = () => {
  const demos = [
    { title: 'Weekly Business Report', desc: 'Standard execution. Summarize a file and send it safely.', tag: 'Normal' },
    { title: 'Meeting Preparation', desc: 'Multi-tool planning combining Calendar, Contacts, and Maps.', tag: 'Complex' },
    { title: 'Context Drift', desc: 'The target manager changed since Recallyn last ran.', tag: 'Drift' },
    { title: 'Safety Check', desc: 'Malicious instructions injected into a document.', tag: 'Blocked' },
    { title: 'Missing Input', desc: 'Required input file was moved or deleted.', tag: 'Preflight' },
    { title: 'Verification Failure', desc: 'Action completes but post-condition is missing.', tag: 'Recovery' }
  ];

  return (
    <section className="py-24 border-t border-border/50 text-center">
      <h2 className="text-4xl font-bold mb-4">TRY RECALLYN</h2>
      <p className="text-gray-400 mb-16 text-lg">See how Recallyn thinks before it acts.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto text-left">
        {demos.map(demo => (
          <div key={demo.title} className="glass-panel p-6 flex flex-col hover:border-primary/50 transition-colors group">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold px-2 py-1 rounded bg-white/5 text-gray-300">{demo.tag}</span>
              <Target size={16} className="text-gray-500 group-hover:text-primary transition-colors" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">{demo.title}</h3>
            <p className="text-sm text-gray-400 mb-8 flex-1">{demo.desc}</p>
            <Link to="/demo" className="btn-secondary w-full group-hover:bg-primary group-hover:text-white group-hover:border-primary">
              Run Demo <ArrowRight size={16} />
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
};

export default function LandingPage() {
  return (
    <div className="flex flex-col w-full">
      <Hero />
      <HowItWorks />
      <Capabilities />
      <DemoShowcase />
    </div>
  );
}
