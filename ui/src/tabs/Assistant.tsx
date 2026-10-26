import { useEffect, useRef, useState } from "react";
import { api, type ChatTurn } from "../api";
import { ChatCard } from "../components/Cards";
import { ErrorNote } from "../components/Chips";
import { Markdown } from "../components/Markdown";
import { copy } from "../copy";
import { useEvents } from "../useEvents";

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const day = (iso: string) => new Date(iso).toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" });

// The same thread as the Webex Assistant space in Webex: turns typed there arrive live over SSE,
// and turns typed here are mirrored into Webex by the server.
export function AssistantTab() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [text, setText] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const load = () => api.chat().then(setTurns).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [turns.length, thinking]);

  useEvents({
    chat_turn: (turn: ChatTurn) => {
      setTurns((prev) => (prev.some((t) => t.id === turn.id) ? prev : [...prev, turn]));
      if (turn.role === "assistant") setThinking(false);
    },
    assistant_thinking: () => setThinking(true),
    reconnected: load,
  });

  const send = async (value: string) => {
    const message = value.trim();
    if (!message) return;
    setText(""); setError(null); setThinking(true);
    try {
      const turn = await api.send(message);
      setTurns((prev) => (prev.some((t) => t.id === turn.id) ? prev : [...prev, turn]));
    } catch (e) { setError((e as Error).message); setThinking(false); }
  };

  let lastDay = "";
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-line bg-panel px-6 py-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-accent to-violet-500 text-lg text-white">🎯</div>
        <div>
          <div className="font-semibold">{copy.assistant.title}</div>
          <div className="text-xs text-muted">{copy.assistant.subtitle}</div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto flex max-w-3xl flex-col gap-3">
          {turns.length === 0 && <p className="py-10 text-center text-sm text-muted">{copy.assistant.empty}</p>}
          {turns.map((t) => {
            const d = day(t.created);
            const divider = d !== lastDay ? (lastDay = d) : null;
            return (
              <div key={t.id}>
                {divider && <div className="my-3 text-center text-xs font-medium text-muted">{divider}</div>}
                <Turn turn={t} />
              </div>
            );
          })}
          {thinking && (
            <div className="flex items-center gap-1 pl-11 text-2xl leading-none text-muted" aria-label="Assistant is thinking">
              <span className="dot">•</span><span className="dot">•</span><span className="dot">•</span>
            </div>
          )}
          <div ref={bottom} />
        </div>
      </div>

      <div className="border-t border-line bg-panel px-6 py-3">
        <div className="mx-auto max-w-3xl">
          <ErrorNote error={error} />
          <div className="mb-2 flex flex-wrap gap-1.5">
            {copy.assistant.quick.map((q) => (
              <button key={q} onClick={() => send(q)}
                className="rounded-full border border-line bg-white px-3 py-1 text-xs text-ink hover:border-accent hover:text-accent">{q}</button>
            ))}
          </div>
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); send(text); }}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder={copy.assistant.placeholder} autoFocus
              className="flex-1 rounded-xl border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20" />
            <button type="submit" disabled={!text.trim()}
              className="rounded-xl bg-accent px-5 text-sm font-medium text-white disabled:opacity-40">{copy.assistant.send}</button>
          </form>
        </div>
      </div>
    </div>
  );
}

function Turn({ turn }: { turn: ChatTurn }) {
  if (turn.role === "user") {
    return (
      <div className="flex flex-col items-end">
        <div className="bubble-user max-w-[80%] rounded-2xl rounded-br-md bg-accent px-4 py-2 text-sm text-white">
          <Markdown text={turn.text} />
        </div>
        <div className="mt-0.5 text-[11px] text-muted">{time(turn.created)} · {turn.source === "webex" ? copy.assistant.viaWebex : copy.assistant.viaWeb}</div>
      </div>
    );
  }
  const notice = turn.role === "notice";
  return (
    <div className="flex gap-3">
      <div className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm ${notice ? "bg-high-soft" : "bg-violet-100"}`}>
        {notice ? "🔔" : "🤖"}
      </div>
      <div className="min-w-0 max-w-[85%]">
        <div className={`rounded-2xl rounded-tl-md px-4 py-2 text-sm ${notice ? "border border-high/20 bg-high-soft/60" : "border border-line bg-white"}`}>
          <Markdown text={turn.text} />
        </div>
        {turn.cards.slice(0, 5).map((c, i) => <ChatCard key={`${c.type}-${c.id}-${i}`} card={c} />)}
        <div className="mt-0.5 text-[11px] text-muted">{time(turn.created)}{notice ? ` · ${copy.assistant.notice}` : ""}</div>
      </div>
    </div>
  );
}
