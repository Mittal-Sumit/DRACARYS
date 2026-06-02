import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { setAccessToken, setUnauthenticatedHandler, SESSION_KEY, loginUser, signupUser, refreshAccessToken } from "../api/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(true);

  const logout = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem(SESSION_KEY);
  }, []);

  useEffect(() => {
    setUnauthenticatedHandler(logout);
    return () => setUnauthenticatedHandler(null);
  }, [logout]);

  // Restore session on page load using stored refresh token.
  // Cleanup cancels stale callbacks from React StrictMode's double-invoke.
  useEffect(() => {
    const session = (() => {
      try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch { return null; }
    })();

    if (!session?.refresh) {
      setBootstrapping(false);
      return;
    }

    let cancelled = false;

    refreshAccessToken(session.refresh)
      .then((data) => {
        if (cancelled) return;
        setAccessToken(data.access);
        if (data.refresh) {
          localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, refresh: data.refresh }));
        }
        setUser({ username: session.username, email: session.email });
      })
      .catch(() => {
        if (!cancelled) localStorage.removeItem(SESSION_KEY);
      })
      .finally(() => {
        if (!cancelled) setBootstrapping(false);
      });

    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await loginUser(email, password);
    setAccessToken(data.access);
    setUser({ username: data.username, email: data.email });
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      refresh: data.refresh,
      username: data.username,
      email: data.email,
    }));
  }, []);

  const signup = useCallback(async (email, password) => {
    const data = await signupUser(email, password);
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
