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

export async function generateProposal(query, useWebSearch = false, conversationId = null, tone = "balanced", personName = "", companyName = "", outputFormat = "proposal") {
  const MAX_RETRIES = 2;
  const RETRY_DELAY_MS = 800;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const { data } = await client.post("/generate-proposal/", {
        query,
        use_web_search: useWebSearch,
        conversation_id: conversationId,
        tone,
        person_name: personName,
        company_name: companyName,
        output_format: outputFormat,
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

export async function generateProposalStream(query, useWebSearch = false, conversationId = null, tone = "balanced", personName = "", companyName = "", outputFormat = "proposal", onProgress) {
  const headers = {
    "Content-Type": "application/json",
  };
  if (_accessToken) {
    headers["Authorization"] = `Bearer ${_accessToken}`;
  }

  let response = await fetch("/api/generate-proposal/stream/", {
    method: "POST",
    headers,
    body: JSON.stringify({
      query,
      use_web_search: useWebSearch,
      conversation_id: conversationId,
      tone,
      person_name: personName,
      company_name: companyName,
      output_format: outputFormat,
    }),
  });

  if (response.status === 401) {
    try {
      const session = JSON.parse(localStorage.getItem(SESSION_KEY));
      if (session?.refresh) {
        const { data } = await axios.post("/api/auth/token/refresh/", { refresh: session.refresh });
        _accessToken = data.access;
        localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, refresh: data.refresh }));
        headers["Authorization"] = `Bearer ${data.access}`;
        
        response = await fetch("/api/generate-proposal/stream/", {
          method: "POST",
          headers,
          body: JSON.stringify({
            query,
            use_web_search: useWebSearch,
            conversation_id: conversationId,
            tone,
            person_name: personName,
            company_name: companyName,
            output_format: outputFormat,
          }),
        });
      }
    } catch (refreshErr) {
      _onUnauthenticated?.();
      throw new Error("Authentication session expired.");
    }
  }

  if (!response.ok) {
    let errorMsg = "Failed to generate proposal";
    try {
      const errData = await response.json();
      errorMsg = errData.error || errorMsg;
    } catch {}
    throw new Error(errorMsg);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const jsonStr = line.slice(6).trim();
          if (jsonStr) {
            const data = JSON.parse(jsonStr);
            onProgress(data);
          }
        } catch (e) {
          console.error("Failed to parse stream chunk:", e, line);
        }
      }
    }
  }

  // Flush remaining buffer after stream ends
  if (buffer && buffer.startsWith("data: ")) {
    try {
      const jsonStr = buffer.slice(6).trim();
      if (jsonStr) {
        const data = JSON.parse(jsonStr);
        onProgress(data);
      }
    } catch (e) {
      console.error("Failed to parse final stream chunk:", e, buffer);
    }
  }
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
