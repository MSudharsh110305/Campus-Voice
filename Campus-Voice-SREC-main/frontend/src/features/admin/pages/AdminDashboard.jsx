import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import ExportModal from '../../../components/ExportModal';
import adminService from '../../../services/admin.service';
import complaintService from '../../../services/complaint.service';
import { Card, Select, Skeleton, EliteButton, STATUS_COLORS } from '../../../components/UI';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend, BarChart, Bar
} from 'recharts';
import { AlertTriangle, CheckCircle, Users, FileText, Activity, ArrowUpRight, Download, Star, TrendingUp } from 'lucide-react';
import AdminComplaintCard from '../components/AdminComplaintCard';

// Simple stats card for admin dashboard
function StatCard({ label, value, icon: Icon, color = 'blue', sub, onClick }) {
  const colorMap = {
    blue:   { icon: 'bg-blue-50 text-blue-600 border border-blue-100',            bar: 'from-blue-400 to-blue-600',       link: 'text-blue-700' },
    green:  { icon: 'bg-emerald-50 text-emerald-700 border border-emerald-100',   bar: 'from-emerald-500 to-green-600',   link: 'text-emerald-700' },
    red:    { icon: 'bg-red-50 text-red-600 border border-red-100',               bar: 'from-red-400 to-rose-500',        link: 'text-red-600' },
    amber:  { icon: 'bg-amber-50 text-amber-600 border border-amber-100',         bar: 'from-amber-400 to-orange-500',    link: 'text-amber-700' },
    purple: { icon: 'bg-violet-50 text-violet-600 border border-violet-100',      bar: 'from-violet-400 to-purple-500',   link: 'text-violet-700' },
  };
  const cfg = colorMap[color] || colorMap.blue;
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden transition-all duration-200 ${onClick ? 'cursor-pointer hover:shadow-md hover:border-gray-200 group' : ''}`}
    >
      <div className={`h-1 w-full bg-gradient-to-r ${cfg.bar}`} />
      <div className="p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-500">{label}</span>
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${cfg.icon} ${onClick ? 'group-hover:scale-110 transition-transform duration-200' : ''}`}>
            <Icon size={20} />
          </div>
        </div>
        <p className="text-3xl font-bold text-gray-900">{value ?? '—'}</p>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
        {onClick && <p className={`text-xs mt-2 opacity-0 group-hover:opacity-100 transition-opacity font-semibold ${cfg.link}`}>View details →</p>}
      </div>
    </div>
  );
}

