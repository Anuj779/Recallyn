import axios from 'axios';

// Uses VITE_API_URL if set in production, otherwise defaults to local backend
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
});

export const fetchWorkflows = async () => (await api.get('/workflows')).data;
export const fetchHistory = async () => (await api.get('/history')).data;
export const teachWorkflow = async (prompt) => (await api.post('/workflows/teach', { prompt })).data;
export const runWorkflow = async (id) => (await api.post(`/workflows/${id}/run`)).data;
export const stepRun = async (runId) => (await api.post(`/runs/${runId}/step`)).data;
export const verifyRun = async (runId) => (await api.post(`/runs/${runId}/verify`)).data;
export const approveRun = async (runId, decision, fileId = null, originalFileId = null) => 
  (await api.post(`/runs/${runId}/approve`, { decision, file_id: fileId, original_file_id: originalFileId })).data;
export const getRunStatus = async (runId) => (await api.get(`/runs/${runId}/status`)).data;
export const getReceipt = async (runId) => (await api.get(`/runs/${runId}/receipt`)).data;
