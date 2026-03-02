import { api } from '../utils/api';

// Authority Management
const createAuthority = async (authorityData) => {
    return await api('/admin/authorities', {
        method: 'POST',
        body: JSON.stringify(authorityData),
    });
};

const getAllAuthorities = async (skip = 0, limit = 50, is_active = null) => {
    const params = new URLSearchParams({ skip, limit });
    if (is_active !== null) params.append('is_active', is_active);
    return await api(`/admin/authorities?${params}`);
};

const toggleAuthorityActive = async (authorityId, activate) => {
    const params = new URLSearchParams({ activate });
    return await api(`/admin/authorities/${authorityId}/toggle-active?${params}`, {
        method: 'PUT',
    });
};

const deleteAuthority = async (authorityId) => {
    return await api(`/admin/authorities/${authorityId}`, {
        method: 'DELETE',
    });
};

// Student Management
const getAllStudents = async (skip = 0, limit = 50, is_active = null, department_id = null) => {
    const params = new URLSearchParams({ skip, limit });
    if (is_active !== null) params.append('is_active', is_active);
    if (department_id) params.append('department_id', department_id);
    return await api(`/admin/students?${params}`);
};

const toggleStudentActive = async (rollNo, activate) => {
    const params = new URLSearchParams({ activate });
    return await api(`/admin/students/${rollNo}/toggle-active?${params}`, {
        method: 'PUT',
    });
};

// Complaint Routing Control
const reassignComplaint = async (complaintId, authorityId) => {
    const params = new URLSearchParams({ authority_id: authorityId });
    return await api(`/admin/complaints/${complaintId}/reassign?${params}`, {
        method: 'PUT',
    });
};

const deleteComplaint = async (complaintId) => {
    return await api(`/admin/complaints/${complaintId}`, {
        method: 'DELETE',
    });
};

// System Stats
const getSystemOverview = async () => {
    return await api('/admin/stats/overview');
};

const getAnalytics = async (days = 30) => {
    const params = new URLSearchParams({ days });
    return await api(`/admin/stats/analytics?${params}`);
};

// Bulk Operations
const bulkStatusUpdate = async (complaintIds, newStatus, reason) => {
    const params = new URLSearchParams({
        new_status: newStatus,
        reason
    });
    complaintIds.forEach(id => params.append('complaint_ids', id));

    return await api(`/admin/complaints/bulk-status-update?${params}`, {
        method: 'POST',
    });
};

// Image Moderation
const getPendingImageVerifications = async (skip = 0, limit = 20) => {
    const params = new URLSearchParams({ skip, limit });
    return await api(`/admin/images/pending-verification?${params}`);
};

const moderateImage = async (complaintId, approve, reason = null) => {
    const params = new URLSearchParams({ approve });
    if (reason) params.append('reason', reason);
    return await api(`/admin/images/${complaintId}/moderate?${params}`, {
        method: 'POST',
    });
};

// Complaints (admin view — all complaints)
const getAdminComplaints = async ({ status = '', priority = '', category_id = '', category_name = '', search = '', date_from = '', date_to = '', skip = 0, limit = 20 } = {}) => {
    const params = new URLSearchParams({ skip, limit });
    if (status) params.append('status_filter', status);
    if (priority) params.append('priority', priority);
    if (category_id) params.append('category_id', category_id);
    if (category_name) params.append('category_name', category_name);
    if (search) params.append('search', search);
    if (date_from) params.append('date_from', date_from);
    if (date_to) params.append('date_to', date_to);
    return await api(`/admin/complaints?${params}`);
};

// Escalations
const getEscalations = async () => {
    return await api('/admin/escalations');
};

// Department-specific queries
const getStudentsByDepartment = async (departmentCode, skip = 0, limit = 200) => {
    const params = new URLSearchParams({ skip, limit });
    if (departmentCode) params.append('department_code', departmentCode);
    return await api(`/admin/students?${params}`);
};

const getDepartmentComplaints = async (departmentCode, skip = 0, limit = 50) => {
    const params = new URLSearchParams({ skip, limit, category_name: 'Department' });
    if (departmentCode) params.append('department_code', departmentCode);
    return await api(`/admin/complaints?${params}`);
};

// Health Metrics
const getHealthMetrics = async () => {
    return await api('/admin/health/metrics');
};

// ── Representatives ──────────────────────────────────────────────────────────

const getRepresentatives = async (params = {}) => {
    const qs = new URLSearchParams();
    if (params.department_id) qs.set('department_id', params.department_id);
    if (params.year) qs.set('year', params.year);
    if (params.scope) qs.set('scope', params.scope);
    if (params.active_only !== undefined) qs.set('active_only', params.active_only);
    return await api(`/admin/representatives?${qs}`);
};

const appointRepresentative = async ({ student_roll_no, scope }) => {
    return await api('/admin/representatives', {
        method: 'POST',
        body: JSON.stringify({ student_roll_no, scope }),
    });
};

const removeRepresentative = async (repId) => {
    return await api(`/admin/representatives/${repId}`, { method: 'DELETE' });
};

const getRepCapacity = async () => {
    return await api('/admin/representatives/capacity');
};

const getAnomalies = async (days = 30) => {
    return await api(`/admin/anomalies?days=${days}`);
};

// System Settings
const getSystemSettings = async () => {
    return await api('/admin/settings');
};

const updateSystemSetting = async (key, value) => {
    return await api(`/admin/settings/${key}`, {
        method: 'PUT',
        body: JSON.stringify({ value: String(value) }),
    });
};

const adminService = {
    createAuthority,
    getAllAuthorities,
    toggleAuthorityActive,
    deleteAuthority,
    getAllStudents,
    toggleStudentActive,
    reassignComplaint,
    deleteComplaint,
    getSystemOverview,
    getAnalytics,
    getAdminComplaints,
    bulkStatusUpdate,
    getPendingImageVerifications,
    moderateImage,
    getEscalations,
    getHealthMetrics,
    getStudentsByDepartment,
    getDepartmentComplaints,
    getRepresentatives,
    appointRepresentative,
    removeRepresentative,
    getRepCapacity,
    getAnomalies,
    getSystemSettings,
    updateSystemSetting,
};

export default adminService;