const PIE_COLORS = ['#14532D', '#B8952E', '#22C55E', '#C82828', '#6366F1'];

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

  useEffect(() => {
    if (!user || user.role !== 'Admin') return;
    loadOverview();
    loadAnalytics();
    loadPublicAnalytics();
  }, [user]);

  const loadOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminService.getSystemOverview();
      setOverview(data);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const loadAnalytics = async () => {
    try {
      const data = await adminService.getAnalytics(30);
      setAnalytics(data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  };

  const loadPublicAnalytics = async () => {
    try {
      const data = await complaintService.getPublicAnalytics();
      setPublicAnalytics(data);
    } catch (err) {
      console.error('Failed to load public analytics:', err);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 rounded-2xl" />)}
        </div>
        <Skeleton className="h-96 rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <AlertTriangle className="text-red-500 mb-4" size={48} />
        <h2 className="text-xl font-bold text-gray-900 mb-2">Dashboard Error</h2>
        <p className="text-gray-500 mb-6">{error}</p>
        <EliteButton onClick={loadOverview}>Retry</EliteButton>
      </div>
    );
  }

  // --- Map real API fields ---
  // overview: { total_students, total_authorities, total_complaints,
  //             recent_complaints_7d, complaints_by_status, complaints_by_priority,
  //             complaints_by_category, image_statistics }
  const byStatus = overview?.complaints_by_status || {};
  const byPriority = overview?.complaints_by_priority || {};
  const byCategory = overview?.complaints_by_category || {};

  const totalComplaints = overview?.total_complaints || 0;
  const totalStudents = overview?.total_students || 0;
  const totalAuthorities = overview?.total_authorities || 0;
  const recent7d = overview?.recent_complaints_7d || 0;
  const resolved = byStatus['Resolved'] || 0;
  const criticalCount = byPriority['Critical'] || 0;
  const resolutionRate = totalComplaints > 0
    ? Math.round((resolved / totalComplaints) * 100)
    : 0;

  // analytics: { period_days, total_complaints, resolved_complaints,
  //              resolution_rate_percent, avg_resolution_time_hours, daily_complaints: [{date, count}] }
  // Chart expects array with date + count
  const dailyData = analytics?.daily_complaints || [];

  // Build pie data from complaints_by_category
  const categoryPieData = Object.entries(byCategory).map(([name, value]) => ({ name, value }));

  // Build status bar data
  const statusData = Object.entries(byStatus).map(([name, value]) => ({ name, value }));

  // Public analytics extras
  const deptData = Object.entries(publicAnalytics?.top_departments || {}).map(([name, value]) => ({ name, value }));
  const satisfactionAvg = publicAnalytics?.satisfaction_avg;
  const avgResolutionH = publicAnalytics?.avg_resolution_hours ?? analytics?.avg_resolution_time_hours;

  const exportSections = [
    {
      id: 'overview',
      label: 'System Overview',
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
      id: 'by_status',
      label: 'Complaints by Status',
      tableHeaders: ['Status', 'Count'],
      tableRows: Object.entries(byStatus).map(([s, c]) => [s, c]),
    },
    {
      id: 'by_priority',
      label: 'Complaints by Priority',
      tableHeaders: ['Priority', 'Count'],
      tableRows: ['Critical', 'High', 'Medium', 'Low'].map(p => [p, byPriority[p] || 0]),
    },
    {
      id: 'by_category',
      label: 'Complaints by Category',
      tableHeaders: ['Category', 'Count'],
      tableRows: Object.entries(byCategory).map(([c, v]) => [c, v]),
    },
    ...(analytics ? [{
      id: 'analytics',
      label: `Analytics (Last ${analytics.period_days || 30} Days)`,
      stats: [
        { label: 'Total Submitted', value: analytics.total_complaints },
        { label: 'Resolved', value: analytics.resolved_complaints },
        { label: 'Resolution Rate', value: analytics.resolution_rate_percent != null ? `${Math.round(analytics.resolution_rate_percent)}%` : '—' },
        { label: 'Avg Resolution Time', value: analytics.avg_resolution_time_hours != null ? `${Math.round(analytics.avg_resolution_time_hours)}h` : '—' },
      ],
    }] : []),
    ...(dailyData.length > 0 ? [{
      id: 'daily_trend',
      label: 'Daily Complaint Trend',
      tableHeaders: ['Date', 'Count'],
      tableRows: dailyData.map(d => [d.date, d.count]),
    }] : []),
  ];

  return (
    <div className="space-y-8 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Executive Dashboard</h1>
          <p className="text-gray-500 mt-1">Real-time overview of system performance and grievance resolution</p>
        </div>
        <div className="flex items-center gap-3">
          <EliteButton variant="outline" onClick={loadOverview}>Refresh Data</EliteButton>
          <EliteButton onClick={() => setShowExport(true)} className="flex items-center gap-2">
            <Download size={16} /> Export
          </EliteButton>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Complaints"
          value={totalComplaints}
          icon={FileText}
          color="blue"
          sub={`${recent7d} in last 7 days`}
          onClick={() => navigate('/admin/complaints')}
        />
        <StatCard
          label="Resolution Rate"
          value={`${resolutionRate}%`}
          icon={CheckCircle}
          color="green"
          sub={`${resolved} resolved of ${totalComplaints} total`}
          onClick={() => analyticsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
        />
        <StatCard
          label="Critical Issues"
          value={criticalCount}
          icon={AlertTriangle}
          color="red"
          sub={`${byPriority['High'] || 0} High priority`}
          onClick={() => navigate('/admin/complaints?priority=Critical')}
        />
        <StatCard
          label="Total Users"
          value={totalStudents + totalAuthorities}
          icon={Users}
          color="purple"
          sub={`${totalStudents} students · ${totalAuthorities} authorities`}
          onClick={() => navigate('/admin/authorities')}
        />
      </div>

      {/* Status breakdown — clickable chips using canonical STATUS_COLORS */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        {['Raised', 'In Progress', 'Resolved', 'Closed', 'Spam'].map((status) => {
          const count = byStatus[status] || 0;
          const c = STATUS_COLORS[status] || STATUS_COLORS['Raised'];
          return (
            <div
              key={status}
              onClick={() => navigate(`/admin/complaints?status=${encodeURIComponent(status)}`)}
              className={`rounded-xl border px-4 py-3 text-center cursor-pointer transition-all duration-200 hover:shadow-card-hover hover:-translate-y-px ${c.bg} ${c.border} ${c.text}`}
            >
              <p className="text-2xl font-bold leading-tight">{count}</p>
              <p className="text-xs font-semibold mt-1 opacity-80">{status}</p>
            </div>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Daily Trend */}
        <Card className="lg:col-span-2 p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
            <Activity size={20} className="text-srec-primary" />
            Complaint Volume (Last {analytics?.period_days || 30} Days)
          </h3>
          <div className="h-72 w-full">
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
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#9CA3AF', fontSize: 11 }}
                    tickFormatter={v => v?.slice(5)} // Show MM-DD
                  />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#14532D"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#colorCount)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-gray-400">No analytics data yet</div>
            )}
          </div>
        </Card>

        {/* Category Pie */}
        <Card className="p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-6">By Category</h3>
          <div className="h-72 w-full">
            {categoryPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryPieData}
                    cx="50%"
                    cy="45%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {categoryPieData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36} iconSize={10} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-gray-400">No data yet</div>
            )}
          </div>
        </Card>
      </div>

      {/* Analytics Summary Row */}
      <div ref={analyticsRef} className="scroll-mt-6">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">
          Resolution Analytics (last {analytics?.period_days || 30} days)
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm text-center">
            <p className="text-2xl font-bold text-gray-900">{analytics?.total_complaints || 0}</p>
            <p className="text-xs text-gray-500 mt-1 font-medium">Total Submitted</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm text-center">
            <p className="text-2xl font-bold text-green-600">{analytics?.resolved_complaints || 0}</p>
            <p className="text-xs text-gray-500 mt-1 font-medium">Resolved</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm text-center">
            <p className="text-2xl font-bold text-srec-primary">
              {analytics?.resolution_rate_percent != null
                ? `${Math.round(analytics.resolution_rate_percent)}%`
                : '—'}
            </p>
            <p className="text-xs text-gray-500 mt-1 font-medium">Resolution Rate</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm text-center">
            <p className="text-2xl font-bold text-blue-600">
              {avgResolutionH != null ? `${Math.round(avgResolutionH)}h` : '—'}
            </p>
            <p className="text-xs text-gray-500 mt-1 font-medium">Avg Resolution Time</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm text-center">
            <p className="text-2xl font-bold text-amber-600 flex items-center justify-center gap-1">
              <Star size={18} className="fill-amber-400 text-amber-400" />
              {satisfactionAvg != null ? satisfactionAvg : '—'}
            </p>
            <p className="text-xs text-gray-500 mt-1 font-medium">Satisfaction Avg / 5</p>
          </div>
        </div>

        {/* Top Departments chart */}
        {deptData.length > 0 && (
          <div className="mt-4 bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <h4 className="text-sm font-bold text-gray-700 mb-4 flex items-center gap-2">
              <TrendingUp size={15} className="text-srec-primary" />
              Top Departments by Complaint Volume
            </h4>
            <ResponsiveContainer width="100%" height={Math.min(deptData.length * 36, 240)}>
              <BarChart data={deptData} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#9CA3AF' }} allowDecimals={false} axisLine={false} tickLine={false} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#6B7280' }} width={80} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Bar dataKey="value" name="Complaints" fill="#14532D" radius={[0, 4, 4, 0]}>
                  {deptData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Priority breakdown */}
        {Object.keys(byPriority).length > 0 && (
          <div className="mt-4 bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <h4 className="text-sm font-bold text-gray-700 mb-3">Priority Breakdown (all time)</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {['Critical', 'High', 'Medium', 'Low'].map(p => {
                const pColors = {
                  Critical: 'text-red-600 bg-red-50 border-red-100',
                  High: 'text-orange-600 bg-orange-50 border-orange-100',
                  Medium: 'text-amber-600 bg-amber-50 border-amber-100',
                  Low: 'text-gray-600 bg-gray-50 border-gray-100',
                };
                return (
                  <div
                    key={p}
                    onClick={() => navigate(`/admin/complaints?priority=${p}`)}
                    className={`rounded-xl border px-4 py-3 text-center cursor-pointer hover:shadow-sm transition-all ${pColors[p]}`}
                  >
                    <p className="text-xl font-bold">{byPriority[p] || 0}</p>
                    <p className="text-xs font-semibold mt-0.5">{p}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
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
