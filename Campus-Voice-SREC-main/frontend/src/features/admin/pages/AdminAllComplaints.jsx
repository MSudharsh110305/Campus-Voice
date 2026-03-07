import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import adminService from '../../../services/admin.service';
import AdminComplaintCard from '../components/AdminComplaintCard';
import { Skeleton } from '../../../components/UI';
import { Filter, X, Search, FileSearch, ShieldAlert, CheckCircle, XCircle } from 'lucide-react';
import { STATUSES, PRIORITIES, CATEGORY_LIST } from '../../../utils/constants';
import { tokenStorage } from '../../../utils/api';

const getToken = () => tokenStorage.getAccessToken();

export default function AdminAllComplaints() {
    const [searchParams] = useSearchParams();
    const categoryFromUrl = searchParams.get('category') || '';
    const statusFromUrl = searchParams.get('status') || '';
    const priorityFromUrl = searchParams.get('priority') || '';
    const [authorities, setAuthorities] = useState([]);
    const searchFromUrl = searchParams.get('search') || '';

    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);

    // Pending disputes panel
    const [disputes, setDisputes] = useState([]);
    const [disputesLoading, setDisputesLoading] = useState(true);
    const [disputeActions, setDisputeActions] = useState({}); // { [id]: { reason, submitting, msg } }

    const [filters, setFilters] = useState({
        status: statusFromUrl,
        priority: priorityFromUrl,
        category_name: categoryFromUrl,
        search: searchFromUrl,
        date_from: '',
        date_to: '',
    });
    const [skip, setSkip] = useState(0);
    const LIMIT = 20;

    useEffect(() => {
        setFilters(f => ({
            ...f,
            status: statusFromUrl,
            priority: priorityFromUrl,
            category_name: categoryFromUrl,
            search: searchFromUrl,
        }));
    }, [categoryFromUrl, statusFromUrl, priorityFromUrl, searchFromUrl]);

    useEffect(() => {
        loadComplaints(true);
    }, [filters]);

    useEffect(() => {
        adminService.getAllAuthorities(0, 200, true)
            .then(data => setAuthorities(data.authorities || []))
            .catch(() => {});
    }, []);

    useEffect(() => {
        setDisputesLoading(true);
        adminService.getPendingDisputes(0, 50)
            .then(data => setDisputes(data.complaints || []))
            .catch(() => setDisputes([]))
            .finally(() => setDisputesLoading(false));
    }, []);

    const handleDisputeAction = async (complaintId, action) => {
        const reason = (disputeActions[complaintId]?.reason || '').trim();
        if (!reason) {
            setDisputeActions(prev => ({
                ...prev,
                [complaintId]: { ...prev[complaintId], msg: { type: 'error', text: 'Please provide a reason.' } }
            }));
            return;
        }
        setDisputeActions(prev => ({ ...prev, [complaintId]: { ...prev[complaintId], submitting: true, msg: null } }));
        try {
            await adminService.resolveDispute(complaintId, action, reason);
            setDisputeActions(prev => ({
                ...prev,
                [complaintId]: { reason: '', submitting: false, msg: { type: 'success', text: `Dispute ${action}ed successfully.` } }
            }));
            setDisputes(prev => prev.filter(d => d.id !== complaintId));
        } catch (err) {
            const msg = err?.data?.detail || err?.message || 'Failed';
            setDisputeActions(prev => ({
                ...prev,
                [complaintId]: { ...prev[complaintId], submitting: false, msg: { type: 'error', text: typeof msg === 'object' ? JSON.stringify(msg) : msg } }
            }));
        }
    };

    const loadComplaints = async (reset = false) => {
        try {
            setLoading(true);
            const currentSkip = reset ? 0 : skip;
            const data = await adminService.getAdminComplaints({
                status: filters.status,
                priority: filters.priority,
                category_name: filters.category_name,
                search: filters.search,
                date_from: filters.date_from,
                date_to: filters.date_to,
                skip: currentSkip,
                limit: LIMIT,
            });

            if (reset) {
                setComplaints(data.complaints || []);
                setSkip(LIMIT);
            } else {
                setComplaints(prev => [...prev, ...(data.complaints || [])]);
                setSkip(prev => prev + LIMIT);
            }
        } catch (err) {
            console.error("Failed to load complaints", err);
        } finally {
            setLoading(false);
        }
    };

    const setFilter = (key, val) => setFilters(f => ({ ...f, [key]: val }));
    const clearFilters = () => setFilters({ status: '', priority: '', category_name: '', search: '', date_from: '', date_to: '' });
    const hasFilters = !!(filters.status || filters.priority || filters.category_name || filters.search || filters.date_from || filters.date_to);

    const handleDelete = async (complaintId) => {
        await adminService.deleteComplaint(complaintId);
        setComplaints(prev => prev.filter(c => c.id !== complaintId));
    };

    const handleReassign = async (complaintId, authorityId) => {
        const result = await adminService.reassignComplaint(complaintId, authorityId);
        const auth = authorities.find(a => a.id === authorityId);
        if (auth) {
            setComplaints(prev =>
                prev.map(c => c.id === complaintId
                    ? { ...c, assigned_authority_name: auth.name }
                    : c
                )
            );
        }
        return result;
    };

    return (
        <div className="space-y-5">
            <div>
                <h1 className="text-xl font-bold text-gray-900">All Complaints</h1>
                <p className="text-sm text-gray-400 mt-0.5">
                    {hasFilters ? 'Filtered results' : 'All complaints in the system'}
                </p>
            </div>

            {/* ── Pending Disputes Panel ──────────────────────────────────── */}
            {(disputesLoading || disputes.length > 0) && (
                <div className="bg-orange-50 border border-orange-200 rounded-2xl p-4 space-y-3">
                    <div className="flex items-center gap-2">
                        <ShieldAlert size={16} className="text-orange-600" />
                        <h2 className="text-sm font-bold text-orange-800">
                            Pending Spam Disputes {disputes.length > 0 && <span className="ml-1 px-2 py-0.5 text-[10px] bg-orange-100 text-orange-700 border border-orange-200 rounded-full">{disputes.length}</span>}
                        </h2>
                    </div>
                    {disputesLoading ? (
                        <Skeleton className="h-16 rounded-xl" />
                    ) : disputes.map(d => {
                        const da = disputeActions[d.id] || {};
                        return (
                            <div key={d.id} className="bg-white border border-orange-100 rounded-xl p-3 space-y-2">
                                <div className="flex items-start justify-between gap-2 flex-wrap">
                                    <div>
                                        <p className="text-xs font-semibold text-gray-800 line-clamp-2">{d.rephrased_text || d.original_text}</p>
                                        <p className="text-[10px] text-gray-400 mt-0.5">Student: {d.student_roll_no} {d.student_name ? `(${d.student_name})` : ''}</p>
                                        {d.appeal_reason && (
                                            <p className="text-[10px] text-orange-700 mt-1 italic">Reason: "{d.appeal_reason}"</p>
                                        )}
                                    </div>
                                </div>
                                <textarea
                                    rows={2}
                                    placeholder="Admin resolution note (required)..."
                                    className="w-full text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-gray-50 text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-200 resize-none"
                                    value={da.reason || ''}
                                    onChange={e => setDisputeActions(prev => ({ ...prev, [d.id]: { ...prev[d.id], reason: e.target.value } }))}
                                />
                                {da.msg && (
                                    <p className={`text-[10px] font-medium ${da.msg.type === 'success' ? 'text-green-700' : 'text-red-600'}`}>{da.msg.text}</p>
                                )}
                                <div className="flex gap-2">
                                    <button
                                        disabled={da.submitting}
                                        onClick={() => handleDisputeAction(d.id, 'accept')}
                                        className="flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50"
                                    >
                                        <CheckCircle size={11} /> {da.submitting ? 'Saving…' : 'Accept'}
                                    </button>
                                    <button
                                        disabled={da.submitting}
                                        onClick={() => handleDisputeAction(d.id, 'reject')}
                                        className="flex items-center gap-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50"
                                    >
                                        <XCircle size={11} /> {da.submitting ? 'Saving…' : 'Reject'}
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                    {!disputesLoading && disputes.length === 0 && (
                        <p className="text-xs text-orange-600">No pending disputes.</p>
                    )}
                </div>
            )}

            {/* Filter Panel */}
            <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm space-y-3">
                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                    <input
                        type="text"
                        className="w-full bg-gray-50 border border-gray-200 rounded-xl py-2.5 pl-9 pr-3 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
                        placeholder="Search complaint text..."
                        value={filters.search}
                        onChange={(e) => setFilter('search', e.target.value)}
                    />
                </div>

                {/* Dropdowns */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus-within:ring-2 focus-within:ring-srec-primary/20 focus-within:border-srec-primary transition-all">
                        <Filter size={12} className="text-gray-400 flex-shrink-0" />
                        <select className="bg-transparent text-sm focus:outline-none text-gray-700 w-full" value={filters.status} onChange={(e) => setFilter('status', e.target.value)}>
                            <option value="">All Statuses</option>
                            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                    </div>
                    <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus-within:ring-2 focus-within:ring-srec-primary/20 focus-within:border-srec-primary transition-all">
                        <Filter size={12} className="text-gray-400 flex-shrink-0" />
                        <select className="bg-transparent text-sm focus:outline-none text-gray-700 w-full" value={filters.priority} onChange={(e) => setFilter('priority', e.target.value)}>
                            <option value="">All Priorities</option>
                            {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </div>
                    <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus-within:ring-2 focus-within:ring-srec-primary/20 focus-within:border-srec-primary transition-all col-span-2 sm:col-span-1">
                        <Filter size={12} className="text-gray-400 flex-shrink-0" />
                        <select className="bg-transparent text-sm focus:outline-none text-gray-700 w-full" value={filters.category_name} onChange={(e) => setFilter('category_name', e.target.value)}>
                            <option value="">All Categories</option>
                            {CATEGORY_LIST.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                        </select>
                    </div>
                </div>

                {/* Date range */}
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium text-gray-400">From</span>
                        <input type="date" className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none" value={filters.date_from} onChange={(e) => setFilter('date_from', e.target.value)} />
                        <span className="text-xs font-medium text-gray-400">To</span>
                        <input type="date" className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none" value={filters.date_to} onChange={(e) => setFilter('date_to', e.target.value)} />
                    </div>
                    {hasFilters && (
                        <button onClick={clearFilters} className="ml-auto flex items-center gap-1 text-xs text-srec-danger font-medium border border-dashed border-red-200 rounded-xl px-3 py-2 hover:bg-red-50 transition-colors">
                            <X size={12} /> Clear All
                        </button>
                    )}
                </div>

                {/* Active filter chips */}
                {hasFilters && (
                    <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-gray-50">
                        <span className="text-xs text-gray-400">Active:</span>
                        {filters.status && <Chip label={filters.status} onRemove={() => setFilter('status', '')} color="blue" />}
                        {filters.priority && <Chip label={filters.priority} onRemove={() => setFilter('priority', '')} color="orange" />}
                        {filters.category_name && <Chip label={filters.category_name} onRemove={() => setFilter('category_name', '')} color="purple" />}
                        {filters.search && <Chip label={`"${filters.search}"`} onRemove={() => setFilter('search', '')} color="amber" icon={<FileSearch size={10} />} />}
                        {filters.date_from && <Chip label={`From ${filters.date_from}`} onRemove={() => setFilter('date_from', '')} color="gray" />}
                        {filters.date_to && <Chip label={`To ${filters.date_to}`} onRemove={() => setFilter('date_to', '')} color="gray" />}
                    </div>
                )}
            </div>

            {loading && complaints.length === 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-52 rounded-2xl" />)}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {complaints.map(c => (
                        <AdminComplaintCard
                            key={c.id}
                            complaint={c}
                            token={getToken()}
                            authorities={authorities}
                            onDelete={handleDelete}
                            onReassign={handleReassign}
                        />
                    ))}
                </div>
            )}

            {!loading && complaints.length === 0 && (
                <div className="text-center py-20 bg-white rounded-2xl border border-gray-100 shadow-sm">
                    <div className="w-14 h-14 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-3 text-gray-400">
                        <FileSearch size={26} />
                    </div>
                    <h3 className="text-base font-semibold text-gray-700">No complaints found</h3>
                    <p className="text-gray-400 text-sm mt-1">Try adjusting your filters</p>
                    {hasFilters && <button onClick={clearFilters} className="mt-3 text-sm text-srec-primary hover:underline">Clear all filters</button>}
                </div>
            )}

            {complaints.length > 0 && (
                <div className="flex justify-center mt-6">
                    <button onClick={() => loadComplaints(false)} disabled={loading}
                        className="border border-gray-200 rounded-xl px-6 py-2 text-sm text-gray-600 hover:border-srec-primary hover:text-srec-primary transition-all duration-200 disabled:opacity-50">
                        {loading ? 'Loading...' : 'Load More'}
                    </button>
                </div>
            )}
        </div>
    );
}

function Chip({ label, onRemove, color = 'gray', icon }) {
    const colorMap = {
        blue:   'bg-blue-50 text-blue-700 border-blue-100',
        orange: 'bg-orange-50 text-orange-700 border-orange-100',
        purple: 'bg-purple-50 text-purple-700 border-purple-100',
        amber:  'bg-amber-50 text-amber-700 border-amber-100',
        gray:   'bg-gray-100 text-gray-600 border-gray-200',
    };
    return (
        <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${colorMap[color] || colorMap.gray}`}>
            {icon}{label}
            <button onClick={onRemove} className="hover:text-red-500 ml-0.5"><X size={10} /></button>
        </span>
    );
}
