import { useEffect, useState } from "react";
import { api, localDate, type Message, type TriageStats } from "../api";
import { CategoryChip, DecidedByChip, PageHeader } from "../components/Chips";
import { FeedbackButtons } from "../components/Feedback";
import { copy } from "../copy";
import { go } from "../router";
import { useEvents } from "../useEvents";

type Filter = "all" | "high" | "regular" | "review";

export function TriageTab({ focusId }: { focusId?: string }) {
  const [date, setDate] = useState(localDate());
  const [filter, setFilter] = useState<Filter>("all");
  const [q, setQ] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [stats, setStats] = useState<TriageStats | null>(null);
  const [selected, setSelected] = useState<string | undefined>(focusId);
  const [fresh, setFresh] = useState<Set<string>>(new Set());

  const load = () => {
    api.messages({ start: date, end: date, q, category: filter === "high" || filter === "regular" ? filter : "", needs_review: filter === "review" })
      .then((rows) => setMessages(rows.filter((m) => m.category !== "self")));
    api.stats(date, date).then(setStats);
  };
  useEffect(load, [date, filter, q]);
  useEffect(() => { if (focusId) setSelected(focusId); }, [focusId]);

  useEvents({
    message_stored: (m: Message) => {
      if (m.category === "self" || date !== localDate()) return;
      setFresh((s) => new Set(s).add(m.id));
      setTimeout(() => setFresh((s) => { const n = new Set(s); n.delete(m.id); return n; }), 4000);
      load();
    },
    message_updated: load,
    reconnected: load,
  });

  const update = (u: Message) => { setMessages((ms) => ms.map((m) => (m.id === u.id ? u : m))); api.stats(date, date).then(setStats); };
  const current = messages.find((m) => m.id === selected);
  const count = (f: Filter) => (stats ? { all: stats.total, high: stats.high, regular: stats.regular, review: stats.needs_review }[f] : 0);

  return (
    <div className="flex h-full flex-col">
      <PageHeader title={copy.triage.title} subtitle={copy.triage.subtitle}>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="rounded-lg border border-line px-2 py-1.5 text-sm" />
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-panel px-6 py-2.5">
        {(["all", "high", "regular", "review"] as Filter[]).map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`rounded-full px-3 py-1 text-sm ${filter === f ? "bg-ink text-white" : "bg-gray-100 text-ink hover:bg-gray-200"}`}>
            {copy.triage.filters[f]} <span className="opacity-60">{count(f)}</span>
          </button>
        ))}
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={copy.triage.search}
          className="ml-2 w-56 rounded-lg border border-line px-3 py-1.5 text-sm" />
        <div className="flex-1" />
        {stats && (
          <div className="text-sm text-muted">
            {copy.triage.reviewed} <b className="text-ink">{stats.overall.reviewed}</b>
            {stats.overall.accuracy !== null && <> · {copy.triage.accuracy} <b className="text-ink">{stats.overall.accuracy}%</b></>}
            {stats.ai.accuracy !== null && <> (AI {stats.ai.accuracy}%{stats.rules.accuracy !== null ? `, rules ${stats.rules.accuracy}%` : ""})</>}
          </div>
        )}
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1 overflow-y-auto">
          {messages.length === 0 && <p className="py-16 text-center text-sm text-muted">{copy.triage.empty}</p>}
          {messages.map((m) => (
            <div key={m.id} onClick={() => setSelected(m.id)}
              className={`cursor-pointer border-b border-line px-6 py-3 transition ${selected === m.id ? "bg-accent-soft/60" : fresh.has(m.id) ? "bg-yellow-50" : "bg-panel hover:bg-gray-50"}`}>
              <div className="flex items-center gap-2 text-sm">
                <span className="w-12 shrink-0 text-xs text-muted">{m.time}</span>
                <span className="font-medium">{m.sender}</span>
                <span className="text-muted">{m.is_direct ? "· 1:1" : `· ${m.space}`}</span>
                {m.mentioned_me && <span className="rounded bg-amber-100 px-1.5 text-[11px] font-medium text-amber-800">@you</span>}
                <span className="flex-1" />
                <CategoryChip category={m.category} />
              </div>
              <div className="mt-1 line-clamp-2 pl-14 text-sm">{m.text}</div>
              <div className="mt-1.5 flex items-center justify-between gap-3 pl-14">
                <div className="flex min-w-0 items-center gap-2 text-xs text-muted">
                  <DecidedByChip m={m} /><span className="truncate">{m.reason}</span>
                  {m.notified && <span title={copy.triage.notified}>· 🔔 pinged</span>}
                </div>
                <FeedbackButtons m={m} onDone={update} />
              </div>
            </div>
          ))}
        </div>

        {current && (
          <aside className="w-96 shrink-0 overflow-y-auto border-l border-line bg-panel p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">{copy.triage.details}</h2>
              <button className="text-muted hover:text-ink" onClick={() => setSelected(undefined)}>✕</button>
            </div>
            <div className="text-sm"><b>{current.sender}</b> <span className="text-muted">({current.sender_email})</span></div>
            <div className="text-sm text-muted">{current.is_direct ? "1:1 chat" : current.space} · {current.time}</div>
            <p className="my-3 whitespace-pre-wrap rounded-lg bg-canvas p-3 text-sm">{current.text}</p>
            <dl className="space-y-1.5 text-sm">
              <div className="flex gap-2"><dt className="w-28 text-muted">Category</dt><dd><CategoryChip category={current.category} /></dd></div>
              <div className="flex gap-2"><dt className="w-28 text-muted">{copy.triage.why}</dt><dd className="min-w-0 break-words">{current.reason}</dd></div>
              <div className="flex gap-2"><dt className="w-28 text-muted">Decided by</dt><dd><DecidedByChip m={current} /></dd></div>
              <div className="flex gap-2"><dt className="w-28 text-muted">{copy.triage.mentioned}</dt><dd>{current.mentioned_me ? "Yes" : "No"}</dd></div>
              <div className="flex gap-2"><dt className="w-28 text-muted">{copy.triage.focusAtTime}</dt><dd>{current.focus_on ? "On" : "Off"}</dd></div>
              <div className="flex gap-2"><dt className="w-28 text-muted">{copy.triage.notified}</dt><dd>{current.notified ? "Yes" : "No"}</dd></div>
            </dl>
            <div className="mt-4"><FeedbackButtons m={current} onDone={update} /></div>
            <div className="mt-5 border-t border-line pt-4">
              <div className="mb-2 text-sm font-medium">{copy.triage.makeRule}</div>
              <div className="flex flex-col gap-1.5">
                {current.sender_email && (
                  <RuleShortcut label={`Messages from ${current.sender_email}`} params={{ match_type: "sender", value: current.sender_email }} m={current} />
                )}
                {!current.is_direct && <RuleShortcut label={`Anything in "${current.space}"`} params={{ match_type: "space", value: current.space }} m={current} />}
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function RuleShortcut({ label, params, m }: { label: string; params: Record<string, string>; m: Message }) {
  // Suggest the opposite category, since that's usually why you'd make a rule from a message.
  const category = m.feedback === "should_be_high" || (m.category === "regular" && m.feedback !== "correct") ? "high" : m.category === "high" ? "regular" : "high";
  return (
    <button onClick={() => go("rules", { ...params, category })}
      className="rounded-lg border border-line px-3 py-2 text-left text-sm hover:border-accent hover:bg-accent-soft/40">
      {label} → <b>{category === "high" ? "High" : "Regular"}</b>
    </button>
  );
}
