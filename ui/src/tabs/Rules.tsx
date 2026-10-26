import { useEffect, useState } from "react";
import { api, type Contact, type Preview, type Rule, type Space } from "../api";
import { Button, CategoryChip, ErrorNote, PageHeader, Toggle } from "../components/Chips";
import { copy } from "../copy";
import { useRoute } from "../router";

const MATCH_TYPES = ["sender", "space", "keyword", "mention", "topic"] as const;

function ruleText(r: Pick<Rule, "match_type" | "value">) {
  switch (r.match_type) {
    case "sender": return <>Messages from <b>{r.value}</b></>;
    case "space": return <>Anything in <b>{r.value}</b></>;
    case "keyword": return <>Messages containing “<b>{r.value}</b>”</>;
    case "mention": return <>When I'm <b>@mentioned</b></>;
    default: return <>Anything about <b>{r.value}</b> <span className="text-xs text-violet-600">(judged by AI)</span></>;
  }
}

export function RulesTab() {
  const { params } = useRoute();
  const [rules, setRules] = useState<Rule[]>([]);
  const [error, setError] = useState<string | null>(null);
  const load = () => api.rules().then(setRules).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader title={copy.rules.title} subtitle={copy.rules.subtitle} />
      <div className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-6">
        <ErrorNote error={error} />
        <section className="overflow-hidden rounded-xl border border-line bg-panel">
          {rules.length === 0 && <p className="px-5 py-6 text-sm text-muted">{copy.rules.empty}</p>}
          {rules.map((r) => (
            <div key={r.id} className={`flex items-center gap-4 border-b border-line px-5 py-3 last:border-b-0 ${r.enabled ? "" : "opacity-55"}`}>
              <span className="w-8 font-mono text-xs text-muted">#{r.id}</span>
              <span className="flex-1 text-sm">{ruleText(r)}</span>
              <span className="text-muted">→</span>
              <CategoryChip category={r.category} />
              <Toggle on={r.enabled} label="Rule on/off" onChange={async (v) => { await api.setRuleEnabled(r.id, v); load(); }} />
              <button className="text-sm text-muted hover:text-red-600" title="Delete"
                onClick={async () => { if (confirm(copy.rules.deleteConfirm)) { await api.deleteRule(r.id); load(); } }}>🗑</button>
            </div>
          ))}
        </section>
        <NewRule key={JSON.stringify(params)} initial={params} onSaved={load} />
        <TryIt />
        <Profile />
      </div>
    </div>
  );
}

function NewRule({ initial, onSaved }: { initial: Record<string, string>; onSaved: () => void }) {
  const [category, setCategory] = useState(initial.category || "high");
  const [matchType, setMatchType] = useState(initial.match_type || "sender");
  const [value, setValue] = useState(initial.value || "");
  const [suggestions, setSuggestions] = useState<(Contact | Space)[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setPreview(null); setError(null); setSaved(false);
    if (matchType === "sender") api.contacts(value).then(setSuggestions);
    else if (matchType === "space") api.spaces(value).then(setSuggestions);
    else setSuggestions([]);
  }, [matchType, value, category]);

  const rule = { category, match_type: matchType, value: matchType === "mention" ? "" : value };
  const runPreview = async () => {
    try { setPreview(await api.previewRule(rule)); setError(null); } catch (e) { setError((e as Error).message); }
  };
  const save = async () => {
    try { await api.addRule(rule); setValue(""); setSaved(true); onSaved(); } catch (e) { setError((e as Error).message); }
  };

  const input = "rounded-lg border border-line bg-white px-2.5 py-1.5 text-sm";
  return (
    <section className="rounded-xl border border-line bg-panel p-5">
      <h2 className="mb-3 font-semibold">{copy.rules.add}</h2>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <select className={input} value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="high">🔔 High priority</option><option value="regular">Regular</option>
        </select>
        <span className="text-muted">{copy.rules.when}</span>
        <select className={input} value={matchType} onChange={(e) => setMatchType(e.target.value)}>
          {MATCH_TYPES.map((t) => <option key={t} value={t}>{copy.matchTypes[t]}</option>)}
        </select>
        {matchType !== "mention" && (
          <>
            {(matchType === "sender" || matchType === "space") && <span className="text-muted">{copy.rules.is}</span>}
            <input className={`${input} min-w-64 flex-1`} value={value} onChange={(e) => setValue(e.target.value)} list="rule-suggestions"
              placeholder={matchType === "sender" ? "bob@example.com" : matchType === "space" ? "Space title" : matchType === "keyword" ? "outage" : "the Q3 launch"} />
            <datalist id="rule-suggestions">
              {suggestions.map((s) => "email" in s
                ? <option key={s.email} value={s.email}>{s.name ?? ""}</option>
                : <option key={s.title} value={s.title}>{s.type === "direct" ? "1:1" : "space"}</option>)}
            </datalist>
          </>
        )}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <Button kind="primary" onClick={save}>{copy.rules.save}</Button>
        <Button onClick={runPreview}>{copy.rules.preview}</Button>
        {saved && <span className="text-sm text-ok">✓ Saved. It applies from the next message.</span>}
      </div>
      <div className="mt-3"><ErrorNote error={error} /></div>
      {preview && (
        <div className="mt-3 rounded-lg bg-canvas p-3 text-sm">
          {!preview.supported ? copy.rules.previewTopic
            : preview.changed.length === 0 ? `${copy.rules.previewNone} (checked ${preview.checked})`
              : (
                <>
                  <div className="mb-2 font-medium">Would change {preview.changed.length} of today's {preview.checked} messages:</div>
                  <ul className="space-y-1">
                    {preview.changed.slice(0, 10).map((m) => (
                      <li key={m.id} className="flex items-center gap-2">
                        <span className="text-xs text-muted">{m.time}</span><b>{m.sender}</b>
                        <span className="min-w-0 flex-1 truncate text-muted">{m.text}</span>
                        <CategoryChip category={m.category} /> → <CategoryChip category={m.new_category} />
                      </li>
                    ))}
                  </ul>
                </>
              )}
        </div>
      )}
    </section>
  );
}

