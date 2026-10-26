import { copy } from "../copy";
import { go, type Page } from "../router";

const ITEMS: { page: Page; icon: string }[] = [
  { page: "assistant", icon: "💬" },
  { page: "triage", icon: "🗂️" },
  { page: "rules", icon: "⚙️" },
  { page: "summaries", icon: "📄" },
  { page: "templates", icon: "✏️" },
];

export function Sidebar({ current }: { current: Page }) {
  return (
    <nav className="flex w-56 shrink-0 flex-col bg-side px-3 py-4 text-gray-300">
      <div className="mb-6 flex items-center gap-2 px-2 text-white">
        <span className="text-xl">🎯</span>
        <span className="font-semibold tracking-tight">{copy.appName}</span>
      </div>
      {ITEMS.map(({ page, icon }) => (
        <button key={page} onClick={() => go(page)}
          className={`mb-1 flex flex-col items-start rounded-lg px-3 py-2 text-left transition ${current === page ? "bg-side-hover text-white" : "hover:bg-side-hover/60"}`}>
          <span className="text-sm font-medium">{icon}&nbsp;&nbsp;{copy.nav[page]}</span>
          <span className="text-[11px] text-gray-500">{copy.navHint[page]}</span>
        </button>
      ))}
    </nav>
  );
}
