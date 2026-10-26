import { useEffect, useRef, useState } from "react";
import { api, type TemplateInfo, type TemplateItem } from "../api";
import { Button, PageHeader } from "../components/Chips";
import { Markdown } from "../components/Markdown";
import { copy } from "../copy";

// For non-technical teammates: edit wording with a live preview. Saving is refused (with a plain
// explanation) if the template wouldn't work.
export function TemplatesTab() {
  const [items, setItems] = useState<TemplateItem[]>([]);
  const [name, setName] = useState<string>("notify/assistant_post.md");
  const [info, setInfo] = useState<TemplateInfo | null>(null);
  const [text, setText] = useState("");
  const [output, setOutput] = useState<{ ok: boolean; output?: string; error?: string } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const area = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { api.templates().then(setItems); }, []);
  useEffect(() => {
    api.template(name).then((i) => { setInfo(i); setText(i.text); setNotice(null); });
  }, [name]);
  useEffect(() => {
    if (!info) return;
    const t = setTimeout(() => api.previewTemplate(name, text).then(setOutput), 250);
    return () => clearTimeout(t);
  }, [text, info, name]);

  const dirty = info !== null && text !== info.text;
  const choose = (n: string) => { if (!dirty || confirm("Discard unsaved changes?")) setName(n); };
  const insert = (placeholder: string) => {
    const el = area.current; if (!el) return;
    const token = `{{ ${placeholder} }}`;
    const next = text.slice(0, el.selectionStart) + token + text.slice(el.selectionEnd);
    setText(next);
    requestAnimationFrame(() => { el.focus(); el.selectionStart = el.selectionEnd = el.selectionStart + token.length; });
  };

  const groups = Object.entries(copy.templates.groups);
  const isPrompt = name.startsWith("prompts/");
  const isText = name.endsWith(".txt");
  const isHtml = name.endsWith(".html");

  return (
    <div className="flex h-full flex-col">
      <PageHeader title={copy.templates.title} subtitle={copy.templates.subtitle} />
      <div className="flex min-h-0 flex-1">
        <nav className="w-64 shrink-0 overflow-y-auto border-r border-line bg-panel py-3">
          {groups.map(([group, label]) => (
            <div key={group} className="mb-3">
              <div className="px-4 pb-1 text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</div>
              {items.filter((i) => i.group === group).map((i) => (
                <button key={i.name} onClick={() => choose(i.name)} title={i.description}
                  className={`block w-full truncate px-4 py-1.5 text-left text-sm ${name === i.name ? "bg-accent-soft font-medium text-accent" : "hover:bg-gray-50"}`}>
                  {i.name.split("/")[1]}
                </button>
              ))}
            </div>
          ))}
        </nav>

        {info && (
          <div className="flex min-w-0 flex-1 flex-col gap-3 overflow-y-auto p-5 lg:flex-row">
            <div className="flex min-w-0 flex-1 flex-col">
              <div className="mb-1 flex items-center gap-2">
                <code className="text-sm font-semibold">{name}</code>
                {dirty && <span className="rounded bg-amber-100 px-1.5 text-xs text-amber-800">{copy.templates.unsaved}</span>}
              </div>
              <p className="mb-2 text-sm text-muted">{info.description}</p>
              {isPrompt && <p className="mb-2 rounded-lg bg-violet-50 px-3 py-2 text-sm text-violet-800">🤖 {copy.templates.promptNote}</p>}
              <textarea ref={area} value={text} onChange={(e) => setText(e.target.value)} spellCheck={false}
                className="min-h-80 flex-1 rounded-xl border border-line bg-white p-3 font-mono text-[13px] leading-relaxed outline-none focus:border-accent" />
              <div className="mt-3">
                <div className="mb-1 text-xs font-medium text-muted">{copy.templates.placeholders} · {copy.templates.insert}</div>
                <div className="flex flex-wrap gap-1.5">
                  {info.placeholders.map((p) => (
                    <button key={p.name} onClick={() => insert(p.name)} title={p.meaning}
                      className="rounded-md bg-gray-100 px-2 py-1 font-mono text-xs hover:bg-accent-soft hover:text-accent">{`{{ ${p.name} }}`}</button>
                  ))}
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <Button kind="primary" disabled={!dirty || output?.ok === false} onClick={async () => {
                  try { await api.saveTemplate(name, text); setInfo({ ...info, text, has_default: true }); setNotice(`✓ ${copy.templates.saved}`); }
                  catch (e) { setNotice(`⚠️ ${(e as Error).message}`); }
                }}>{copy.templates.save}</Button>
                <Button disabled={!info.has_default} onClick={async () => {
                  if (!confirm("Restore the original text?")) return;
                  const r = await api.resetTemplate(name); setInfo({ ...info, text: r.text }); setText(r.text); setNotice("Restored the original.");
                }}>{copy.templates.reset}</Button>
                {notice && <span className={`text-sm ${notice.startsWith("⚠️") ? "text-red-700" : "text-ok"}`}>{notice}</span>}
              </div>
            </div>
            <div className="flex min-w-0 flex-1 flex-col">
              <div className="mb-2 text-sm font-medium">{copy.templates.preview}</div>
              <div className="flex-1 rounded-xl border border-line bg-panel p-4">
                {!output ? null : !output.ok ? (
                  <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">⚠️ {output.error}</div>
                ) : isHtml ? (
                  <iframe title="preview" sandbox="" srcDoc={output.output} className="h-[520px] w-full rounded-lg border border-line" />
                ) : isText || isPrompt ? (
                  <pre className="whitespace-pre-wrap text-sm">{output.output}</pre>
                ) : (
                  <Markdown text={output.output ?? ""} />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
