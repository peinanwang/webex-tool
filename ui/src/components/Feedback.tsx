import { api, type Message } from "../api";
import { copy } from "../copy";

// ✓ / ↑ High / ↓ Regular buttons. Shows the verdict once given (click again to change it).
export function FeedbackButtons({ m, onDone }: { m: Pick<Message, "id" | "category" | "feedback">; onDone?: (updated: Message) => void }) {
  if (m.category === "self") return null;
  const send = async (label: "correct" | "should_be_high" | "should_be_regular") => onDone?.(await api.feedback(m.id, label));
  const verdict = m.feedback === "correct" ? `✓ ${copy.feedback.correct}`
    : m.feedback === "should_be_high" ? `↑ ${copy.feedback.toHigh}`
      : m.feedback === "should_be_regular" ? `↓ ${copy.feedback.toRegular}` : null;
  const btn = "rounded-md px-2 py-1 text-xs font-medium ring-1 ring-line hover:bg-gray-50";
  return (
    <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
      {verdict && <span className={`mr-1 text-xs font-medium ${m.feedback === "correct" ? "text-ok" : "text-high"}`}>{verdict}</span>}
      <button className={btn} title={copy.feedback.correct} onClick={() => send("correct")}>✓</button>
      {m.category === "regular"
        ? <button className={btn} onClick={() => send("should_be_high")}>↑ {copy.category.high}</button>
        : <button className={btn} onClick={() => send("should_be_regular")}>↓ {copy.category.regular}</button>}
    </div>
  );
}
