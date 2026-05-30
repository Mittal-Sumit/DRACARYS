import { createContext, useContext, useState, useEffect, useCallback } from "react";
import axios from "axios";
import { setAccessToken, setUnauthenticatedHandler, SESSION_KEY } from "../api/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(true);

  const logout = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem("dracarys_messages");
  }, []);

  useEffect(() => {
    setUnauthenticatedHandler(logout);
    return () => setUnauthenticatedHandler(null);
  }, [logout]);

  // Restore session on page load using stored refresh token
  useEffect(() => {
    const session = (() => {
      try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch { return null; }
    })();

    if (!session?.refresh) {
      setBootstrapping(false);
      return;
    }

    axios
      .post("/api/auth/token/refresh/", { refresh: session.refresh })
      .then(({ data }) => {
        setAccessToken(data.access);
        if (data.refresh) {
          localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, refresh: data.refresh }));
        }
        setUser({ username: session.username, email: session.email });
      })
      .catch(() => {
        localStorage.removeItem(SESSION_KEY);
      })
      .finally(() => setBootstrapping(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const { data } = await axios.post("/api/auth/login/", { email, password });
    setAccessToken(data.access);
    setUser({ username: data.username, email: data.email });
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      refresh: data.refresh,
      username: data.username,
      email: data.email,
    }));
  }, []);

  const signup = useCallback(async (email, password) => {
    const { data } = await axios.post("/api/auth/signup/", { email, password });
    setAccessToken(data.access);
    setUser({ username: data.username, email: data.email });
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      refresh: data.refresh,
      username: data.username,
      email: data.email,
    }));
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, bootstrapping }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
