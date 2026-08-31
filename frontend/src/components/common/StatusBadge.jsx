import React from 'react';
import { CheckCircle, AlertTriangle, XCircle, Loader2, PlayCircle, Info, Check } from 'lucide-react';

export default function StatusBadge({ status, text, className="" }) {
  const config = {
    READY: { icon: PlayCircle, color: 'text-info', bg: 'bg-info/10', border: 'border-info/20' },
    RUNNING: { icon: Loader2, color: 'text-primary', bg: 'bg-primary/10', border: 'border-primary/20', animate: 'animate-spin' },
    COMPLETED: { icon: Check, color: 'text-success', bg: 'bg-success/10', border: 'border-success/20' },
    VERIFIED: { icon: CheckCircle, color: 'text-success', bg: 'bg-success/10', border: 'border-success/20' },
    BLOCKED: { icon: XCircle, color: 'text-danger', bg: 'bg-danger/10', border: 'border-danger/20' },
    FAILED: { icon: XCircle, color: 'text-danger', bg: 'bg-danger/10', border: 'border-danger/20' },
    WAITING_FOR_APPROVAL: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/20' },
    ATTENTION: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/20' },
    DEFAULT: { icon: Info, color: 'text-gray-400', bg: 'bg-white/5', border: 'border-white/10' }
  };
  
  const c = config[status] || config.DEFAULT;
  const Icon = c.icon;
  
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-bold tracking-wide uppercase border ${c.bg} ${c.color} ${c.border} ${className}`}>
      <Icon size={12} className={c.animate || ''} />
      {text || status.replace(/_/g, ' ')}
    </div>
  );
}
