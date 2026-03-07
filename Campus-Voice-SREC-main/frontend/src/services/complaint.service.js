import { api, fetchBlobUrl } from '../utils/api';

const submitComplaint = async (formData) => {
    // FormData submission - do NOT set Content-Type header (browser sets it with boundary)
    const token = localStorage.getItem('token');

    // Use /api prefix so the Vite proxy routes it to localhost:8000
    const url = '/api/complaints/submit';

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
            // No Content-Type here — let browser set multipart/form-data boundary
        },
        body: formData
    });

    if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return;
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const message = data.error || data.detail || data.message || `Submission failed with status ${response.status}`;
        const err = new Error(message);
        err.status = response.status;
        err.data = data;
        throw err;
    }

    return data;
};

const getMyComplaints = async (rollNumber, limit = 50, offset = 0) => {
    // Legacy alias – use studentService.getMyComplaints instead
    const params = new URLSearchParams({ skip: offset, limit });
    return await api(`/students/my-complaints?${params}`);
};

const getPublicFeed = async (skip = 0, limit = 20, { categoryId, sortBy } = {}) => {
    const params = new URLSearchParams({ skip, limit });
    if (categoryId && categoryId !== 'All') params.set('category_id', categoryId);
    if (sortBy) params.set('sort_by', sortBy);
    return await api(`/complaints/public-feed?${params}`);
};

const getComplaintDetails = async (id) => {
    return await api(`/complaints/${id}`);
};

const voteOnComplaint = async (complaintId, voteType) => {
    return await api(`/complaints/${complaintId}/vote`, {
        method: 'POST',
        body: JSON.stringify({ vote_type: voteType }),
    });
};

const removeVote = async (complaintId) => {
    return await api(`/complaints/${complaintId}/vote`, {
        method: 'DELETE',
    });
};

const getMyVote = async (complaintId) => {
    return await api(`/complaints/${complaintId}/my-vote`);
};

const uploadImage = async (complaintId, imageFile) => {
    const token = localStorage.getItem('token');
    const fd = new FormData();
    fd.append('file', imageFile); // field name is "file" for existing complaint uploads

    const response = await fetch(`/api/complaints/${complaintId}/upload-image`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: fd
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || error.message || 'Failed to upload image');
    }

    return await response.json();
};

const fetchImage = async (complaintId, thumbnail = false) => {
    const suffix = thumbnail ? '?thumbnail=true' : '';
    return await fetchBlobUrl(`/complaints/${complaintId}/image${suffix}`);
};

const verifyImage = async (complaintId) => {
    return await api(`/complaints/${complaintId}/verify-image`, { method: 'POST' });
};

const getComplaintStatusHistory = async (id) => {
    return await api(`/complaints/${id}/status-history`);
};

const getComplaintTimeline = async (id) => {
    return await api(`/complaints/${id}/timeline`);
};

const getAdvancedFilteredComplaints = async (filters) => {
    const cleanFilters = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v !== null && v !== undefined && v !== '')
    );
    const params = new URLSearchParams(cleanFilters);
    return await api(`/complaints/filter/advanced?${params}`);
};

const flagSpam = async (complaintId, reason) => {
    const params = new URLSearchParams({ reason });
    return await api(`/complaints/${complaintId}/flag-spam?${params}`, { method: 'POST' });
};

const unflagSpam = async (complaintId) => {
    return await api(`/complaints/${complaintId}/unflag-spam`, { method: 'POST' });
};

const appealSpam = async (complaintId, reason) => {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    return await api(`/complaints/${complaintId}/appeal-spam${params}`, { method: 'POST' });
};

const disputeSpam = async (complaintId, reason) => {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    return await api(`/complaints/${complaintId}/dispute${params}`, { method: 'POST' });
};

const checkDuplicate = async (text, categoryHint = null) => {
    return await api('/complaints/check-duplicate', {
        method: 'POST',
        body: JSON.stringify({ text, category_hint: categoryHint }),
    });
};

const rateComplaint = async (complaintId, rating, feedback = null) => {
    return await api(`/complaints/${complaintId}/rate`, {
        method: 'POST',
        body: JSON.stringify({ rating, feedback }),
    });
};

const getChangelog = async (skip = 0, limit = 20) => {
    const params = new URLSearchParams({ skip, limit });
    return await api(`/complaints/changelog?${params}`);
};

const getPublicAnalytics = async () => {
    return await api('/complaints/analytics/summary');
};

const uploadAuthorityAttachment = async (complaintId, file) => {
    const token = localStorage.getItem('token');
    const fd = new FormData();
    fd.append('file', file);
    const response = await fetch(`/api/complaints/${complaintId}/authority-attachment`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: fd,
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || err.error || 'Failed to upload attachment');
    }
    return await response.json();
};

const complaintService = {
    submitComplaint,
    getMyComplaints,
    getPublicFeed,
    getComplaintDetails,
    voteOnComplaint,
    removeVote,
    getMyVote,
    uploadImage,
    fetchImage,
    verifyImage,
    getComplaintStatusHistory,
    getComplaintTimeline,
    getAdvancedFilteredComplaints,
    flagSpam,
    unflagSpam,
    appealSpam,
    disputeSpam,
    checkDuplicate,
    rateComplaint,
    getChangelog,
    getPublicAnalytics,
    uploadAuthorityAttachment,
};

export default complaintService;
