import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Plus, Command } from 'lucide-react';

export default function Header() {
  const location = useLocation();
  
  const navLinks = [
    { name: 'Home', path: '/' },
    { name: 'Workflows', path: '/workflows' },
    { name: 'Demo', path: '/demo' },
    { name: 'Activity', path: '/activity' },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/60 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-primaryHover flex items-center justify-center text-white font-bold shadow-lg shadow-primary/20 transition-transform group-hover:scale-105">
            R
          </div>
          <span className="text-xl font-bold tracking-wide text-white">RECALLYN</span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-6 absolute left-1/2 -translate-x-1/2">
          {navLinks.map(link => {
            const isActive = location.pathname === link.path || (link.path !== '/' && location.pathname.startsWith(link.path));
            return (
              <Link 
                key={link.name} 
                to={link.path}
                className={`text-sm font-medium transition-colors ${isActive ? 'text-white' : 'text-gray-400 hover:text-gray-200'}`}
              >
                {link.name}
              </Link>
            );
          })}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-4">
          <Link to="/workflows/create" className="btn-primary hidden sm:flex">
            <Plus size={16} /> Create Workflow
          </Link>
          {/* Mobile menu trigger could go here */}
        </div>
      </div>
    </header>
  );
}
