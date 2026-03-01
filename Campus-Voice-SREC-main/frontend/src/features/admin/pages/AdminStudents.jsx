import React, { useEffect, useState } from 'react';
import adminService from '../../../services/admin.service';
import { Skeleton } from '../../../components/UI';
import { Search, UserCheck, UserX, Filter } from 'lucide-react';

export default function AdminStudents() {
  const [students, setStudents] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterActive, setFilterActive] = useState('all'); // 'all' | 'active' | 'inactive'
  const [togglingId, setTogglingId] = useState(null);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    load();
  }, [filterActive]);

  const load = async () => {
    try {
      setLoading(true);
      const is_active = filterActive === 'all' ? null : filterActive === 'active';
      const data = await adminService.getAllStudents(0, 200, is_active);
      setStudents(data.students || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to load students:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (rollNo, currentlyActive) => {
    setTogglingId(rollNo);
    try {
      await adminService.toggleStudentActive(rollNo, !currentlyActive);
      setStudents(prev =>
        prev.map(s => s.roll_no === rollNo ? { ...s, is_active: !currentlyActive } : s)
      );
      setMsg({ type: 'success', text: `Student ${rollNo} ${!currentlyActive ? 'activated' : 'deactivated'}` });
      setTimeout(() => setMsg(null), 3000);
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to update student status' });
      setTimeout(() => setMsg(null), 4000);
    } finally {
      setTogglingId(null);
    }
  };

  const filtered = students.filter(s => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      s.roll_no?.toLowerCase().includes(q) ||
      s.name?.toLowerCase().includes(q) ||
      s.email?.toLowerCase().includes(q) ||
      s.department_code?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-srec-textPrimary">Student Management</h1>
          <p className="text-sm text-srec-textMuted mt-0.5">{total} students total</p>
        </div>
      </div>

      {msg && (
        <div className={`rounded-xl px-4 py-3 text-sm font-medium border ${
          msg.type === 'success'
            ? 'bg-green-50 text-green-700 border-green-200'
            : 'bg-red-50 text-red-700 border-red-200'
        }`}>{msg.text}</div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-srec-textMuted" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name, roll no, email, department…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-srec-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'active', 'inactive'].map(v => (
            <button
              key={v}
              onClick={() => setFilterActive(v)}
              className={`px-4 py-2.5 rounded-xl text-sm font-medium border transition-all ${
                filterActive === v
                  ? 'bg-srec-primary text-white border-srec-primary shadow-sm'
                  : 'bg-white text-srec-textSecondary border-srec-border hover:bg-srec-backgroundAlt'
              }`}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-2">
          {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-14 rounded-xl" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-srec-border">
          <p className="text-srec-textMuted">No students found</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-srec-border shadow-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-srec-backgroundAlt border-b border-srec-borderLight">
                <tr>
                  <th className="text-left px-4 py-3 font-semibold text-srec-textMuted text-xs uppercase tracking-wider">Roll No</th>
                  <th className="text-left px-4 py-3 font-semibold text-srec-textMuted text-xs uppercase tracking-wider">Name</th>
                  <th className="text-left px-4 py-3 font-semibold text-srec-textMuted text-xs uppercase tracking-wider hidden sm:table-cell">Department</th>
                  <th className="text-left px-4 py-3 font-semibold text-srec-textMuted text-xs uppercase tracking-wider hidden md:table-cell">Year</th>
                  <th className="text-left px-4 py-3 font-semibold text-srec-textMuted text-xs uppercase tracking-wider hidden md:table-cell">Stay</th>
                  <th className="text-left px-4 py-3 font-semibold text-srec-textMuted text-xs uppercase tracking-wider">Status</th>
                  <th className="text-right px-4 py-3 font-semibold text-srec-textMuted text-xs uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-srec-borderLight">
                {filtered.map(s => (
                  <tr key={s.roll_no} className="hover:bg-srec-backgroundAlt/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-srec-textSecondary">{s.roll_no}</td>
                    <td className="px-4 py-3 font-medium text-srec-textPrimary">{s.name}</td>
                    <td className="px-4 py-3 text-srec-textMuted hidden sm:table-cell">
                      <span className="px-2 py-0.5 bg-srec-backgroundAlt rounded text-xs font-semibold">
                        {s.department_code || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-srec-textMuted hidden md:table-cell">{s.year ?? '—'}</td>
                    <td className="px-4 py-3 text-srec-textMuted hidden md:table-cell">{s.stay_type || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border ${
                        s.is_active
                          ? 'bg-green-50 text-green-700 border-green-200'
                          : 'bg-red-50 text-red-600 border-red-200'
                      }`}>
                        {s.is_active ? <UserCheck size={11} /> : <UserX size={11} />}
                        {s.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        disabled={togglingId === s.roll_no}
                        onClick={() => handleToggle(s.roll_no, s.is_active)}
                        className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all disabled:opacity-50 ${
                          s.is_active
                            ? 'border-red-200 text-red-600 hover:bg-red-50'
                            : 'border-green-200 text-green-700 hover:bg-green-50'
                        }`}
                      >
                        {togglingId === s.roll_no ? '…' : s.is_active ? 'Disable' : 'Enable'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
