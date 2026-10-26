// Typed helpers for the Python app's JSON API (listener/api.py).

export type Category = "high" | "regular" | "self";
export type Feedback = "correct" | "should_be_high" | "should_be_regular" | null;

export interface Message {
  id: string; time: string; created: string; sender: string; sender_email: string; space: string;
  is_direct: boolean; text: string; category: Category; reason: string; decided_by: "rule" | "default" | "ai" | "self";
  mentioned_me: boolean; focus_on: boolean; notified: boolean; feedback: Feedback;
}
export interface Rule { id: number; category: "high" | "regular"; match_type: string; value: string; enabled: boolean; label: string }
export interface Card {
  type: "rule" | "message" | "summary"; id: number | string;
  [key: string]: unknown;
}
export interface ChatTurn { id: number; role: "user" | "assistant" | "notice"; text: string; source: "webex" | "ui" | "system"; cards: Card[]; created: string }
export interface FocusView { on: boolean; since: string | null; since_utc: string | null; duration?: string; counts: { high: number; regular: number; self: number } | null }
export interface Status {
  focus: FocusView; user: { name: string | null; email: string | null };
  listener: { mode: string; poll_interval: number; last_ok_at: string | null; last_error: string | null };
  assistant_space: boolean; llm: { configured: boolean; model: string }; ai_triage: boolean; notify_channels: string[];
}
export interface Accuracy { reviewed: number; correct: number; accuracy: number | null }
export interface TriageStats { total: number; high: number; regular: number; needs_review: number; overall: Accuracy; rules: Accuracy; ai: Accuracy; defaults: Accuracy; period: string }
export interface Summary { id: number; kind: string; kind_label: string; scope: string; period: string; markdown: string; created: string; delivered_at: string | null; delivered_to: string | null }
export interface TemplateItem { name: string; group: string; description: string }
export interface TemplateInfo { name: string; text: string; description: string; placeholders: { name: string; meaning: string }[]; sample: Record<string, unknown>; has_default: boolean }
export interface Contact { email: string; name: string | null; messages: number }
export interface Space { title: string; type: string; messages: number }
export interface Preview { supported: boolean; checked: number; changed: (Message & { new_category: string; new_reason: string })[] }

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* not JSON */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

const qs = (params: Record<string, string | boolean | number | undefined>) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== "" && v !== false) p.set(k, String(v)); });
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  status: () => request<Status>("GET", "/status"),
  setFocus: (on: boolean) => request<FocusView>("POST", "/focus", { on }),

  messages: (f: { start?: string; end?: string; category?: string; q?: string; needs_review?: boolean }) =>
    request<Message[]>("GET", `/messages${qs(f)}`),
  feedback: (id: string, label: Exclude<Feedback, null>) => request<Message>("POST", `/messages/${encodeURIComponent(id)}/feedback`, { label }),
  stats: (start = "", end = "") => request<TriageStats>("GET", `/triage/stats${qs({ start, end })}`),

  rules: () => request<Rule[]>("GET", "/rules"),
  addRule: (r: { category: string; match_type: string; value: string }) => request<Rule>("POST", "/rules", r),
  setRuleEnabled: (id: number, enabled: boolean) => request<Rule>("PATCH", `/rules/${id}`, { enabled }),
  deleteRule: (id: number) => request<unknown>("DELETE", `/rules/${id}`),
  testRule: (t: { text: string; sender_email: string; space: string; mentioned: boolean }) =>
    request<{ category: string; reason: string; decided_by: string; ai_would_decide: boolean; focus_on: boolean }>("POST", "/rules/test", t),
  previewRule: (r: { category: string; match_type: string; value: string }) => request<Preview>("POST", "/rules/preview", r),
  contacts: (q: string) => request<Contact[]>("GET", `/contacts${qs({ q })}`),
  spaces: (q: string) => request<Space[]>("GET", `/spaces${qs({ q })}`),
  profile: () => request<{ profile: string; ai_triage_on: boolean }>("GET", "/focus-profile"),
  setProfile: (text: string) => request<{ profile: string }>("PUT", "/focus-profile", { text }),

  chat: () => request<ChatTurn[]>("GET", "/chat"),
  send: (text: string) => request<ChatTurn>("POST", "/chat", { text }),

  summaries: (kind = "") => request<Summary[]>("GET", `/summaries${qs({ kind })}`),
  summary: (id: number) => request<Summary>("GET", `/summaries/${id}`),
  createSummary: (s: { start: string; end: string; scope: string }) => request<Summary>("POST", "/summaries", s),
  regenerate: (id: number) => request<Summary>("POST", `/summaries/${id}/regenerate`),
  email: (id: number) => request<{ outbox_path: string; to: string }>("POST", `/summaries/${id}/email`),

  templates: () => request<TemplateItem[]>("GET", "/templates"),
  template: (name: string) => request<TemplateInfo>("GET", `/templates/${name}`),
  previewTemplate: (name: string, text: string) => request<{ ok: boolean; output?: string; error?: string }>("POST", `/template-preview/${name}`, { text }),
  saveTemplate: (name: string, text: string) => request<{ ok: boolean; output: string }>("PUT", `/templates/${name}`, { text }),
  resetTemplate: (name: string) => request<{ ok: boolean; text: string }>("POST", `/template-reset/${name}`),
};

// The outbox .eml path ("data/outbox/x.eml") → the browser preview URL of its .html twin.
export const outboxPreviewUrl = (path: string) => `/api/outbox/${path.split("/").pop()!.replace(/\.eml$/, ".html")}`;

// Local date as YYYY-MM-DD (for <input type="date">).
export const localDate = (d = new Date()) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
