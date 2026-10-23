"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokens } from "./api";
import type { Role, User } from "./types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function homeFor(role: Role): string {
  if (role === "student") return "/dashboard";
  if (role === "admin") return "/analytics";
  return "/agent/board";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokens.access) {
      setLoading(false);
      return;
    }
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => tokens.clear())
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("qoldau:logout", onLogout);
    return () => window.removeEventListener("qoldau:logout", onLogout);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const t = await api<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      json: { email, password },
    });
    tokens.set(t.access_token, t.refresh_token);
    const me = await api<User>("/auth/me");
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {}
    tokens.clear();
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}

export const isStaff = (u: User | null) => !!u && u.role !== "student";
