"use client";

import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useRef, useState } from "react";
import { api, tokens, WS_URL } from "./api";
import { useAuth } from "./auth";

export type RtEvent = { event: string; [k: string]: unknown };
type Listener = (e: RtEvent) => void;

interface RealtimeCtx {
  unread: number;
  setUnread: (n: number) => void;
  subscribe: (fn: Listener) => () => void;
  connected: boolean;
}

const Ctx = createContext<RealtimeCtx | null>(null);

/** One WebSocket per signed-in user: notifications + unit feed. Reconnects with backoff. */
export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [unread, setUnreadState] = useState(0);
  const [connected, setConnected] = useState(false);
  const listeners = useRef(new Set<Listener>());

  const setUnread = useCallback((n: number) => setUnreadState(Math.max(0, n)), []);

  const subscribe = useCallback((fn: Listener) => {
    listeners.current.add(fn);
    return () => {
      listeners.current.delete(fn);
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    let ws: WebSocket | null = null;
    let stopped = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout>;
    let ping: ReturnType<typeof setInterval>;

    api<{ count: number }>("/notifications/unread-count").then((r) => setUnread(r.count)).catch(() => {});

    const connect = () => {
      const token = tokens.access;
      if (!token || stopped) return;
      ws = new WebSocket(`${WS_URL}/ws/notifications?token=${encodeURIComponent(token)}`);
      ws.onopen = () => {
        attempt = 0;
        setConnected(true);
        ping = setInterval(() => ws?.readyState === 1 && ws.send("ping"), 25000);
      };
      ws.onmessage = (m) => {
        let data: RtEvent;
        try {
          data = JSON.parse(m.data);
        } catch {
          return;
        }
        if (data.event === "notification") setUnreadState((n) => n + 1);
        if (data.event === "unread_count") setUnread(Number(data.count) || 0);
        listeners.current.forEach((fn) => fn(data));
      };
      ws.onclose = () => {
        setConnected(false);
        clearInterval(ping);
        if (stopped) return;
        attempt += 1;
        // Token may have expired: refresh through a cheap authenticated call before reconnecting.
        api("/auth/me").catch(() => {});
        timer = setTimeout(connect, Math.min(15000, 1000 * 2 ** attempt));
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      clearInterval(ping);
      ws?.close();
    };
  }, [user, setUnread]);

  return <Ctx.Provider value={{ unread, setUnread, subscribe, connected }}>{children}</Ctx.Provider>;
}

export function useRealtime() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useRealtime outside provider");
  return ctx;
}

export function useRealtimeEvent(fn: Listener) {
  const { subscribe } = useRealtime();
  const ref = useRef(fn);
  useLayoutEffect(() => {
    ref.current = fn;
  });
  useEffect(() => subscribe((e) => ref.current(e)), [subscribe]);
}

/** Per-request channel: status changes, chat messages, typing indicator, read receipts. */
export function useRequestSocket(requestId: string | undefined, onEvent: Listener) {
  const ref = useRef(onEvent);
  useLayoutEffect(() => {
    ref.current = onEvent;
  });
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!requestId) return;
    let stopped = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout>;
    const connect = () => {
      const token = tokens.access;
      if (!token || stopped) return;
      const ws = new WebSocket(`${WS_URL}/ws/requests/${encodeURIComponent(requestId)}?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;
      ws.onopen = () => {
        attempt = 0;
        ref.current({ event: "socket_open" });
      };
      ws.onmessage = (m) => {
        try {
          ref.current(JSON.parse(m.data));
        } catch {}
      };
      ws.onclose = (ev) => {
        if (stopped || ev.code === 4403) return;
        attempt += 1;
        timer = setTimeout(connect, Math.min(15000, 1000 * 2 ** attempt));
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [requestId]);

  return useCallback((payload: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
  }, []);
}
