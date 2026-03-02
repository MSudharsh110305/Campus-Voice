import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import ExportModal from '../../../components/ExportModal';
import adminService from '../../../services/admin.service';
import complaintService from '../../../services/complaint.service';
import { Card, Skeleton, EliteButton, STATUS_COLORS } from '../../../components/UI';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  BarChart, Bar, LabelList,
} from 'recharts';
import {
  AlertTriangle, CheckCircle, Users, FileText, Activity,
  Download, Star, TrendingUp, Clock,
} from 'lucide-react';

// ── Expanded color palette for charts ──────────────────────────────────────
const PIE_COLORS = [
  '#14532D', '#B8952E', '#22C55E', '#C82828', '#6366F1',
  '#0EA5E9', '#F59E0B', '#10B981', '#8B5CF6', '#EC4899',
];

// ── Dept name → short code mapping ─────────────────────────────────────────
const DEPT_CODE_MAP = {
  'Computer Science & Engineering': 'CSE',
  'Electronics & Communication Engineering': 'ECE',
  'Mechanical Engineering': 'MECH',
  'Electrical & Electronics Engineering': 'EEE',
  'Information Technology': 'IT',
  'Civil Engineering': 'CIVIL',
  'Biomedical Engineering': 'BIO',
  'Aeronautical Engineering': 'AERO',
  'Electronics & Instrumentation Engineering': 'EIE',
  'Robotics and Automation': 'RAA',
  'Management Studies': 'MBA',
  'Artificial Intelligence and Data Science': 'AIDS',
  'M.Tech in Computer Science and Engineering': 'MTECH',
  'English': 'ENG',
  'Physics': 'PHY',
  'Chemistry': 'CHEM',
  'Mathematics': 'MATH',
};

const getDeptCode = (name) => {
  if (DEPT_CODE_MAP[name]) return DEPT_CODE_MAP[name];
  // Extract code from parentheses e.g. "XYZ (ABC)" → "ABC"
  const m = name.match(/\(([A-Z]+)\)/);
  if (m) return m[1];
  // First letters of each word, max 5 chars
  return name.split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0, 5);
};

