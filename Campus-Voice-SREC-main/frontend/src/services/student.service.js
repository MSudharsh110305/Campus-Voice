import { api } from '../utils/api';

const getProfile = async () => {
    return await api('/students/profile');
};

const updateProfile = async (data) => {
    // Only send allowed fields: name, email, year
    // Students do NOT have a phone column — never send phone
    const allowed = {};
    if (data.name !== undefined) allowed.name = data.name;
    if (data.email !== undefined) allowed.email = data.email;
    if (data.year !== undefined && data.year !== '') allowed.year = parseInt(data.year);

    return await api('/students/profile', {
        method: 'PUT',
        body: JSON.stringify(allowed),
    });
};

const changePassword = async (data) => {
    return await api('/students/change-password', {
        method: 'POST',
        body: JSON.stringify(data),
    });
};

const getStats = async () => {
    return await api('/students/stats');
};

const getMyComplaints = async ({ skip = 0, limit = 20, status_filter } = {}) => {
    const params = new URLSearchParams({ skip, limit });
    if (status_filter) params.append('status_filter', status_filter);
    return await api(`/students/my-complaints?${params}`);
};

const getNotifications = async ({ skip = 0, limit = 20, unread_only = false } = {}) => {
    const params = new URLSearchParams({ skip, limit, unread_only });
    return await api(`/students/notifications?${params}`);
};

const getUnreadCount = async () => {
    return await api('/students/notifications/unread-count');
};

const markNotificationRead = async (id) => {
    return await api(`/students/notifications/${id}/read`, { method: 'PUT' });
};

const markAllNotificationsRead = async () => {
    return await api('/students/notifications/mark-all-read', { method: 'PUT' });
};

const deleteNotification = async (id) => {
    return await api(`/students/notifications/${id}`, { method: 'DELETE' });
};

// Notice feed (A13) — returns notices targeted to the logged-in student
const getNotices = async ({ skip = 0, limit = 20 } = {}) => {
    const params = new URLSearchParams({ skip, limit });
    return await api(`/students/notices?${params}`);
};

const studentService = {
    getProfile,
    updateProfile,
    changePassword,
    getStats,
    getMyComplaints,
    getNotifications,
    getUnreadCount,
    markNotificationRead,
    markAllNotificationsRead,
    deleteNotification,
    getNotices,
};

export default studentService;
