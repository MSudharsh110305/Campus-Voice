import React, { useState, useEffect } from 'react';
import adminService from '../../../services/admin.service';
import { Card, EliteButton, Badge, Skeleton } from '../../../components/UI';
import { User, Shield, CheckCircle, XCircle, Plus, X, AlertCircle } from 'lucide-react';
import {
    AUTHORITY_TYPES,
    AUTHORITY_LEVELS,
    DEPARTMENTS,
} from '../../../utils/constants';

const DEPT_REQUIRED_TYPES = ['HOD'];
const HOD_TYPES = ['HOD'];

const emptyForm = {
    name: '',
    email: '',
    password: '',
    authority_type: AUTHORITY_TYPES[0],
    authority_level: '',
    department_id: '',
    phone: '',
    designation: '',
};

function CreateAuthorityModal({ open, onClose, onCreated }) {
    const [form, setForm] = useState(emptyForm);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (open) {
            setForm(emptyForm);
            setError('');
        }
    }, [open]);

    if (!open) return null;

    const isDeptRequired = HOD_TYPES.includes(form.authority_type);

    const handleTypeChange = (type) => {
        const level = AUTHORITY_LEVELS[type] || '';
        setForm(f => ({ ...f, authority_type: type, authority_level: level, department_id: '' }));
    };

    const validate = () => {
        if (!form.name.trim()) return 'Name is required';
        if (!form.email.trim()) return 'Email is required';
        if (!form.email.toLowerCase().endsWith('@srec.ac.in')) return 'Email must end with @srec.ac.in';
        if (!form.password || form.password.length < 8) return 'Password must be at least 8 characters';
        if (!form.authority_type) return 'Authority type is required';
        if (!form.authority_level) return 'Authority level is required';
        if (isDeptRequired && !form.department_id) return 'Department is required for HOD accounts';
        return null;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        const validationError = validate();
        if (validationError) { setError(validationError); return; }

        const payload = {
            name: form.name.trim(),
            email: form.email.trim(),
            password: form.password,
            authority_type: form.authority_type,
            authority_level: parseInt(form.authority_level),
        };
        if (form.department_id) payload.department_id = parseInt(form.department_id);
        if (form.phone.trim()) payload.phone = form.phone.trim();
        if (form.designation.trim()) payload.designation = form.designation.trim();

        setSubmitting(true);
        try {
            await adminService.createAuthority(payload);
            onCreated();
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to create authority');
        } finally {
            setSubmitting(false);
        }
    };

    const inputClass = "w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary transition-all bg-white";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <Card className="w-full max-w-lg p-6 bg-white shadow-xl border-0 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-5">
                    <h3 className="text-lg font-bold text-gray-900">Create Authority Account</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <X size={20} />
                    </button>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-lg text-red-600 text-sm flex items-center gap-2">
                        <AlertCircle size={16} className="flex-shrink-0" />
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-semibold text-gray-600 mb-1.5">Full Name *</label>
                            <input
                                type="text"
                                className={inputClass}
                                value={form.name}
                                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                placeholder="Dr. John Smith"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-600 mb-1.5">Phone (optional)</label>
                            <input
                                type="text"
                                className={inputClass}
                                value={form.phone}
                                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                                placeholder="+91 9876543210"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-600 mb-1.5">Email * (@srec.ac.in)</label>
                        <input
                            type="email"
                            className={inputClass}
                            value={form.email}
                            onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                            placeholder="authority@srec.ac.in"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-600 mb-1.5">Password *</label>
                        <input
                            type="password"
                            className={inputClass}
                            value={form.password}
                            onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                            placeholder="Min 8 characters"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-600 mb-1.5">Authority Type *</label>
                        <select
                            className={inputClass}
                            value={form.authority_type}
                            onChange={e => handleTypeChange(e.target.value)}
                        >
                            {AUTHORITY_TYPES.map(t => (
                                <option key={t} value={t}>{t}</option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-semibold text-gray-600 mb-1.5">Authority Level *</label>
                            <input
                                type="number"
                                className={inputClass}
                                value={form.authority_level}
                                onChange={e => setForm(f => ({ ...f, authority_level: e.target.value }))}
                                placeholder="e.g. 5"
                                min="1"
                                max="100"
                            />
                            {form.authority_type && AUTHORITY_LEVELS[form.authority_type] && (
                                <p className="text-xs text-gray-400 mt-1">
                                    Default for {form.authority_type}: {AUTHORITY_LEVELS[form.authority_type]}
                                </p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-600 mb-1.5">
                                Department {isDeptRequired ? '*' : '(optional)'}
                            </label>
                            <select
                                className={inputClass}
                                value={form.department_id}
                                onChange={e => setForm(f => ({ ...f, department_id: e.target.value }))}
                            >
                                <option value="">None</option>
                                {DEPARTMENTS.map(d => (
                                    <option key={d.id} value={d.id}>{d.code} — {d.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-600 mb-1.5">Designation (optional)</label>
                        <input
                            type="text"
                            className={inputClass}
                            value={form.designation}
                            onChange={e => setForm(f => ({ ...f, designation: e.target.value }))}
                            placeholder="e.g. Associate Professor"
                        />
                    </div>

                    <div className="flex justify-end gap-3 pt-2">
                        <EliteButton variant="outline" type="button" onClick={onClose} disabled={submitting}>
                            Cancel
                        </EliteButton>
                        <EliteButton variant="primary" type="submit" disabled={submitting} isLoading={submitting}>
                            {submitting ? 'Creating...' : 'Create Authority'}
                        </EliteButton>
                    </div>
                </form>
            </Card>
        </div>
    );
}

export default function AdminAuthorities() {
    const [authorities, setAuthorities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showCreate, setShowCreate] = useState(false);
    const [feedback, setFeedback] = useState({ type: '', message: '' });
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        loadAuthorities();
    }, []);

    const showMsg = (type, message) => {
        setFeedback({ type, message });
        setTimeout(() => setFeedback({ type: '', message: '' }), 4000);
    };

    const loadAuthorities = async () => {
        try {
            setLoading(true);
            const data = await adminService.getAllAuthorities();
            setAuthorities(data?.authorities || []);
        } catch (err) {
            setError('Failed to load authorities');
        } finally {
            setLoading(false);
        }
    };

    const toggleStatus = async (id, currentStatus) => {
        try {
            await adminService.toggleAuthorityActive(id, !currentStatus);
            setAuthorities(prev => prev.map(a =>
                a.id === id ? { ...a, is_active: !currentStatus } : a
            ));
            showMsg('success', `Authority ${!currentStatus ? 'enabled' : 'disabled'} successfully`);
        } catch (err) {
            showMsg('error', 'Failed to update status');
        }
    };

    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-48 rounded-2xl" />)}
            </div>
        );
    }

    // Filter authorities in-memory by name/role/department
    const filteredAuthorities = authorities.filter((auth) => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return (
            auth.name?.toLowerCase().includes(q) ||
            auth.authority_type?.toLowerCase().includes(q) ||
            auth.department_name?.toLowerCase().includes(q) ||
            auth.email?.toLowerCase().includes(q)
        );
    });

    return (
        <div className="space-y-5">
            {/* Header */}
            <div className="flex justify-between items-center gap-4">
                <div>
                    <h1 className="text-xl font-bold text-gray-900">Authority Management</h1>
                    <p className="text-gray-400 text-sm mt-0.5">
                        {authorities.length} authorities total
                    </p>
                </div>
                <EliteButton variant="primary" onClick={() => setShowCreate(true)}>
                    <Plus size={16} className="mr-2" />
                    Add Authority
                </EliteButton>
            </div>

            {/* Search/Filter input */}
            <div>
                <input
                    type="text"
                    placeholder="Search authorities by name, role, or department..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all bg-white"
                />
            </div>

            {/* Feedback banner */}
            {feedback.message && (
                <div className={`p-4 rounded-xl text-sm font-medium flex items-center gap-2 ${
                    feedback.type === 'success'
                        ? 'bg-green-50 border border-green-100 text-green-700'
                        : 'bg-red-50 border border-red-100 text-red-600'
                }`}>
                    {feedback.type === 'success'
                        ? <CheckCircle size={16} />
                        : <AlertCircle size={16} />}
                    {feedback.message}
                </div>
            )}

            {error && (
                <div className="text-center text-red-500 py-6">{error}</div>
            )}

            {authorities.length === 0 && !error ? (
                <Card className="p-12 text-center shadow-sm border border-gray-100">
                    <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-300">
                        <Shield size={32} />
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 mb-2">No Authorities Yet</h3>
                    <p className="text-gray-500 mb-4">Create the first authority account to get started.</p>
                    <EliteButton variant="primary" onClick={() => setShowCreate(true)}>
                        <Plus size={16} className="mr-2" /> Create Authority
                    </EliteButton>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {filteredAuthorities.map((auth) => (
                        <div
                            key={auth.id}
                            className="bg-white rounded-2xl border border-gray-100 hover:shadow-lg transition-all duration-200 overflow-hidden group"
                        >
                            {/* Card top accent */}
                            <div className={`h-1 w-full ${auth.is_active ? 'bg-gradient-to-r from-srec-primary to-srec-primaryHover' : 'bg-gray-200'}`} />

                            <div className="p-5">
                                {/* Header: Avatar + name + status badge */}
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-11 h-11 rounded-xl bg-srec-primary/10 flex items-center justify-center text-srec-primary font-bold text-base flex-shrink-0 group-hover:bg-srec-primary group-hover:text-white transition-colors duration-200">
                                            {auth.name.charAt(0).toUpperCase()}
                                        </div>
                                        <div className="min-w-0">
                                            <h3 className="font-bold text-gray-900 truncate text-sm">{auth.name}</h3>
                                            <p className="text-xs text-gray-400 truncate">{auth.email}</p>
                                        </div>
                                    </div>
                                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${
                                        auth.is_active
                                            ? 'bg-green-50 text-green-700 border border-green-100'
                                            : 'bg-red-50 text-red-600 border border-red-100'
                                    }`}>
                                        {auth.is_active
                                            ? <><CheckCircle size={9} /> Active</>
                                            : <><XCircle size={9} /> Disabled</>}
                                    </span>
                                </div>

                                {/* Role badge */}
                                <div className="mb-3">
                                    <span className="inline-block bg-srec-primary/8 text-srec-primary text-xs font-semibold px-2.5 py-1 rounded-lg">
                                        {auth.authority_type}
                                    </span>
                                </div>

                                {/* Department (if any) */}
                                {auth.department_name && (
                                    <p className="text-xs text-gray-500 mb-3">
                                        <span className="text-gray-400">Dept: </span>{auth.department_name}
                                    </p>
                                )}

                                {/* Toggle button */}
                                <button
                                    className={`w-full py-2 rounded-xl text-xs font-bold transition-all mt-2 border ${
                                        auth.is_active
                                            ? 'bg-red-50 text-red-600 hover:bg-red-100 border-red-100'
                                            : 'bg-green-50 text-green-700 hover:bg-green-100 border-green-100'
                                    }`}
                                    onClick={() => toggleStatus(auth.id, auth.is_active)}
                                >
                                    {auth.is_active ? 'Disable Account' : 'Enable Account'}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <CreateAuthorityModal
                open={showCreate}
                onClose={() => setShowCreate(false)}
                onCreated={() => {
                    loadAuthorities();
                    showMsg('success', 'Authority account created successfully');
                }}
            />
        </div>
    );
}
