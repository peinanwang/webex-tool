import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

// Renders Markdown from templates and the AI. react-markdown never renders raw HTML, which matters
// because messages quote what other people wrote.
export function Markdown({ text, className = "" }: { text: string; className?: string }) {
  return (
    <div className={`md ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{ a: ({ href, children }) => <a href={href} target={href?.startsWith("#") ? undefined : "_blank"} rel="noreferrer">{children}</a> }}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