// ── KPI Card ────────────────────────────────────────────────────────────────
function KPICard({ label, value, icon: Icon, accentColor, sub, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60
                  shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)] overflow-hidden
                  transition-all duration-300
                  ${onClick ? 'cursor-pointer hover:shadow-[0_8px_32px_-4px_rgba(0,0,0,0.12)] hover:-translate-y-0.5 group' : ''}`}
    >
      <div className="flex h-full">
        <div className="w-1 rounded-r-full self-stretch" style={{ background: accentColor }} />
        <div className="p-4 flex-1">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{label}</span>
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-300 group-hover:scale-110 group-hover:shadow-md"
              style={{ background: `${accentColor}14`, color: accentColor }}
            >
              <Icon size={15} />
            </div>
          </div>
          <p className="text-2xl font-heading font-bold text-gray-900 leading-tight animate-count-up">{value ?? '—'}</p>
          {sub && <p className="text-[11px] text-gray-500 mt-1.5 leading-tight">{sub}</p>}
        </div>
      </div>
    </div>
  );
}

// ── Custom donut label (percentage only, no overlap) ─────────────────────────
const renderDonutLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  if (percent < 0.06) return null;
  const RADIAN = Math.PI / 180;
  const r = innerRadius + (outerRadius - innerRadius) * 0.6;
  const x = cx + r * Math.cos(-midAngle * RADIAN);
  const y = cy + r * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight="600">
      {`${Math.round(percent * 100)}%`}
    </text>
  );
};

export default function AdminDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const analyticsRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [publicAnalytics, setPublicAnalytics] = useState(null);
  const [error, setError] = useState(null);
  const [showExport, setShowExport] = useState(false);
  const [analyticsDays, setAnalyticsDays] = useState(30);

  useEffect(() => {
    if (!user || user.role !== 'Admin') return;
    loadAll();
  }, [user]);

  useEffect(() => {
    if (!user || user.role !== 'Admin') return;
    adminService.getAnalytics(analyticsDays).then(setAnalytics).catch(console.error);
  }, [analyticsDays]);

  const loadAll = async () => {
    try {
      setLoading(true);
      setError(null);
      const [ov, an, pa] = await Promise.all([
        adminService.getSystemOverview(),
        adminService.getAnalytics(analyticsDays),
        complaintService.getPublicAnalytics(),
      ]);
      setOverview(ov);
      setAnalytics(an);
      setPublicAnalytics(pa);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-28 rounded-2xl" />)}
        </div>
        <Skeleton className="h-80 rounded-2xl" />
        <div className="grid grid-cols-5 gap-6">
          <Skeleton className="col-span-3 h-64 rounded-2xl" />
          <Skeleton className="col-span-2 h-64 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <AlertTriangle className="text-red-500 mb-4" size={48} />
        <h2 className="text-xl font-bold text-gray-900 mb-2">Dashboard Error</h2>
        <p className="text-gray-500 mb-6">{error}</p>
        <EliteButton onClick={loadAll}>Retry</EliteButton>
      </div>
    );
  }

  // ── Data extraction ───────────────────────────────────────────────────────
  const byStatus = overview?.complaints_by_status || {};
  const byPriority = overview?.complaints_by_priority || {};
  const byCategory = overview?.complaints_by_category || {};

  const totalComplaints = overview?.total_complaints || 0;
  const totalStudents = overview?.total_students || 0;
  const totalAuthorities = overview?.total_authorities || 0;
  const recent7d = overview?.recent_complaints_7d || 0;
  const resolved = byStatus['Resolved'] || 0;
  const criticalCount = byPriority['Critical'] || 0;
  const resolutionRate = totalComplaints > 0 ? Math.round((resolved / totalComplaints) * 100) : 0;

  const dailyData = analytics?.daily_complaints || [];
  const categoryPieData = Object.entries(byCategory).map(([name, value]) => ({ name, value }));
  const avgResolutionH = publicAnalytics?.avg_resolution_hours ?? analytics?.avg_resolution_time_hours;
  const satisfactionAvg = publicAnalytics?.satisfaction_avg;

  // Department bar data — use short codes on axis
  const deptData = Object.entries(publicAnalytics?.top_departments || {})
    .map(([name, value]) => ({ name, code: getDeptCode(name), value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const exportSections = [
    {
      id: 'overview', label: 'System Overview',
      stats: [
        { label: 'Total Complaints', value: totalComplaints },
        { label: 'Total Students', value: totalStudents },
        { label: 'Total Authorities', value: totalAuthorities },
        { label: 'Recent (7 days)', value: recent7d },
        { label: 'Resolved', value: resolved },
        { label: 'Resolution Rate', value: `${resolutionRate}%` },
        { label: 'Critical Issues', value: criticalCount },
      ],
    },
    {
      id: 'by_status', label: 'Complaints by Status',
      tableHeaders: ['Status', 'Count'],
      tableRows: Object.entries(byStatus).map(([s, c]) => [s, c]),
    },
    {
      id: 'by_priority', label: 'Complaints by Priority',
      tableHeaders: ['Priority', 'Count'],
      tableRows: ['Critical', 'High', 'Medium', 'Low'].map(p => [p, byPriority[p] || 0]),
    },
    ...(analytics ? [{
      id: 'analytics', label: `Analytics (Last ${analyticsDays} Days)`,
      stats: [
        { label: 'Total Submitted', value: analytics.total_complaints },
        { label: 'Resolved', value: analytics.resolved_complaints },
        { label: 'Resolution Rate', value: analytics.resolution_rate_percent != null ? `${Math.round(analytics.resolution_rate_percent)}%` : '—' },
        { label: 'Avg Resolution Time', value: analytics.avg_resolution_time_hours != null ? `${Math.round(analytics.avg_resolution_time_hours)}h` : '—' },
      ],
    }] : []),
  ];

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">

      {/* ── HEADER ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-heading font-bold text-gray-900 tracking-tight">Executive Dashboard</h1>
            <p className="text-gray-500 text-sm mt-0.5">Real-time overview of campus grievance resolution</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <EliteButton variant="outline" onClick={loadAll} className="text-sm">Refresh</EliteButton>
            <EliteButton onClick={() => setShowExport(true)} className="flex items-center gap-1.5 text-sm">
              <Download size={14} /> Export
            </EliteButton>
          </div>
        </div>

        {/* Status chips inline in header */}
        <div className="flex flex-wrap gap-2">
          {['Raised', 'In Progress', 'Resolved', 'Closed', 'Spam'].map((s) => {
            const c = STATUS_COLORS[s] || STATUS_COLORS['Raised'];
            return (
              <button
                key={s}
                onClick={() => navigate(`/admin/complaints?status=${encodeURIComponent(s)}`)}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border transition-all hover:-translate-y-px hover:shadow-sm ${c.bg} ${c.border} ${c.text}`}
              >
                <span className="font-bold">{byStatus[s] || 0}</span>
                <span className="opacity-70">{s}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── ROW 1: 6 KPI CARDS ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KPICard
          label="Complaints"
          value={totalComplaints}
          icon={FileText}
          accentColor="#3B82F6"
          sub={`${recent7d} in last 7 days`}
          onClick={() => navigate('/admin/complaints')}
        />
        <KPICard
          label="Resolution Rate"
          value={`${resolutionRate}%`}
          icon={CheckCircle}
          accentColor="#10B981"
          sub={`${resolved} of ${totalComplaints} resolved`}
          onClick={() => analyticsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
        />
        <KPICard
          label="Critical Issues"
          value={criticalCount}
          icon={AlertTriangle}
          accentColor="#EF4444"
          sub={`${byPriority['High'] || 0} High priority`}
          onClick={() => navigate('/admin/complaints?priority=Critical')}
        />
        <KPICard
          label="Avg Resolution"
          value={avgResolutionH != null ? `${Math.round(avgResolutionH)}h` : '—'}
          icon={Clock}
          accentColor="#F59E0B"
          sub="Average time to resolve"
        />
        <KPICard
          label="Satisfaction"
          value={satisfactionAvg != null ? `${satisfactionAvg} ★` : '—'}
          icon={Star}
          accentColor="#B8952E"
          sub="Avg student rating / 5"
        />
        <KPICard
          label="Active Users"
          value={totalStudents + totalAuthorities}
          icon={Users}
          accentColor="#8B5CF6"
          sub={`${totalStudents} students · ${totalAuthorities} staff`}
          onClick={() => navigate('/admin/authorities')}
        />
      </div>

      {/* ── ROW 2: CHARTS ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Daily Trend AreaChart */}
        <Card className="lg:col-span-2 p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Activity size={18} className="text-srec-primary" />
              Complaint Volume
            </h3>
            <div className="flex gap-1">
              {[7, 30].map(d => (
                <button
                  key={d}
                  onClick={() => setAnalyticsDays(d)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                    analyticsDays === d
                      ? 'bg-srec-primary text-white'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                  }`}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>
          <div className="h-60 w-full">
            {dailyData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dailyData}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#14532D" stopOpacity={0.12} />
                      <stop offset="95%" stopColor="#14532D" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 10 }} tickFormatter={v => v?.slice(5)} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 10 }} />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', fontSize: 12 }} />
                  <Area type="monotone" dataKey="count" stroke="#14532D" strokeWidth={2.5} fillOpacity={1} fill="url(#colorCount)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-gray-300 text-sm">No data yet</div>
            )}
          </div>
        </Card>

        {/* Category Donut */}
        <Card className="p-5 shadow-sm border border-gray-100">
          <h3 className="text-base font-bold text-gray-900 mb-4">By Category</h3>
          <div className="h-60 w-full">
            {categoryPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryPieData}
                    cx="50%"
                    cy="45%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                    dataKey="value"
                    labelLine={false}
                    label={renderDonutLabel}
                  >
                    {categoryPieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v, n) => [v, n]} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: 12 }} />
                  <Legend verticalAlign="bottom" height={32} iconSize={8} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-gray-300 text-sm">No data yet</div>
            )}
          </div>
        </Card>
      </div>

      {/* ── ROW 3: DEPT BAR + PRIORITY GRID ────────────────────────────────── */}
      <div ref={analyticsRef} className="scroll-mt-6 grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* Department vertical bar chart */}
        <Card className="lg:col-span-3 p-5 shadow-sm border border-gray-100">
          <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp size={17} className="text-srec-primary" />
            Top Departments
          </h3>
          {deptData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={deptData} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
                <XAxis dataKey="code" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#6B7280', fontWeight: 600 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: '#F9FAFB' }}
                  formatter={(v, _, props) => [v, props.payload?.name || '']}
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: 12 }}
                />
                <Bar dataKey="value" name="Complaints" radius={[4, 4, 0, 0]}>
                  {deptData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                  <LabelList dataKey="value" position="top" style={{ fontSize: 10, fill: '#6B7280', fontWeight: 600 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-48 items-center justify-center text-gray-300 text-sm">No department data</div>
          )}
        </Card>

        {/* Priority Grid */}
        <Card className="lg:col-span-2 p-5 shadow-sm border border-gray-100">
          <h3 className="text-base font-bold text-gray-900 mb-4">Priority Breakdown</h3>
          <div className="grid grid-cols-2 gap-3 h-[calc(100%-2.5rem)]">
            {[
              { key: 'Critical', color: '#EF4444', bg: '#FEF2F2', border: '#FECACA', label: 'Critical' },
              { key: 'High',     color: '#F97316', bg: '#FFF7ED', border: '#FED7AA', label: 'High' },
              { key: 'Medium',   color: '#F59E0B', bg: '#FFFBEB', border: '#FDE68A', label: 'Medium' },
              { key: 'Low',      color: '#6B7280', bg: '#F9FAFB', border: '#E5E7EB', label: 'Low' },
            ].map(({ key, color, bg, border, label }) => (
              <div
                key={key}
                onClick={() => navigate(`/admin/complaints?priority=${key}`)}
                className="rounded-xl border p-3 text-center cursor-pointer hover:shadow-sm hover:-translate-y-px transition-all duration-200 flex flex-col items-center justify-center"
                style={{ background: bg, borderColor: border }}
              >
                <p className="text-2xl font-bold" style={{ color }}>{byPriority[key] || 0}</p>
                <p className="text-xs font-semibold mt-1" style={{ color: `${color}CC` }}>{label}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <ExportModal
        isOpen={showExport}
        onClose={() => setShowExport(false)}
        title="Admin Executive Report"
        sections={exportSections}
      />
    </div>
  );
}
