import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const axiosInstance = axios.create({
    baseURL: API_BASE,
});

// Add auth token to requests
axiosInstance.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const api = {
    // Auth
    register: (email, password) =>
        axiosInstance.post('/auth/register', { email, password }),

    login: (email, password) =>
        axiosInstance.post('/auth/login', new URLSearchParams({ username: email, password }), {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        }),

    // Cases
    createCase: (customer_id) =>
        axiosInstance.post('/cases/create', { customer_id }),

    runAnalysis: (case_id, customer_id) =>
        axiosInstance.post(`/cases/${case_id}/run-analysis?customer_id=${customer_id}`),

    getCase: (case_id) =>
        axiosInstance.get(`/cases/${case_id}`),

    // Exports
    exportDocx: (case_id, data) =>
        axiosInstance.post(`/cases/${case_id}/export-docx-body`, data, { responseType: 'blob' }),

    exportPdf: (case_id, data) =>
        axiosInstance.post(`/cases/${case_id}/export-pdf-body`, data, { responseType: 'blob' }),

    // Customers
    getCustomers: () =>
        axiosInstance.get('/customers'),
};

export default axiosInstance;
