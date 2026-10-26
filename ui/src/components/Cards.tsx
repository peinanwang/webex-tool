import { useState } from "react";
import { api, type Card } from "../api";
import { go } from "../router";
import { CategoryChip, Toggle } from "./Chips";
import { FeedbackButtons } from "./Feedback";

// Rich widgets under assistant replies (from tool results). In Webex, the same reply is plain text.
export function ChatCard({ card }: { card: Card }) {
  if (card.type === "rule") return <RuleCard card={card} />;
  if (card.type === "message") return <MessageCard card={card} />;
  if (card.type === "summary") return <SummaryCard card={card} />;
  return null;
}

const shell = "mt-2 rounded-xl border border-line bg-white px-3 py-2 text-sm shadow-sm";

function RuleCard({ card }: { card: Card }) {
  const [enabled, setEnabled] = useState(Boolean(card.enabled));
  const [gone, setGone] = useState(false);
  if (gone) return <div className={`${shell} text-muted line-through`}>Rule #{String(card.id)}</div>;
  return (
    <div className={`${shell} flex items-center gap-3`}>
      <span className="font-mono text-xs text-muted">#{String(card.id)}</span>
      <span className="flex-1">{String(card.label).replace(/^rule#\d+ /, "")}</span>
      <CategoryChip category={String(card.category)} />
      <Toggle on={enabled} label="Rule on/off" onChange={async (v) => { await api.setRuleEnabled(Number(card.id), v); setEnabled(v); }} />
      <button className="text-xs text-muted hover:text-red-600" onClick={async () => {
        if (confirm("Delete this rule?")) { await api.deleteRule(Number(card.id)); setGone(true); }
      }}>Delete</button>
    </div>
  );
}

function MessageCard({ card }: { card: Card }) {
  const [state, setState] = useState(card);
  return (
    <div className={shell}>
      <div className="flex items-center gap-2 text-xs text-muted">
        <span>{String(state.time)}</span>
        <span className="font-medium text-ink">{String(state.sender)}</span>
        {!state.is_direct && <span>in {String(state.space)}</span>}
        <span className="flex-1" />
        <CategoryChip category={String(state.category)} />
      </div>
      <div className="mt-1 line-clamp-3 whitespace-pre-wrap">{String(state.text)}</div>
      <div className="mt-1.5 flex items-center justify-between gap-2">
        <span className="text-xs text-muted">why: {String(state.reason)}</span>
        <FeedbackButtons m={{ id: String(state.id), category: state.category as "high", feedback: state.feedback as null }}
          onDone={(u) => setState({ ...state, feedback: u.feedback })} />
      </div>
    </div>
  );
}

function SummaryCard({ card }: { card: Card }) {
  const [emailed, setEmailed] = useState<string | null>(null);
  return (
    <div className={`${shell} flex items-center gap-3`}>
      <span>📋</span>
      <span className="flex-1"><b>{String(card.kind_label)}</b> · {String(card.period)}</span>
      <button className="text-xs font-medium text-accent hover:underline" onClick={() => go("summaries", { id: String(card.id) })}>Open</button>
      <button className="text-xs font-medium text-accent hover:underline" onClick={async () => setEmailed((await api.email(Number(card.id))).outbox_path)}>
        {emailed ? "✉️ Emailed" : "Email me"}
      </button>
    </div>
  );
}
