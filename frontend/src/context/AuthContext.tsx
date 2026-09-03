import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export interface AuthContextType {
  token: string | null;
  isAuthenticated: boolean;
  userEmail: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'access_token';
const LEGACY_TOKEN_KEY = 'token';
const USER_EMAIL_KEY = 'user_email';

function parseEmailFromToken(jwt: string | null): string | null {
  if (!jwt) return null;
  try {
    const parts = jwt.split('.');
    if (parts.length < 2) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const decoded = JSON.parse(jsonPayload);
    return decoded.email || decoded.sub || null;
  } catch {
    return null;
  }
}

function getStoredToken(): string | null {
  const token = localStorage.getItem(TOKEN_KEY) || localStorage.getItem(LEGACY_TOKEN_KEY);
  return token && token.trim().length > 0 ? token : null;
}

function saveToken(token: string, email?: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(LEGACY_TOKEN_KEY, token);
  const resolvedEmail = email || parseEmailFromToken(token);
  if (resolvedEmail) {
    localStorage.setItem(USER_EMAIL_KEY, resolvedEmail);
  }
}

function clearStoredAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(USER_EMAIL_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken);
  const [userEmail, setUserEmail] = useState<string | null>(() => {
    return localStorage.getItem(USER_EMAIL_KEY) || parseEmailFromToken(getStoredToken());
  });

  const logout = useCallback(() => {
    clearStoredAuth();
    setToken(null);
    setUserEmail(null);
  }, []);

  // Listen for 401 unauthorized events dispatched by API interceptors
  useEffect(() => {
    const handleAuthLogout = () => {
      logout();
    };

    window.addEventListener('auth:logout', handleAuthLogout);
    return () => {
      window.removeEventListener('auth:logout', handleAuthLogout);
    };
  }, [logout]);

  // Keep state in sync across browser tabs
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === TOKEN_KEY || e.key === LEGACY_TOKEN_KEY) {
        const currentToken = getStoredToken();
        setToken(currentToken);
        setUserEmail(localStorage.getItem(USER_EMAIL_KEY) || parseEmailFromToken(currentToken));
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    try {
      const response = await api.post('/auth/login', { email, password });
      const accessToken = response.data.access_token;
      if (!accessToken) {
        throw new Error('No access token returned from server.');
      }
      saveToken(accessToken, email);
      setToken(accessToken);
      setUserEmail(email || parseEmailFromToken(accessToken));
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      let message = 'Login failed. Please check your credentials.';

      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
      } else if (status === 401) {
        message = 'Invalid email or password.';
      } else if (err.message) {
        message = err.message;
      }
      throw new Error(message);
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    try {
      const response = await api.post('/auth/register', { email, password });
      const accessToken = response.data.access_token;
      if (!accessToken) {
        throw new Error('No access token returned from server.');
      }
      saveToken(accessToken, email);
      setToken(accessToken);
      setUserEmail(email || parseEmailFromToken(accessToken));
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      let message = 'Registration failed. Please try again.';

      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
      } else if (status === 409) {
        message = 'An account with this email already exists.';
      } else if (err.message) {
        message = err.message;
      }
      throw new Error(message);
    }
  }, []);

  const value: AuthContextType = {
    token,
    isAuthenticated: Boolean(token),
    userEmail,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    // Graceful fallback for components rendered outside AuthProvider (e.g. isolated unit tests)
    const currentToken = getStoredToken();
    return {
      token: currentToken,
      isAuthenticated: Boolean(currentToken),
      userEmail: localStorage.getItem(USER_EMAIL_KEY) || parseEmailFromToken(currentToken),
      login: async () => {},
      register: async () => {},
      logout: () => {},
    };
  }
  return context;
}

export default AuthContext;
