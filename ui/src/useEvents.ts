import { useEffect, useRef } from "react";

// Live updates from the Python app (Server-Sent Events at /api/events).
// The browser's EventSource keeps one connection open and reconnects by itself if it drops.
// Each page subscribes to the event types it cares about, e.g. useEvents({ message_stored: reload }).
type Handlers = Record<string, (data: any) => void>;

let source: EventSource | null = null;
const listeners = new Set<{ current: Handlers }>();
const TYPES = ["message_stored", "message_updated", "chat_turn", "assistant_thinking", "focus_changed", "summary_created"];

function connect() {
  if (source) return;
  source = new EventSource("/api/events");
  for (const type of TYPES) {
    source.addEventListener(type, (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      listeners.forEach((l) => l.current[type]?.(data));
    });
  }
  // After a reconnect, pages refetch so they don't miss anything that happened while disconnected.
  source.addEventListener("open", () => listeners.forEach((l) => l.current["reconnected"]?.(null)));
}

export function useEvents(handlers: Handlers) {
  const ref = useRef(handlers);
  ref.current = handlers;
  useEffect(() => {
    connect();
    listeners.add(ref);
    return () => { listeners.delete(ref); };
  }, []);
}
