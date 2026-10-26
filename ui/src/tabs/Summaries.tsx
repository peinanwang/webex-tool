import { useEffect, useState } from "react";
import { api, localDate, outboxPreviewUrl, type Summary } from "../api";
import { Button, ErrorNote, PageHeader } from "../components/Chips";
import { Markdown } from "../components/Markdown";
import { copy } from "../copy";
import { go } from "../router";
import { useEvents } from "../useEvents";

const KIND_STYLE: Record<string, string> = {
  end_of_day: "bg-indigo-100 text-indigo-700", focus_session: "bg-ok-soft text-ok", on_demand: "bg-gray-100 text-gray-600",
};

export function SummariesTab({ selectedId }: { selectedId?: number }) {
  const [kind, setKind] = useState("");
  const [list, setList] = useState<Summary[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<{ open: boolean; start: string; end: string; scope: string }>({ open: false, start: localDate(), end: localDate(), scope: "held" });
  const [copied, setCopied] = useState(false);

  const load = () => api.summaries(kind).then(setList).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [kind]);
  useEvents({ summary_created: load, reconnected: load });

  const current = list.find((s) => s.id === selectedId) ?? (selectedId ? undefined : list[0]);
  const act = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label); setError(null);
    try { await fn(); await load(); } catch (e) { setError((e as Error).message); } finally { setBusy(null); }
  };

  return (
    <div className="flex h-full flex-col">
      <PageHeader title={copy.summaries.title} subtitle={copy.summaries.subtitle}>
        <select className="rounded-lg border border-line px-2 py-1.5 text-sm" value={kind} onChange={(e) => setKind(e.target.value)}>
          {Object.entries(copy.summaries.kinds).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
        <Button kind="primary" onClick={() => setForm({ ...form, open: !form.open })}>＋ {copy.summaries.new}</Button>
      </PageHeader>

      {form.open && (
        <div className="flex flex-wrap items-center gap-2 border-b border-line bg-panel px-6 py-3 text-sm">
          From <input type="date" className="rounded-lg border border-line px-2 py-1" value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} />
          to <input type="date" className="rounded-lg border border-line px-2 py-1" value={form.end} onChange={(e) => setForm({ ...form, end: e.target.value })} />
          <select className="rounded-lg border border-line px-2 py-1" value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })}>
            <option value="held">{copy.summaries.held}</option><option value="all">{copy.summaries.all}</option>
          </select>
          <Button kind="primary" disabled={!!busy} onClick={() => act("create", async () => {
            // A single day "until now" for today; whole days otherwise.
            const today = localDate();
            const s = await api.createSummary({ start: form.start, end: form.end === today && form.start === today ? "" : form.end, scope: form.scope });
            setForm({ ...form, open: false });
            go("summaries", { id: String(s.id) });
          })}>{busy === "create" ? copy.summaries.creating : copy.summaries.create}</Button>
        </div>
      )}
      <div className="px-6 pt-3"><ErrorNote error={error} /></div>

      <div className="flex min-h-0 flex-1">
        <div className="w-80 shrink-0 overflow-y-auto border-r border-line bg-panel">
          {list.length === 0 && <p className="p-6 text-sm text-muted">{copy.summaries.empty}</p>}
          {list.map((s) => (
            <button key={s.id} onClick={() => go("summaries", { id: String(s.id) })}
              className={`block w-full border-b border-line px-4 py-3 text-left ${current?.id === s.id ? "bg-accent-soft/60" : "hover:bg-gray-50"}`}>
              <div className="flex items-center gap-2">
                <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${KIND_STYLE[s.kind]}`}>{s.kind_label}</span>
                {s.scope === "all" && <span className="text-[11px] text-muted">everything</span>}
                <span className="flex-1" />
                {s.delivered_at && <span title={s.delivered_to ?? ""}>✉️</span>}
              </div>
              <div className="mt-1 text-sm font-medium">{s.period}</div>
              <div className="text-xs text-muted">#{s.id} · made {new Date(s.created).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</div>
            </button>
          ))}
        </div>

        <div className="min-w-0 flex-1 overflow-y-auto px-8 py-6">
          {!current ? <p className="text-sm text-muted">{copy.summaries.pick}</p> : (
            <div className="mx-auto max-w-3xl">
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <Button disabled={!!busy} onClick={() => act("regen", () => api.regenerate(current.id))}>↻ {busy === "regen" ? copy.summaries.creating : copy.summaries.regenerate}</Button>
                <Button disabled={!!busy} onClick={() => act("email", () => api.email(current.id))}>✉️ {copy.summaries.email}</Button>
                <Button onClick={async () => { await navigator.clipboard.writeText(current.markdown); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
                  {copied ? copy.summaries.copied : copy.summaries.copy}
                </Button>
                {current.delivered_to && (
                  <a className="text-sm text-accent hover:underline" href={outboxPreviewUrl(current.delivered_to)} target="_blank" rel="noreferrer">
                    {copy.summaries.openEmail} ↗
                  </a>
                )}
              </div>
              {current.delivered_at && (
                <p className="mb-3 text-xs text-muted">{copy.summaries.emailed} {new Date(current.delivered_at).toLocaleString()} → <code>{current.delivered_to}</code></p>
              )}
              <article className="rounded-xl border border-line bg-panel px-6 py-5 text-[15px]"><Markdown text={current.markdown} /></article>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
