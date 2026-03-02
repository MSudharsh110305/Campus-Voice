import React, { useState, useEffect } from 'react';
import { Card, EliteButton } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import authorityService from '../../../services/authority.service';
import AuthoritySidebar from '../components/AuthoritySidebar';
import AuthorityHeader from '../components/AuthorityHeader';
import { Megaphone, Plus, Trash2, X, CheckCircle, AlertCircle, Paperclip, Download } from 'lucide-react';
import { NOTICE_CATEGORIES, NOTICE_PRIORITIES, GENDER, STAY_TYPE, DEPARTMENT_LIST } from '../../../utils/constants';

const PRIORITY_STYLES = {
    Low:    'bg-gray-100 text-gray-600',
    Medium: 'bg-blue-50 text-blue-700',
    High:   'bg-orange-50 text-orange-700',
    Urgent: 'bg-red-50 text-red-700 font-bold',
};

const emptyForm = {
    title: '',
    content: '',
    category: 'Announcement',
    priority: 'Medium',
    target_gender: [],
    target_stay_types: [],
    target_departments: [],
    target_years: [],
    expires_at: '',
};

export default function AuthorityNotices() {
    const { user } = useAuth();

    // Determine gender/stay-type constraints based on authority type
    const isMensWarden   = user?.authority_type?.toLowerCase().includes("men's hostel");
    const isWomensWarden = user?.authority_type?.toLowerCase().includes("women's hostel");
    const isHostelWarden = isMensWarden || isWomensWarden;

    // For hostel wardens: pre-lock gender and stay_type
    const lockedGender    = isMensWarden ? ['Male'] : isWomensWarden ? ['Female'] : null;
    const lockedStayTypes = isHostelWarden ? ['Hostel'] : null;

    // Build the initial form with locks applied
    const buildEmptyForm = () => ({
        ...emptyForm,
        target_gender:     lockedGender    ? [...lockedGender]    : [],
        target_stay_types: lockedStayTypes ? [...lockedStayTypes] : [],
    });

    const [notices, setNotices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState(buildEmptyForm);
    const [attachmentFile, setAttachmentFile] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        loadNotices();
    }, []);

    const loadNotices = async () => {
        try {
            setLoading(true);
            const data = await authorityService.getMyNotices({ limit: 50 });
            setNotices(data?.notices || []);
        } catch (err) {
            console.error('Failed to load notices', err);
        } finally {
            setLoading(false);
        }
    };

    const toggleArrayItem = (arr, item) =>
        arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item];

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (!form.title.trim() || form.title.length < 5) {
            setError('Title must be at least 5 characters');
            return;
        }
        if (!form.content.trim() || form.content.length < 10) {
            setError('Content must be at least 10 characters');
            return;
        }

        const payload = {
            title: form.title.trim(),
            content: form.content.trim(),
            category: form.category,
            priority: form.priority,
            target_gender: form.target_gender.length ? form.target_gender : null,
            target_stay_types: form.target_stay_types.length ? form.target_stay_types : null,
            target_departments: form.target_departments.length ? form.target_departments : null,
            target_years: form.target_years.length ? form.target_years : null,
            expires_at: form.expires_at || null,
        };

        setSubmitting(true);
        try {
            const created = await authorityService.createNotice(payload);
            if (attachmentFile && created?.id) {
                try {
                    await authorityService.uploadNoticeAttachment(created.id, attachmentFile);
                } catch (attachErr) {
                    console.error('Attachment upload failed:', attachErr);
                    // Notice created successfully, just attachment failed
                    setSuccess('Notice sent! (Attachment upload failed — try re-uploading)');
                    setForm(buildEmptyForm());
                    setAttachmentFile(null);
                    setShowForm(false);
                    await loadNotices();
                    return;
                }
            }
            setSuccess('Notice sent successfully!');
            setForm(buildEmptyForm());
            setAttachmentFile(null);
            setShowForm(false);
            await loadNotices();
        } catch (err) {
            setError(err.message || 'Failed to send notice');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeactivate = async (noticeId) => {
        if (!window.confirm('Deactivate this notice? It will no longer appear in student feeds.')) return;
        try {
            await authorityService.deactivateNotice(noticeId);
            setNotices(prev => prev.filter(n => n.id !== noticeId));
            setSuccess('Notice deactivated');
            setTimeout(() => setSuccess(''), 3000);
        } catch (err) {
            setError(err.message || 'Failed to deactivate notice');
            setTimeout(() => setError(''), 3000);
        }
    };

    const inputClass = "w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary transition-all";

    return (
        <div className="flex min-h-screen bg-srec-background">
            <AuthoritySidebar className="hidden md:flex fixed inset-y-0 left-0 z-10" />

            <div className="flex-1 md:ml-64 flex flex-col min-w-0 transition-all duration-300">
                <AuthorityHeader />

                <main className="flex-1 p-6 sm:p-8 overflow-y-auto animate-fadeIn">
                    <div className="max-w-4xl mx-auto space-y-6">
                        {/* Header */}
                        <div className="flex items-center justify-between">
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">Notices & Broadcasts</h1>
                                <p className="text-sm text-gray-500 mt-1">Send announcements to targeted student groups</p>
                            </div>
                            <EliteButton variant="primary" onClick={() => setShowForm(!showForm)}>
                                <Plus size={18} className="mr-2" />
                                New Notice
                            </EliteButton>
                        </div>

                        {/* Feedback */}
                        {success && (
                            <div className="flex items-center gap-2 p-4 bg-green-50 border border-green-100 rounded-xl text-green-700 text-sm">
                                <CheckCircle size={18} /> {success}
                            </div>
                        )}
                        {error && (
                            <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-100 rounded-xl text-red-600 text-sm">
                                <AlertCircle size={18} /> {error}
                            </div>
                        )}

                        {/* Notice Creation Form */}
                        {showForm && (
                            <Card className="p-6 shadow-sm border border-gray-100">
                                <div className="flex items-center justify-between mb-6">
                                    <h2 className="text-lg font-bold text-gray-900">Create New Notice</h2>
                                    <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
                                        <X size={20} />
                                    </button>
                                </div>

                                <form onSubmit={handleSubmit} className="space-y-5">
                                    {/* Title */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5">Title *</label>
                                        <input
                                            type="text"
                                            className={inputClass}
                                            value={form.title}
                                            onChange={e => setForm({ ...form, title: e.target.value })}
                                            placeholder="Notice title (5-255 chars)"
                                            maxLength={255}
                                        />
                                    </div>

                                    {/* Content */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5">Content *</label>
                                        <textarea
                                            className={inputClass}
                                            rows={4}
                                            value={form.content}
                                            onChange={e => setForm({ ...form, content: e.target.value })}
                                            placeholder="Notice content (10-5000 chars)"
                                            maxLength={5000}
                                        />
                                        <p className="text-xs text-gray-400 mt-1">{form.content.length} / 5000</p>
                                    </div>

                                    {/* Category & Priority */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1.5">Category</label>
                                            <select className={inputClass} value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
                                                {NOTICE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1.5">Priority</label>
                                            <select className={inputClass} value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
                                                {NOTICE_PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                                            </select>
                                        </div>
                                    </div>

                                    {/* Targeting */}
                                    <div className="bg-gray-50 rounded-xl p-4 border border-gray-100 space-y-4">
                                        <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                                            Target Audience (leave empty = all students)
                                        </p>

                                        {/* Gender */}
                                        <div>
                                            <label className="text-xs font-semibold text-gray-600 mb-2 block">
                                                Gender
                                                {lockedGender && <span className="ml-2 text-[10px] text-srec-primary font-normal">(auto-set for your hostel)</span>}
                                            </label>
                                            <div className="flex gap-2 flex-wrap">
                                                {GENDER.map(g => {
                                                    const isLocked = lockedGender !== null;
                                                    const isSelected = form.target_gender.includes(g);
                                                    return (
                                                        <button
                                                            key={g}
                                                            type="button"
                                                            disabled={isLocked}
                                                            onClick={() => !isLocked && setForm(f => ({ ...f, target_gender: toggleArrayItem(f.target_gender, g) }))}
                                                            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                                                                isSelected
                                                                    ? 'bg-srec-primary text-white shadow-sm'
                                                                    : 'bg-white text-gray-600 border border-gray-200'
                                                            } ${isLocked ? 'opacity-60 cursor-not-allowed' : 'hover:border-srec-primary/50'}`}
                                                        >
                                                            {g}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>

                                        {/* Stay Type */}
                                        <div>
                                            <label className="text-xs font-semibold text-gray-600 mb-2 block">
                                                Stay Type
                                                {lockedStayTypes && <span className="ml-2 text-[10px] text-srec-primary font-normal">(auto-set for hostel wardens)</span>}
                                            </label>
                                            <div className="flex gap-2 flex-wrap">
                                                {STAY_TYPE.map(s => {
                                                    const isLocked = lockedStayTypes !== null;
                                                    const isSelected = form.target_stay_types.includes(s);
                                                    return (
                                                        <button
                                                            key={s}
                                                            type="button"
                                                            disabled={isLocked}
                                                            onClick={() => !isLocked && setForm(f => ({ ...f, target_stay_types: toggleArrayItem(f.target_stay_types, s) }))}
                                                            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                                                                isSelected
                                                                    ? 'bg-srec-primary text-white shadow-sm'
                                                                    : 'bg-white text-gray-600 border border-gray-200'
                                                            } ${isLocked ? 'opacity-60 cursor-not-allowed' : 'hover:border-srec-primary/50'}`}
                                                        >
                                                            {s}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>

                                        {/* Years */}
                                        <div>
                                            <label className="text-xs font-semibold text-gray-600 mb-2 block">Year(s)</label>
                                            <div className="flex gap-2 flex-wrap">
                                                {['1','2','3','4','5'].map(y => (
                                                    <button
                                                        key={y}
                                                        type="button"
                                                        onClick={() => setForm(f => ({ ...f, target_years: toggleArrayItem(f.target_years, y) }))}
                                                        className={`w-9 h-9 rounded-full text-xs font-bold transition-all ${
                                                            form.target_years.includes(y)
                                                                ? 'bg-srec-primary text-white shadow-sm'
                                                                : 'bg-white text-gray-600 border border-gray-200 hover:border-srec-primary/50'
                                                        }`}
                                                    >
                                                        {y}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Expiry */}
                                        <div>
                                            <label className="text-xs font-semibold text-gray-600 mb-2 block">Expires At (optional)</label>
                                            <input
                                                type="datetime-local"
                                                className={inputClass}
                                                value={form.expires_at}
                                                onChange={e => setForm({ ...form, expires_at: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    {/* Attachment */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5 flex items-center gap-1.5">
                                            <Paperclip size={14} className="text-gray-400" />
                                            Attach File <span className="font-normal text-gray-400 text-xs">(optional · PDF, Word, Excel, image · max 10 MB)</span>
                                        </label>
                                        <input
                                            type="file"
                                            accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp"
                                            onChange={e => setAttachmentFile(e.target.files[0] || null)}
                                            className="block w-full text-sm text-gray-600
                                                       file:mr-3 file:py-2 file:px-3
                                                       file:rounded-lg file:border-0
                                                       file:text-xs file:font-semibold
                                                       file:bg-srec-primarySoft file:text-srec-primary
                                                       hover:file:bg-srec-primarySoft/80
                                                       cursor-pointer"
                                        />
                                        {attachmentFile && (
                                            <div className="mt-1.5 flex items-center gap-2 text-xs text-gray-500">
                                                <Paperclip size={11} />
                                                {attachmentFile.name}
                                                <button type="button" onClick={() => setAttachmentFile(null)}
                                                    className="text-red-400 hover:text-red-600 ml-1">
                                                    <X size={12} />
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex justify-end gap-3 pt-2">
                                        <EliteButton variant="outline" type="button" onClick={() => setShowForm(false)}>Cancel</EliteButton>
                                        <EliteButton variant="primary" type="submit" disabled={submitting} isLoading={submitting}>
                                            {submitting ? 'Sending...' : 'Send Notice'}
                                        </EliteButton>
                                    </div>
                                </form>
                            </Card>
                        )}

                        {/* Existing Notices */}
                        <div className="space-y-4">
                            {loading ? (
                                <div className="text-center py-8 text-gray-400">Loading notices...</div>
                            ) : notices.length === 0 ? (
                                <Card className="p-12 text-center shadow-sm border border-gray-100">
                                    <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-300">
                                        <Megaphone size={32} />
                                    </div>
                                    <h3 className="text-lg font-bold text-gray-900 mb-2">No Notices Yet</h3>
                                    <p className="text-gray-500 mb-4">Create your first notice to inform students.</p>
                                    <EliteButton variant="primary" onClick={() => setShowForm(true)}>
                                        <Plus size={16} className="mr-2" /> Create Notice
                                    </EliteButton>
                                </Card>
                            ) : (
                                notices.map(notice => (
                                    <div key={notice.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 transition-all duration-200 hover:shadow-md">
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-2 flex-wrap">
                                                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${PRIORITY_STYLES[notice.priority] || 'bg-gray-100 text-gray-600'}`}>
                                                        {notice.priority}
                                                    </span>
                                                    <span className="text-xs text-gray-400">{notice.category}</span>
                                                    <span className="text-xs text-gray-300 ml-auto">
                                                        {new Date(notice.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}
                                                    </span>
                                                </div>
                                                <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">{notice.title}</h3>
                                                <p className="text-sm text-gray-500 line-clamp-2 leading-relaxed">{notice.content}</p>
                                                {notice.expires_at && (
                                                    <p className="mt-2 text-xs text-amber-600">
                                                        Expires: {new Date(notice.expires_at).toLocaleDateString()}
                                                    </p>
                                                )}
                                                {notice.attachment_filename && (
                                                    <a
                                                        href={authorityService.getNoticeAttachmentUrl(notice.id)}
                                                        download={notice.attachment_filename}
                                                        className="mt-2 inline-flex items-center gap-1.5 text-xs text-srec-primary hover:underline"
                                                        onClick={e => e.stopPropagation()}
                                                    >
                                                        <Download size={11} />
                                                        {notice.attachment_filename}
                                                    </a>
                                                )}
                                            </div>
                                            <button
                                                onClick={() => handleDeactivate(notice.id)}
                                                className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-200 flex-shrink-0"
                                                title="Deactivate notice"
                                            >
                                                <Trash2 size={15} />
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
