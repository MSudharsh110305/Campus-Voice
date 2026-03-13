import { api } from '../utils/api';

const getPetitions = async (skip = 0, limit = 20, statusFilter = null) => {
    const params = new URLSearchParams({ skip, limit });
    if (statusFilter) params.set('status', statusFilter);
    return await api(`/petitions/?${params}`);
};

const createPetition = async ({ title, description, petition_scope, custom_goal, duration_days }) => {
    return await api('/petitions/', {
        method: 'POST',
        body: JSON.stringify({ title, description, petition_scope, custom_goal, duration_days }),
    });
};

const getPetitionDetail = async (id) => {
    return await api(`/petitions/${id}`);
};

const signPetition = async (id) => {
    return await api(`/petitions/${id}/sign`, { method: 'POST' });
};

const respondToPetition = async (id, { response, status }) => {
    return await api(`/petitions/${id}/respond`, {
        method: 'POST',
        body: JSON.stringify({ response, status }),
    });
};

const approvePetition = async (id) => {
    return await api(`/petitions/${id}/approve`, { method: 'POST' });
};

const rejectPetition = async (id, reason) => {
    return await api(`/petitions/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ response: reason, status: 'Closed' }),
    });
};

const getMyRepStatus = async () => {
    return await api('/petitions/me/status');
};

const petitionService = {
    getPetitions,
    createPetition,
    getPetitionDetail,
    signPetition,
    respondToPetition,
    approvePetition,
    rejectPetition,
    getMyRepStatus,
};

export default petitionService;
