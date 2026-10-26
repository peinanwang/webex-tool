import { useEffect, useState } from "react";
import { api, type Status } from "../api";
import { copy } from "../copy";
import { useEvents } from "../useEvents";
import { Button } from "./Chips";

const secondsAgo = (iso: string | null) => (iso ? Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 1000)) : null);

export function TopBar() {
  const [status, setStatus] = useState<Status | null>(null);
  const [, tick] = useState(0);
  const load = () => api.status().then(setStatus).catch(() => setStatus(null));

  useEffect(() => {
    load();
    const refresh = setInterval(load, 10000);
    const clock = setInterval(() => tick((t) => t + 1), 1000);
    return () => { clearInterval(refresh); clearInterval(clock); };
  }, []);
  useEvents({ focus_changed: load, message_stored: load, reconnected: load });

  const focus = status?.focus;
  const ago = secondsAgo(status?.listener.last_ok_at ?? null);
  const polling = status?.listener.mode === "polling";
  const healthy = status && (!polling || (ago !== null && ago < Math.max(15, status.listener.poll_interval * 5)));

  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-line bg-panel px-5">
      {focus?.on ? (
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ok opacity-60" /><span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-ok" /></span>
          <span className="font-semibold">{copy.focus.on}</span>
          <span className="text-sm text-muted">since {focus.since} · {focus.duration} · <b className="text-high">{focus.counts?.high ?? 0}</b> {copy.focus.high} · <b className="text-ink">{focus.counts?.regular ?? 0}</b> {copy.focus.held}</span>
          <Button small onClick={async () => { await api.setFocus(false); load(); }}>{copy.focus.turnOff}</Button>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-gray-300" />
          <span className="font-semibold">{copy.focus.off}</span>
          <span className="text-sm text-muted">{copy.focus.offHint}</span>
          <Button small kind="primary" onClick={async () => { await api.setFocus(true); load(); }}>🎯 {copy.focus.turnOn}</Button>
        </div>
      )}
      <div className="flex-1" />
      {status && (
        <div className="flex items-center gap-4 text-xs text-muted">
          <span title={status.listener.last_error ?? ""} className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${healthy ? "bg-ok" : "bg-red-500"}`} />
            {healthy ? copy.health.ok : copy.health.stale}{polling && ago !== null ? ` · ${ago}s ago` : polling ? "" : " · webhook"}
          </span>
          <span className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${status.llm.configured ? "bg-violet-500" : "bg-gray-300"}`} />
            {status.llm.configured ? `${copy.health.ai} · ${status.llm.model}` : copy.health.noAi}
          </span>
          {status.user.name && <span className="hidden lg:inline">{status.user.name}</span>}
        </div>
      )}
      {!status && <span className="text-xs text-red-600">Can't reach the Webex Focus app. Is `python -m listener` running?</span>}
    </header>
  );
}
