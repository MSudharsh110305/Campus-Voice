import { api } from '../utils/api';

// Authority Profile
const getProfile = async () => {
    return await api('/authorities/profile');
};

// Authority Dashboard
const getDashboard = async () => {
    return await api('/authorities/dashboard');
};

// Get assigned complaints
const getMyComplaints = async (skip = 0, limit = 20, status_filter = null) => {
    const params = new URLSearchParams({ skip, limit });
    if (status_filter) params.append('status_filter', status_filter);
    return await api(`/authorities/my-complaints?${params}`);
};

// Get specific complaint details (authority view)
const getComplaintDetails = async (complaintId) => {
    return await api(`/authorities/complaints/${complaintId}`);
};

// Update complaint status — JSON body with status + optional reason
const updateComplaintStatus = async (complaintId, status, reason = null) => {
    const body = { status };
    if (reason) body.reason = reason;
    return await api(`/authorities/complaints/${complaintId}/status`, {
        method: 'PUT',
        body: JSON.stringify(body),
    });
};

// Post public update — uses QUERY PARAMS not JSON body (C7)
const postUpdate = async (complaintId, title, content) => {
    const params = new URLSearchParams({ title, content });
    return await api(`/authorities/complaints/${complaintId}/post-update?${params}`, {
        method: 'POST',
    });
};

// Escalate complaint — uses QUERY PARAM not JSON body (C8)
const escalateComplaint = async (complaintId, reason) => {
    const params = new URLSearchParams({ reason });
    return await api(`/authorities/complaints/${complaintId}/escalate?${params}`, {
        method: 'POST',
    });
};

// Get escalation history
const getEscalationHistory = async (complaintId) => {
    return await api(`/authorities/complaints/${complaintId}/escalation-history`);
};

// Get authority stats
const getStats = async () => {
    return await api('/authorities/stats');
};

// Get detailed stats for executive dashboard
const getDetailedStats = async () => {
    return await api('/authorities/stats/detailed');
};

// --- Notice / Broadcast endpoints ---

// Create a notice (C11) — JSON body
const createNotice = async (noticeData) => {
    return await api('/authorities/notices', {
        method: 'POST',
        body: JSON.stringify(noticeData),
    });
};

// Get my notices (C12)
const getMyNotices = async ({ skip = 0, limit = 20, active_only = true } = {}) => {
    const params = new URLSearchParams({ skip, limit, active_only });
    return await api(`/authorities/my-notices?${params}`);
};

// Deactivate a notice (C13)
const deactivateNotice = async (noticeId) => {
    return await api(`/authorities/notices/${noticeId}`, { method: 'DELETE' });
};

// Upload attachment to a notice
const uploadNoticeAttachment = async (noticeId, file) => {
    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`/api/authorities/notices/${noticeId}/attachment`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || 'Failed to upload attachment');
    }
    return await res.json();
};

// Get attachment download URL (public)
const getNoticeAttachmentUrl = (noticeId) => `/api/authorities/notices/${noticeId}/attachment`;

// --- Notifications (Authority/Admin) ---

const getNotifications = async ({ skip = 0, limit = 20, unread_only = false } = {}) => {
    const params = new URLSearchParams({ skip, limit, unread_only });
    return await api(`/authorities/notifications?${params}`);
};

const markNotificationRead = async (id) => {
    return await api(`/authorities/notifications/${id}/read`, { method: 'PUT' });
};

const markAllNotificationsRead = async () => {
    return await api('/authorities/notifications/mark-all-read', { method: 'PUT' });
};

const deleteNotification = async (id) => {
    return await api(`/authorities/notifications/${id}`, { method: 'DELETE' });
};

const authorityService = {
    getProfile,
    getDashboard,
    getMyComplaints,
    getComplaintDetails,
    updateComplaintStatus,
    postUpdate,
    escalateComplaint,
    getEscalationHistory,
    getStats,
    getDetailedStats,
    createNotice,
    getMyNotices,
    deactivateNotice,
    uploadNoticeAttachment,
    getNoticeAttachmentUrl,
    getNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    deleteNotification,
};

export default authorityService;
