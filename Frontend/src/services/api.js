const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api';

/**
 * Generic API request wrapper
 */
async function request(endpoint, options = {}) {
    const token = localStorage.getItem('token');

    const headers = {
        ...options.headers,
    };

    // Default to application/json if Content-Type is not provided
    if (!('Content-Type' in headers)) {
        headers['Content-Type'] = 'application/json';
    }
    // If strictly undefined (e.g. for FormData), remove it to let browser handle it
    else if (headers['Content-Type'] === undefined) {
        delete headers['Content-Type'];
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers,
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || data.error || 'Something went wrong');
        }

        return data;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

export const api = {
    // Auth
    login: (username, password) =>
        request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        }),

    register: (username, email, password, phone) =>
        request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, email, password, phone }),
        }),

    getMe: () => request('/auth/me'),

    updateProfile: (data) =>
        request('/auth/profile', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    changePassword: (old_password, new_password) =>
        request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({ old_password, new_password }),
        }),

    googleAuth: (data) =>
        request('/auth/google', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    // Documents
    uploadDocument: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('source', 'manual_upload');

        // request wrapper handles Content-Type automatically if we don't set it for FormData
        return request('/documents/upload', {
            method: 'POST',
            body: formData,
            headers: {
                // Let browser set the boundary for multipart/form-data
                'Content-Type': undefined,
            }
        });
    },

    uploadText: (text) =>
        request('/documents/upload-text', {
            method: 'POST',
            body: JSON.stringify({ text, source: 'pasted_text' }),
        }),

    // News
    listNews: (params = {}) => {
        const query = new URLSearchParams();
        Object.keys(params).forEach(key => {
            const val = params[key];
            if (Array.isArray(val)) {
                val.forEach(v => query.append(key, v));
            } else if (val !== null && val !== undefined) {
                query.append(key, val);
            }
        });
        return request(`/news/fetch?${query.toString()}`);
    },

    getArticle: (id) => request(`/news/article/${id}`),

    intelliSearch: (query) =>
        request('/intelli-search/search', {
            method: 'POST',
            body: JSON.stringify({ query }),
        }),

    analyzeArticle: (id, targetLang = 'en') =>
        request(`/news/analyze/${id}?target_lang=${targetLang}`),

    getAnalysis: (id) =>
        request(`/news/analyze/${id}`),

    getPipelineStatus: (id) => request(`/news/pipeline-status/${id}`),

    listDocuments: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/documents/list${query ? `?${query}` : ''}`);
    },
    getDocument: (id) => request(`/documents/${id}`),
    deleteDocument: (id) => request(`/documents/${id}`, { method: 'DELETE' }),
    translate: (text, sourceLang, targetLang) =>
        request('/translation/translate', {
            method: 'POST',
            body: JSON.stringify({ text, source_lang: sourceLang, target_lang: targetLang })
        }),
    detectLanguage: (text) =>
        request('/translation/detect', {
            method: 'POST',
            body: JSON.stringify({ text })
        }),
    generateSummary: (id) => request(`/documents/${id}/summarize`, { method: 'POST' }),
    extractKeywords: (id) => request(`/documents/${id}/extract-keywords`, { method: 'POST' }),
    analyzeSentiment: (id) => request(`/documents/${id}/analyze-sentiment`, { method: 'POST' }),

    // Dashboard
    getSentimentDistribution: () => request('/dashboard/sentiment-distribution'),
    getSentimentTrend: (interval = 'daily', hours = 168) => request(`/dashboard/sentiment-trend?interval=${interval}&hours=${hours}`),
    getFeatureEngagement: () => request('/dashboard/feature-engagement'),
    getGlobalStats: () => request('/dashboard/global-stats'),
};
