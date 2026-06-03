import axios from "axios";

export const SESSION_KEY = "dracarys_session";

// In dev: VITE_API_BASE_URL is unset → "" → Vite proxy handles /api → localhost:8000
// In prod: VITE_API_BASE_URL=https://<hf-space>.hf.space → full cross-origin URL
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export const client = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 60000,
});

// Module-level token store — written by AuthContext, read by interceptor
let _accessToken = null;
let _onUnauthenticated = null;
let _refreshPromise = null; // deduplicates concurrent refresh calls

export const setAccessToken = (token) => { _accessToken = token; };
export const setUnauthenticatedHandler = (fn) => { _onUnauthenticated = fn; };

client.interceptors.request.use((config) => {
  if (_accessToken) config.headers.Authorization = `Bearer ${_accessToken}`;
  return config;
});

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status !== 401 || error.config._retry) {
      return Promise.reject(error);
    }
    error.config._retry = true;

    const session = (() => {
      try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch { return null; }
    })();

    if (!session?.refresh) {
      _onUnauthenticated?.();
      return Promise.reject(error);
    }

    try {
      if (!_refreshPromise) {
        _refreshPromise = axios
          .post(`${API_BASE}/api/auth/token/refresh/`, { refresh: session.refresh })
          .finally(() => { _refreshPromise = null; });
      }
      const { data } = await _refreshPromise;
      _accessToken = data.access;
      if (data.refresh) {
        localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, refresh: data.refresh }));
      }
      error.config.headers.Authorization = `Bearer ${data.access}`;
      return client(error.config);
    } catch {
      _onUnauthenticated?.();
      return Promise.reject(error);
    }
  }
);

const isConnectionError = (err) =>
  !err.response || err.response.status === 502 || err.response.status === 503;

const withRetry = async (fn, maxRetries = 2, delay = 1000) => {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (isConnectionError(err) && attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      throw err;
    }
  }
};

export const loginUser = (email, password) =>
  axios.post(`${API_BASE}/api/auth/login/`, { email, password }).then((r) => r.data);

export const signupUser = (email, password) =>
  axios.post(`${API_BASE}/api/auth/signup/`, { email, password }).then((r) => r.data);

export const refreshAccessToken = (refresh) =>
  axios.post(`${API_BASE}/api/auth/token/refresh/`, { refresh }).then((r) => r.data);

export const forgotPassword = (email) =>
  axios.post(`${API_BASE}/api/auth/forgot-password/`, { email }).then((r) => r.data);

export const resetPassword = (uid, token, newPassword) =>
  axios.post(`${API_BASE}/api/auth/reset-password/`, { uid, token, new_password: newPassword }).then((r) => r.data);

export async function generateProposal(query, useWebSearch = false, conversationId = null, tone = "balanced") {
  return withRetry(() =>
    client
      .post("/generate-proposal/", {
        query,
        use_web_search: useWebSearch,
        conversation_id: conversationId,
        tone,
      })
      .then((r) => r.data),
    2,
    800
  );
}

export async function getConversations() {
  const { data } = await client.get("/conversations/");
  return data;
}

export async function getConversation(id) {
  const { data } = await client.get(`/conversations/${id}/`);
  return data;
}

export async function deleteConversation(id) {
  await client.delete(`/conversations/${id}/`);
}
