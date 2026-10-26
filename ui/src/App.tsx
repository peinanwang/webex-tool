import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { useRoute } from "./router";
import { AssistantTab } from "./tabs/Assistant";
import { RulesTab } from "./tabs/Rules";
import { SummariesTab } from "./tabs/Summaries";
import { TemplatesTab } from "./tabs/Templates";
import { TriageTab } from "./tabs/Triage";

export default function App() {
  const { page, params } = useRoute();
  return (
    <div className="flex h-full">
      <Sidebar current={page} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="min-h-0 flex-1 overflow-hidden">
          {page === "assistant" && <AssistantTab />}
          {page === "triage" && <TriageTab focusId={params.msg} />}
          {page === "rules" && <RulesTab />}
          {page === "summaries" && <SummariesTab selectedId={params.id ? Number(params.id) : undefined} />}
          {page === "templates" && <TemplatesTab />}
        </main>
      </div>
    </div>
  );
}
