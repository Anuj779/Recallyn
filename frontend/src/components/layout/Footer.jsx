import React from 'react';
import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="w-full border-t border-border bg-surface mt-24">
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-12 flex flex-col md:flex-row justify-between gap-12">
        <div className="max-w-xs">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-6 h-6 rounded bg-primary flex items-center justify-center text-xs font-bold text-white">R</div>
            <span className="text-lg font-bold text-white tracking-wide">RECALLYN</span>
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">
            Teach once. Recall intelligently. Act safely.
          </p>
          <p className="text-xs text-gray-500 mt-6">
            &copy; {new Date().getFullYear()} Recallyn Workflow Engine.
          </p>
        </div>
        
        <div className="flex gap-12 md:gap-24">
          <div className="flex flex-col gap-3">
            <span className="text-sm font-semibold text-white mb-2">Product</span>
            <Link to="/" className="text-sm text-gray-400 hover:text-white transition-colors">How it Works</Link>
            <Link to="/demo" className="text-sm text-gray-400 hover:text-white transition-colors">Demo</Link>
            <Link to="/workflows" className="text-sm text-gray-400 hover:text-white transition-colors">Workflows</Link>
          </div>
          <div className="flex flex-col gap-3">
            <span className="text-sm font-semibold text-white mb-2">Resources</span>
            <a href="#" className="text-sm text-gray-400 hover:text-white transition-colors">Documentation</a>
            <a href="https://github.com/Anuj779/Recallyn" target="_blank" rel="noreferrer" className="text-sm text-gray-400 hover:text-white transition-colors">GitHub</a>
          </div>
          <div className="flex flex-col gap-3">
            <span className="text-sm font-semibold text-white mb-2">Status</span>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span className="w-2 h-2 rounded-full bg-success"></span>
              All Systems Operational
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
