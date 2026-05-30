import axios from "axios";

export const SESSION_KEY = "dracarys_session";

export const client = axios.create({
  baseURL: "/api",
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
    // Only attempt refresh on 401, and only once per request
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
          .post("/api/auth/token/refresh/", { refresh: session.refresh })
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

export async function generateProposal(query, useWebSearch = false) {
  const MAX_RETRIES = 2;
  const RETRY_DELAY_MS = 800;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const { data } = await client.post("/generate-proposal/", {
        query,
        use_web_search: useWebSearch,
      });
      return data;
    } catch (err) {
      if (isConnectionError(err) && attempt < MAX_RETRIES) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }
      throw err;
    }
  }
}
