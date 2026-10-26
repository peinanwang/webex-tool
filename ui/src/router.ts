import { useEffect, useState } from "react";

// Tiny hash router: #/triage?msg=abc → { page: "triage", params: { msg: "abc" } }.
// Hash URLs work with the Python app's static file server and with links in notifications.
export type Page = "assistant" | "triage" | "rules" | "summaries" | "templates";
const PAGES: Page[] = ["assistant", "triage", "rules", "summaries", "templates"];

function parse() {
  const [path, query = ""] = window.location.hash.replace(/^#\/?/, "").split("?");
  const page = (PAGES.includes(path as Page) ? path : "assistant") as Page;
  return { page, params: Object.fromEntries(new URLSearchParams(query)) as Record<string, string> };
}

export function useRoute() {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const onChange = () => setRoute(parse());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export const go = (page: Page, params: Record<string, string> = {}) => {
  const q = new URLSearchParams(params).toString();
  window.location.hash = `/${page}${q ? `?${q}` : ""}`;
};
