import React from 'react';

export function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-2xl border border-srec-border shadow-card hover:shadow-card-hover hover:-translate-y-[1px] transition-all duration-300 ${className}`}>
      {children}
    </div>
  );
}

// Button component moved to ./UI/Button.jsx
export { default as Button } from './UI/Button';

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse bg-srec-backgroundAlt rounded-xl ${className}`} />;
}

export function Badge({ children, type = 'default', variant = 'status' }) {
  // Normalize type to title case for matching keys (e.g. "low" -> "Low")
  const normalize = (str) => {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  };

  const key = normalize(type);

  // Priority badge styles with pastel gradients
  const priorityStyles = {
    Low: 'bg-gradient-to-r from-priority-low/30 to-priority-low/20 text-green-700 border border-priority-low/40',
    Medium: 'bg-gradient-to-r from-priority-medium/30 to-priority-medium/20 text-amber-700 border border-priority-medium/40',
    High: 'bg-gradient-to-r from-priority-high/30 to-priority-high/20 text-orange-700 border border-priority-high/40',
    Critical: 'bg-gradient-to-r from-priority-critical/30 to-priority-critical/20 text-red-700 border border-priority-critical/40',
  };

  // Status badge styles with pastel gradients  
  const statusStyles = {
    Raised: 'bg-gradient-to-r from-status-raised/30 to-status-raised/20 text-blue-700 border border-status-raised/40',
    Opened: 'bg-gradient-to-r from-status-opened/30 to-status-opened/20 text-teal-700 border border-status-opened/40',
    Reviewed: 'bg-gradient-to-r from-status-reviewed/30 to-status-reviewed/20 text-violet-700 border border-status-reviewed/40',
    Closed: 'bg-gradient-to-r from-status-closed/30 to-status-closed/20 text-gray-600 border border-status-closed/40',
    Pending: 'bg-gradient-to-r from-status-raised/30 to-status-raised/20 text-blue-700 border border-status-raised/40',
    Resolved: 'bg-gradient-to-r from-brand/20 to-brand/10 text-brand-dark border border-brand/30',
    Rejected: 'bg-gradient-to-r from-red-100 to-red-50 text-red-700 border border-red-200',
  };

  // Category badge style
  const categoryStyle = 'bg-gradient-to-r from-brand/15 to-brand/5 text-brand-dark border border-brand/20';

  // Determine which style set to use
  let badgeStyle = 'bg-gray-100 text-gray-700 border border-gray-200';

  if (variant === 'priority' && priorityStyles[key]) {
    badgeStyle = priorityStyles[key];
  } else if (variant === 'status' && statusStyles[key]) {
    badgeStyle = statusStyles[key];
  } else if (variant === 'category') {
    badgeStyle = categoryStyle;
  } else if (statusStyles[key]) {
    badgeStyle = statusStyles[key];
  } else if (priorityStyles[key]) {
    badgeStyle = priorityStyles[key];
  }

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold shadow-sm backdrop-blur-sm ${badgeStyle}`}>
      {children}
    </span>
  );
}

// Raise Issue Button — SREC green, matches brand, stays prominent as CTA
export function RaiseButton({ children, className = '', ...props }) {
  return (
    <button
      className={`
        inline-flex items-center justify-center gap-2
        px-6 py-3.5
        bg-gradient-to-b from-[#1f7a4a] via-srec-primary to-[#155e32]
        text-white font-semibold
        rounded-xl
        shadow-[0_4px_14px_-2px_rgba(22,101,52,0.45),0_1px_3px_rgba(0,0,0,0.12),inset_0_1px_0_rgba(255,255,255,0.1)]
        border border-[#1a6b3c]/60
        transition-all duration-200
        will-change-transform
        hover:shadow-[0_6px_20px_-2px_rgba(22,101,52,0.55),0_2px_6px_rgba(0,0,0,0.1)] hover:-translate-y-0.5
        active:translate-y-0 active:scale-[0.98] active:shadow-none
        focus:outline-none focus:ring-2 focus:ring-srec-primary/50 focus:ring-offset-2
        ${className}
      `}
      {...props}
    >
      {children}
    </button>
  );
}

export function Select({ value, onChange, options, placeholder, className = '' }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full appearance-none rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 shadow-neu-light focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50 ${className}`}
      >
        {placeholder && <option value="" className="bg-white text-gray-900">{placeholder}</option>}
        {options.map((opt) => {
          const value = typeof opt === 'object' ? opt.value : opt;
          const label = typeof opt === 'object' ? opt.label : opt;
          return (
            <option key={value} value={value} className="bg-white text-gray-900">{label}</option>
          );
        })}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );
}

export function Stat({ label, value, color = 'brand' }) {
  const colorClasses = {
    brand: 'bg-brand/5 text-brand-dark border border-brand/10',
    green: 'bg-brand/5 text-brand-dark border border-brand/10',
    amber: 'bg-accent/5 text-accent-dark border border-accent/10',
    red: 'bg-red-50 text-red-700 border border-red-100',
  }[color] || 'bg-gray-50 text-gray-700';

  return (
    <div className={`rounded-xl ${colorClasses} p-4 shadow-sm`}>
      <div className="text-sm font-medium opacity-80">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}

// Single source of truth for status colors — used everywhere
export const STATUS_COLORS = {
  'Raised':      { bg: 'bg-blue-50',    text: 'text-blue-700',    border: 'border-blue-100',    dot: 'bg-blue-400' },
  'In Progress': { bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-100',   dot: 'bg-amber-400' },
  'Resolved':    { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-100', dot: 'bg-emerald-500' },
  'Closed':      { bg: 'bg-gray-100',   text: 'text-gray-500',    border: 'border-gray-200',    dot: 'bg-gray-400' },
  'Spam':        { bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-100',     dot: 'bg-red-400' },
};

export function StatusBadge({ status, className = '' }) {
  const c = STATUS_COLORS[status] || STATUS_COLORS['Raised'];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${c.bg} ${c.text} ${c.border} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {status}
    </span>
  );
}

export function PriorityBadge({ priority, className = '' }) {
  const config = {
    'Critical': { bg: 'bg-red-50',    text: 'text-red-700' },
    'High':     { bg: 'bg-orange-50', text: 'text-orange-700' },
    'Medium':   { bg: 'bg-amber-50',  text: 'text-amber-700' },
    'Low':      { bg: 'bg-gray-50',   text: 'text-gray-600' },
  };
  const c = config[priority] || config['Low'];
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text} ${className}`}>
      {priority}
    </span>
  );
}

// Export new components
export { default as EliteButton } from './UI/EliteButton';
export { default as StatsCard } from './UI/StatsCard';
