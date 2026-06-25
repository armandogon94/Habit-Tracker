"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiJson, setAccessToken } from "./api";
import type { TokenResponse, User } from "@/types/habit";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8020";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const u = await apiJson<User>("/api/v1/auth/me");
      setUser(u);
    } catch {
      setUser(null);
      setAccessToken(null);
    }
  }, []);

  // Try refreshing on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (res.ok) {
          const data: TokenResponse = await res.json();
          setAccessToken(data.access_token);
          await fetchUser();
        }
      } catch {
        // Not logged in
      } finally {
        setLoading(false);
      }
    })();
  }, [fetchUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(err.detail);
      }
      // Drop any cached data from a previous session before this user's data loads.
      queryClient.clear();
      const data: TokenResponse = await res.json();
      setAccessToken(data.access_token);
      await fetchUser();
    },
    [fetchUser, queryClient]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      // Send the browser's IANA timezone so the backend's date math (streaks,
      // "today") matches the calendar day the UI logs completions against.
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const res = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, timezone }),
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Registration failed" }));
        throw new Error(err.detail);
      }
      queryClient.clear();
      const data: TokenResponse = await res.json();
      setAccessToken(data.access_token);
      await fetchUser();
    },
    [fetchUser, queryClient]
  );

  const logout = useCallback(async () => {
    await fetch(`${API_URL}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    setAccessToken(null);
    setUser(null);
    // Prevent the next user on this device from seeing cached habit data.
    queryClient.clear();
  }, [queryClient]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
