import React, { useEffect, useState } from 'react';
import { Card, Skeleton } from '../../../components/UI';
import complaintService from '../../../services/complaint.service';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import { TrendingUp, Clock, Star, BarChart2 } from 'lucide-react';

const STATUS_COLORS = {
  Raised: '#14532D',
  'In Progress': '#2563EB',
  Resolved: '#16A34A',
  Closed: '#6B7280',
  Spam: '#EF4444',
};

const PIE_COLORS = ['#14532D', '#22C55E', '#86EFAC', '#2563EB', '#F59E0B', '#EF4444', '#8B5CF6'];

function StatCard({ icon: Icon, label, value, sub, color = 'green' }) {
  const colorMap = {
    green:  'bg-green-50 text-green-700 border-green-100',
    blue:   'bg-blue-50 text-blue-700 border-blue-100',
    amber:  'bg-amber-50 text-amber-700 border-amber-100',
    purple: 'bg-violet-50 text-violet-700 border-violet-100',
  };
  return (
    <div className="bg-white rounded-2xl border border-srec-border shadow-card p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-srec-textMuted uppercase tracking-wider">{label}</span>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${colorMap[color]}`}>
          <Icon size={17} />
        </div>
      </div>
      <p className="text-3xl font-bold text-srec-textPrimary">{value ?? '—'}</p>
      {sub && <p className="text-xs text-srec-textMuted mt-1">{sub}</p>}
    </div>
  );
}

export default function AdminAnalytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const result = await complaintService.getPublicAnalytics();
        setData(result);
      } catch (err) {
        setError(err.message || 'Failed to load analytics');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48 rounded-lg" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <Skeleton key={i} className="h-28 rounded-2xl" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-64 rounded-2xl" />
          <Skeleton className="h-64 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">{error}</div>
      </div>
    );
  }

  // Prepare chart data
  const statusData = Object.entries(data?.status_breakdown || {}).map(([name, value]) => ({ name, value }));
  const categoryData = Object.entries(data?.category_breakdown || {}).map(([name, value]) => ({ name, value }));
  const deptData = Object.entries(data?.top_departments || {}).map(([name, value]) => ({ name, value }));

  const resolved = data?.status_breakdown?.Resolved || 0;
  const total = data?.total_complaints || 0;
  const resolutionRate = total > 0 ? Math.round((resolved / total) * 100) : 0;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-srec-textPrimary">Analytics</h1>
        <p className="text-sm text-srec-textMuted mt-0.5">Public complaint statistics overview</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={BarChart2}
          label="Total Complaints"
          value={total.toLocaleString()}
          sub="All public complaints"
          color="green"
        />
        <StatCard
          icon={TrendingUp}
          label="Resolution Rate"
          value={`${resolutionRate}%`}
          sub={`${resolved} resolved`}
          color="blue"
        />
        <StatCard
          icon={Clock}
          label="Avg Resolution"
          value={data?.avg_resolution_hours != null ? `${data.avg_resolution_hours}h` : '—'}
          sub="Hours to resolve"
          color="purple"
        />
        <StatCard
          icon={Star}
          label="Satisfaction"
          value={data?.satisfaction_avg != null ? `${data.satisfaction_avg}/5` : '—'}
          sub="Student rating avg"
          color="amber"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Status breakdown pie */}
        <Card className="p-5">
          <h2 className="text-sm font-bold text-srec-textPrimary mb-4">Status Breakdown</h2>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {statusData.map((entry) => (
                    <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || '#86EFAC'} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [v, 'Complaints']} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-srec-textMuted text-center py-10">No data</p>}
        </Card>

        {/* Category breakdown bar */}
        <Card className="p-5">
          <h2 className="text-sm font-bold text-srec-textPrimary mb-4">By Category</h2>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={categoryData} margin={{ top: 4, right: 8, bottom: 24, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8E2" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" name="Complaints" fill="#14532D" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-srec-textMuted text-center py-10">No data</p>}
        </Card>
      </div>

      {/* Top departments */}
      {deptData.length > 0 && (
        <Card className="p-5">
          <h2 className="text-sm font-bold text-srec-textPrimary mb-4">Top Departments by Complaint Volume</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={deptData} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 100 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8E2" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
              <Tooltip />
              <Bar dataKey="value" name="Complaints" fill="#22C55E" radius={[0, 4, 4, 0]}>
                {deptData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
