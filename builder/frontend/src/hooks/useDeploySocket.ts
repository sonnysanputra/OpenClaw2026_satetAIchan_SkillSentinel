"use client";
import { useEffect, useRef, useState } from "react";
import type { LogMessage, WsMessage } from "@/types";
import { wsBase } from "@/lib/api";

export function useDeploySocket(sessionId: string | null) {
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [status, setStatus] = useState<"idle" | "deploying" | "completed" | "failed">("idle");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    setStatus("deploying");
    const ws = new WebSocket(`${wsBase}/ws/deploy/${sessionId}`);
    wsRef.current = ws;
    ws.onmessage = (e) => {
      try {
        const msg: WsMessage = JSON.parse(e.data);
        if (msg.type === "log") setLogs((prev) => [...prev, msg]);
        else if (msg.type === "status") setStatus(msg.status);
      } catch {
        /* ignore */
      }
    };
    ws.onerror = () => setStatus("failed");
    ws.onclose = () =>
      setStatus((cur) => (cur === "deploying" ? "failed" : cur));
    return () => ws.close();
  }, [sessionId]);

  return { logs, status };
}
