import React, { useState, useEffect, useCallback } from 'react';
import { Card, EliteButton } from '../../../components/UI';
import authorityService from '../../../services/authority.service';
import adminService from '../../../services/admin.service';
import {
  Megaphone, Plus, Trash2, X, CheckCircle, AlertCircle,
  Paperclip, Pin, Users, ShieldCheck, Eye, ChevronDown,
} from 'lucide-react';
import {
  NOTICE_CATEGORIES, NOTICE_PRIORITIES, GENDER, STAY_TYPE, DEPARTMENT_LIST,
} from '../../../utils/constants';

const PRIORITY_STYLES = {
  Low:    'bg-gray-100 text-gray-600',
  Medium: 'bg-blue-50 text-blue-700',
  High:   'bg-orange-50 text-orange-700',
  Urgent: 'bg-red-50 text-red-700 font-bold',
};
const CATEGORY_COLORS = {
  Emergency:      'bg-red-100 text-red-700',
  Announcement:   'bg-blue-50 text-blue-700',
  'Policy Change':'bg-amber-50 text-amber-700',
  Event:          'bg-emerald-50 text-emerald-700',
  Maintenance:    'bg-slate-100 text-slate-600',
  General:        'bg-sky-50 text-sky-700',
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

// ─── Audience chip row ────────────────────────────────────────────────────────
function AudienceTags({ notice }) {
  const none = !notice.target_gender?.length && !notice.target_stay_types?.length &&
               !notice.target_departments?.length && !notice.target_years?.length;
  if (none) return <span className="px-2 py-0.5 rounded-full text-[10px] bg-gray-50 text-gray-500 border border-gray-200">All Students</span>;
  return (
    <>
      {notice.target_gender?.map(g => <span key={g} className="px-2 py-0.5 rounded-full text-[10px] bg-blue-50 text-blue-600 border border-blue-100">{g}</span>)}
      {notice.target_stay_types?.map(s => <span key={s} className="px-2 py-0.5 rounded-full text-[10px] bg-purple-50 text-purple-600 border border-purple-100">{s}</span>)}
      {notice.target_departments?.map(d => <span key={d} className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-50 text-emerald-600 border border-emerald-100">{d}</span>)}
      {notice.target_years?.length > 0 && (
        <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-50 text-amber-600 border border-amber-100">
          Yr {notice.target_years.join(', ')}
        </span>
      )}
    </>
  );
}

const CATEGORY_LEFT_ACCENT = {
  Emergency:      'bg-red-500',
  Announcement:   'bg-blue-500',
  'Policy Change':'bg-amber-500',
  Event:          'bg-emerald-500',
  Maintenance:    'bg-slate-400',
  General:        'bg-sky-500',
};

// ─── Notice card (shared) ─────────────────────────────────────────────────────
function NoticeRow({ notice, onDelete, showAuthority = false }) {
  const dateStr = new Date(notice.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  const isEdited = notice.updated_at && notice.created_at &&
      new Date(notice.updated_at) - new Date(notice.created_at) > 5000;
  const accentBar = CATEGORY_LEFT_ACCENT[notice.category] || 'bg-gray-300';

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm transition-all duration-200 hover:shadow-md relative overflow-hidden flex">
      {/* Left color accent */}
      <div className={`w-1 flex-shrink-0 ${accentBar} rounded-l-2xl`} />

      <div className="flex-1 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${PRIORITY_STYLES[notice.priority] || 'bg-gray-100 text-gray-600'}`}>
                {notice.priority}
              </span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${CATEGORY_COLORS[notice.category] || 'bg-gray-100 text-gray-600'}`}>
                {notice.category}
              </span>
              {showAuthority && notice.authority_name && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-srec-primarySoft text-srec-primary border border-srec-primary/20">
                  <ShieldCheck size={10} /> {notice.authority_name}
                  {notice.authority_type && <span className="text-srec-primary/60 ml-0.5">· {notice.authority_type}</span>}
                </span>
              )}
              {isEdited && (
                <span className="text-[10px] text-gray-400 italic">edited</span>
              )}
              <span className="text-xs text-gray-300 ml-auto">{dateStr}</span>
            </div>
            <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">{notice.title}</h3>
            <p className="text-sm text-gray-500 line-clamp-2 leading-relaxed">{notice.content}</p>
            {notice.expires_at && (
              <p className="mt-2 text-xs text-amber-600">Active until: {new Date(notice.expires_at).toLocaleString()}</p>
            )}
            <div className="mt-2 flex flex-wrap gap-1.5">
              <AudienceTags notice={notice} />
            </div>
            {notice.attachments?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {notice.attachments.map(att => (
                  <a key={att.id}
                    href={authorityService.getNoticeAttachmentByIdUrl(notice.id, att.id)}
                    target="_blank" rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-srec-primary hover:underline"
                  >
                    <Paperclip size={11} />{att.filename}
                  </a>
                ))}
              </div>
            )}
          </div>
          {onDelete && (
            <button
              onClick={() => onDelete(notice.id)}
              className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all flex-shrink-0"
              title="Delete notice"
            >
              <Trash2 size={15} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Tab: Authority Notices (monitor) ────────────────────────────────────────
function AuthorityNoticesTab() {
  const [notices, setNotices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authorities, setAuthorities] = useState([]);
  const [selectedAuth, setSelectedAuth] = useState('');

  const load = useCallback(async (authId) => {
    try {
      setLoading(true);
      const data = await adminService.getAllNoticesAdmin({
        limit: 100,
        authority_id: authId || null,
      });
      setNotices(data?.notices || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    adminService.getAllAuthorities(0, 100, true).then(data => {
      setAuthorities(data?.authorities || []);
    }).catch(() => {});
    load('');
  }, [load]);

  const handleAuthChange = (e) => {
    const val = e.target.value;
    setSelectedAuth(val);
    load(val);
  };

  return (
    <div className="space-y-4">
      {/* Authority filter */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <select
            value={selectedAuth}
            onChange={handleAuthChange}
            className="w-full rounded-xl border border-gray-200 px-3 py-2.5 pr-8 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary bg-white appearance-none"
          >
            <option value="">All Authorities</option>
            {authorities.map(a => (
              <option key={a.id} value={a.id}>{a.name} ({a.authority_type})</option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
        <span className="text-xs text-gray-400">{notices.length} notice{notices.length !== 1 ? 's' : ''}</span>
      </div>

      {loading ? (
        <div className="text-center py-8 text-gray-400">Loading…</div>
      ) : notices.length === 0 ? (
        <Card className="p-12 text-center shadow-sm border border-gray-100">
          <Eye size={32} className="text-gray-200 mx-auto mb-3" />
          <p className="text-sm font-semibold text-gray-600">No notices found</p>
          <p className="text-xs text-gray-400 mt-1">
            {selectedAuth ? 'This authority has not posted any notices.' : 'No authority has posted any notices yet.'}
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {notices.map(notice => (
            <NoticeRow key={notice.id} notice={notice} showAuthority />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function AdminNotices() {
  const [tab, setTab] = useState('mine');

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fadeIn">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Pin size={20} className="text-srec-primary" /> Admin Notices
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Broadcast pinned announcements or monitor authority notice board activity.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/70 backdrop-blur-sm border border-white/60 rounded-xl p-1 shadow-sm max-w-sm">
        <button
          onClick={() => setTab('mine')}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-all duration-200 ${
            tab === 'mine'
              ? 'bg-srec-primary text-white shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          My Broadcasts
        </button>
        <button
          onClick={() => setTab('all')}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-all duration-200 ${
            tab === 'all'
              ? 'bg-srec-primary text-white shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Authority Notices
        </button>
      </div>

      {tab === 'mine' ? <MyBroadcastsTabContent /> : <AuthorityNoticesTab />}
    </div>
  );
}

// ─── My Broadcasts tab content ────────────────────────────────────────────────
function MyBroadcastsTabContent() {
  const [showForm, setShowForm] = useState(false);

  const inputClass = "w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary transition-all bg-white";
  const chipClass = (active) => `px-3 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer select-none ${
    active ? 'bg-srec-primary text-white shadow-sm' : 'bg-white text-gray-600 border border-gray-200 hover:border-srec-primary/50'
  }`;

  const [notices, setNotices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ ...emptyForm });
  const [attachmentFiles, setAttachmentFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      setLoading(true);
      const data = await authorityService.getMyNotices({ limit: 100 });
      setNotices(data?.notices || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const toggleArrayItem = (arr, item) =>
    arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    if (!form.title.trim() || form.title.length < 5) { setError('Title must be at least 5 characters'); return; }
    if (!form.content.trim() || form.content.length < 10) { setError('Content must be at least 10 characters'); return; }

    const payload = {
      title: form.title.trim(), content: form.content.trim(),
      category: form.category, priority: form.priority,
      target_gender:       form.target_gender.length       ? form.target_gender       : null,
      target_stay_types:   form.target_stay_types.length   ? form.target_stay_types   : null,
      target_departments:  form.target_departments.length  ? form.target_departments  : null,
      target_years:        form.target_years.length        ? form.target_years        : null,
      expires_at: form.expires_at || null,
    };

    setSubmitting(true);
    try {
      const created = await authorityService.createNotice(payload);
      if (attachmentFiles.length > 0 && created?.id) {
        for (const file of attachmentFiles) {
          try { await authorityService.addNoticeAttachment(created.id, file); } catch {}
        }
      }
      setSuccess('Notice broadcast to all matching students!');
      setForm({ ...emptyForm }); setAttachmentFiles([]); setShowForm(false);
      await load();
    } catch (err) {
      setError(err.message || 'Failed to send notice');
    } finally { setSubmitting(false); }
  };

  const handleDeactivate = async (noticeId) => {
    if (!window.confirm('Deactivate this notice?')) return;
    try {
      await authorityService.deactivateNotice(noticeId);
      setNotices(prev => prev.filter(n => n.id !== noticeId));
    } catch (err) {
      setError(err.message || 'Failed to deactivate');
      setTimeout(() => setError(''), 3000);
    }
  };

  return (
    <div className="space-y-4">
      {/* New broadcast button row */}
      <div className="flex justify-end">
        <EliteButton variant="primary" onClick={() => setShowForm(!showForm)}>
          <Plus size={18} className="mr-2" /> New Broadcast
        </EliteButton>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 p-3.5 bg-amber-50 border border-amber-200 rounded-xl">
        <ShieldCheck size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-amber-800">
          <strong>Admin notices are pinned</strong> — they always appear at the top of students' notice board with a special badge, regardless of when they were created.
        </p>
      </div>

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

      {showForm && (
        <Card className="p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Create Admin Broadcast</h2>
              <p className="text-xs text-gray-400 mt-0.5">This notice will be pinned to the top for all matching students</p>
            </div>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">Title *</label>
              <input type="text" className={inputClass} value={form.title}
                onChange={e => setForm({ ...form, title: e.target.value })}
                placeholder="Notice title (5–255 chars)" maxLength={255} />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">Content *</label>
              <textarea className={inputClass} rows={5} value={form.content}
                onChange={e => setForm({ ...form, content: e.target.value })}
                placeholder="Notice content — URLs will be rendered as clickable links" maxLength={5000} />
              <p className="text-xs text-gray-400 mt-1 text-right">{form.content.length} / 5000</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Category</label>
                <select className={inputClass} value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
                  {NOTICE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Priority</label>
                <select className={inputClass} value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
                  {NOTICE_PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>

            <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100 space-y-4">
              <div className="flex items-center gap-2">
                <Users size={14} className="text-gray-400" />
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                  Target Audience <span className="font-normal normal-case text-gray-400">(leave empty = all students)</span>
                </p>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-2 block">Gender</label>
                <div className="flex gap-2 flex-wrap">
                  {GENDER.map(g => (
                    <button key={g} type="button"
                      onClick={() => setForm(f => ({ ...f, target_gender: toggleArrayItem(f.target_gender, g) }))}
                      className={chipClass(form.target_gender.includes(g))}>{g}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-2 block">Stay Type</label>
                <div className="flex gap-2 flex-wrap">
                  {STAY_TYPE.map(s => (
                    <button key={s} type="button"
                      onClick={() => setForm(f => ({ ...f, target_stay_types: toggleArrayItem(f.target_stay_types, s) }))}
                      className={chipClass(form.target_stay_types.includes(s))}>{s}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-2 block">Year(s)</label>
                <div className="flex gap-2 flex-wrap">
                  {['1','2','3','4','5'].map(y => (
                    <button key={y} type="button"
                      onClick={() => setForm(f => ({ ...f, target_years: toggleArrayItem(f.target_years, y) }))}
                      className={`w-9 h-9 rounded-full text-xs font-bold transition-all ${
                        form.target_years.includes(y)
                          ? 'bg-srec-primary text-white shadow-sm'
                          : 'bg-white text-gray-600 border border-gray-200 hover:border-srec-primary/50'
                      }`}>{y}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-2 block">Departments</label>
                <div className="flex gap-2 flex-wrap">
                  {DEPARTMENT_LIST.map(d => (
                    <button key={d.code} type="button"
                      onClick={() => setForm(f => ({ ...f, target_departments: toggleArrayItem(f.target_departments, d.code) }))}
                      className={chipClass(form.target_departments.includes(d.code))}>{d.code}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-2 block">Active Until (optional)</label>
                <input type="datetime-local" className={inputClass} value={form.expires_at}
                  onChange={e => setForm({ ...form, expires_at: e.target.value })} />
                <p className="text-[10px] text-gray-400 mt-1">Leave empty for a permanent notice.</p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">
                Attachments <span className="font-normal text-gray-400 text-xs">(optional · up to 5)</span>
              </label>
              <input type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp" multiple
                onChange={e => {
                  const selected = Array.from(e.target.files || []).slice(0, 5);
                  setAttachmentFiles(prev => [...prev, ...selected].slice(0, 5));
                  e.target.value = '';
                }}
                className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-srec-primarySoft file:text-srec-primary cursor-pointer"
              />
              {attachmentFiles.length > 0 && (
                <div className="mt-2 space-y-1">
                  {attachmentFiles.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 rounded-lg px-2 py-1.5">
                      <Paperclip size={11} className="flex-shrink-0" />
                      <span className="flex-1 truncate">{f.name}</span>
                      <span className="text-gray-400 flex-shrink-0">{(f.size / 1024).toFixed(0)} KB</span>
                      <button type="button" onClick={() => setAttachmentFiles(p => p.filter((_, idx) => idx !== i))} className="text-red-400 hover:text-red-600">
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <EliteButton variant="outline" type="button" onClick={() => setShowForm(false)}>Cancel</EliteButton>
              <EliteButton variant="primary" type="submit" disabled={submitting} isLoading={submitting}>
                {submitting ? 'Broadcasting...' : '📣 Broadcast Notice'}
              </EliteButton>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <div className="text-center py-8 text-gray-400">Loading notices...</div>
      ) : notices.length === 0 ? (
        <Card className="p-12 text-center shadow-sm border border-gray-100">
          <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-300">
            <Megaphone size={32} />
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">No Notices Sent</h3>
          <p className="text-gray-500 mb-4">Broadcast your first admin notice to students.</p>
          <EliteButton variant="primary" onClick={() => setShowForm(true)}>
            <Plus size={16} className="mr-2" /> Create Notice
          </EliteButton>
        </Card>
      ) : (
        <div className="space-y-4">
          {notices.map(notice => (
            <NoticeRow key={notice.id} notice={notice} onDelete={handleDeactivate} />
          ))}
        </div>
      )}
    </div>
  );
}