function TryIt() {
  const [t, setT] = useState({ text: "", sender_email: "", space: "", mentioned: false });
  const [res, setRes] = useState<Awaited<ReturnType<typeof api.testRule>> | null>(null);
  const input = "rounded-lg border border-line bg-white px-2.5 py-1.5 text-sm";
  return (
    <section className="rounded-xl border border-line bg-panel p-5">
      <h2 className="mb-3 font-semibold">{copy.rules.testTitle}</h2>
      <div className="flex flex-wrap gap-2">
        <input className={input} placeholder="sender email" value={t.sender_email} onChange={(e) => setT({ ...t, sender_email: e.target.value })} />
        <input className={input} placeholder="space title" value={t.space} onChange={(e) => setT({ ...t, space: e.target.value })} />
        <input className={`${input} min-w-64 flex-1`} placeholder="message text" value={t.text} onChange={(e) => setT({ ...t, text: e.target.value })} />
        <label className="flex items-center gap-1.5 text-sm"><input type="checkbox" checked={t.mentioned} onChange={(e) => setT({ ...t, mentioned: e.target.checked })} /> @me</label>
        <Button onClick={async () => setRes(await api.testRule(t))}>{copy.rules.testButton}</Button>
      </div>
      {res && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          <CategoryChip category={res.category} />
          <span>because <b>{res.decided_by === "rule" ? res.reason : res.reason === "default:mention" ? "you're @mentioned" : "no rule matches"}</b></span>
          {res.ai_would_decide && <span className="text-violet-700">· for a real message, the AI would decide</span>}
          {res.category === "high" && !res.focus_on && <span className="text-muted">· focus is off, so no ping right now</span>}
        </div>
      )}
    </section>
  );
}

function Profile() {
  const [text, setText] = useState("");
  const [state, setState] = useState<{ aiOn: boolean; saved: boolean; error: string | null }>({ aiOn: false, saved: false, error: null });
  useEffect(() => { api.profile().then((p) => { setText(p.profile); setState((s) => ({ ...s, aiOn: p.ai_triage_on })); }); }, []);
  return (
    <section className="rounded-xl border border-line bg-panel p-5">
      <h2 className="font-semibold">{copy.rules.profileTitle}</h2>
      <p className="mb-3 text-sm text-muted">{copy.rules.profileHint}{!state.aiOn && " (AI triage is off right now: no OpenAI key, or AI_TRIAGE=off.)"}</p>
      <textarea className="h-24 w-full rounded-lg border border-line p-3 text-sm" value={text} onChange={(e) => { setText(e.target.value); setState({ ...state, saved: false }); }} />
      <div className="mt-2 flex items-center gap-2">
        <Button kind="primary" onClick={async () => {
          try { await api.setProfile(text); setState({ ...state, saved: true, error: null }); } catch (e) { setState({ ...state, error: (e as Error).message }); }
        }}>{copy.rules.profileSave}</Button>
        {state.saved && <span className="text-sm text-ok">✓ Saved</span>}
      </div>
      <div className="mt-2"><ErrorNote error={state.error} /></div>
    </section>
  );
}
