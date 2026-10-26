import type { Category, Message } from "../api";
import { copy } from "../copy";

export function CategoryChip({ category }: { category: Category | string }) {
  const style =
    category === "high" ? "bg-high-soft text-high ring-high/20"
      : category === "self" ? "bg-gray-100 text-gray-600 ring-gray-300/40"
        : "bg-accent-soft text-accent ring-accent/20";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${style}`}>
      {category === "high" && "🔔"}{copy.category[category as Category] ?? category}
    </span>
  );
}

export function DecidedByChip({ m }: { m: Pick<Message, "decided_by"> }) {
  const ai = m.decided_by === "ai";
  return (
    <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${ai ? "bg-violet-100 text-violet-700" : "bg-gray-100 text-gray-500"}`}>
      {copy.decidedBy[m.decided_by]}
    </span>
  );
}

export function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={() => onChange(!on)}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition ${on ? "bg-ok" : "bg-gray-300"}`}>
      <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition ${on ? "translate-x-4.5" : "translate-x-0.5"}`} />
    </button>
  );
}

export function Button({ children, onClick, kind = "default", disabled, type = "button", small }: {
  children: React.ReactNode; onClick?: () => void; kind?: "default" | "primary" | "danger" | "ghost";
  disabled?: boolean; type?: "button" | "submit"; small?: boolean;
}) {
  const styles = {
    default: "bg-white text-ink ring-1 ring-line hover:bg-gray-50",
    primary: "bg-accent text-white hover:bg-accent/90",
    danger: "bg-white text-red-600 ring-1 ring-red-200 hover:bg-red-50",
    ghost: "text-muted hover:bg-gray-100",
  }[kind];
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`inline-flex items-center gap-1.5 rounded-lg font-medium transition disabled:opacity-50 ${small ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-sm"} ${styles}`}>
      {children}
    </button>
  );
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line bg-panel px-6 py-4">
      <div>
        <h1 className="text-lg font-semibold">{title}</h1>
        {subtitle && <p className="mt-0.5 max-w-3xl text-sm text-muted">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">⚠️ {error}</div>;
}
