# Phase 11 — Template editor for non-technical teammates

Since Phase 4, every response has come from a file in `templates/`. This phase lets a teammate edit those files from the UI, with a live preview and a safety check, so nobody needs VS Code or git to improve the wording.

## Learn first
- **Sandboxed rendering**: templates are rendered in Jinja's `SandboxedEnvironment`, so a template can format text but can't reach into Python. That makes it safe to let people edit them from a web page.
- **Validate before save**: we render the edited text with the sample data from `templates/samples.yaml`. If that fails (misspelled placeholder, unclosed `{% if %}`), we show the error in plain words and don't write the file.

## Action items

### Backend
- [ ] `GET /api/templates`: list grouped by folder, with each file's description from its header comment
- [ ] `GET /api/templates/{name}`: the text, the available placeholders, and the sample values
- [ ] `POST /api/templates/{name}/preview {text}`: rendered output, or a friendly error with a line number
- [ ] `PUT /api/templates/{name} {text}`: validate, then save. Only paths inside `templates/` (reject `..`)
- [ ] `POST /api/templates/{name}/reset`: restore the shipped version (copies kept in `templates/_defaults/`, or `git show HEAD:…`)
- [ ] Error messages for editors written in plain language ("`{{ sendr }}` isn't a known placeholder. Did you mean `{{ sender }}`?")

### Frontend
- [ ] **Templates tab**: groups (Notifications, Chat replies, Summaries, AI prompts), an editor with placeholder chips that insert `{{ … }}`, live side-by-side preview (Markdown rendered), Save / Reset, and an "unsaved changes" warning
- [ ] For `prompts/*`: a note explaining that these instruct the AI and aren't shown to users, with a link to `eval_triage` for the triage prompt

### Docs
- [ ] `templates/README.md`: update with screenshots of the tab and a "five most common edits" section

## Checkpoint
- [ ] A teammate changes the alert wording in the UI, previews it, and saves → the next high message uses it
- [ ] Type `{{ sendr }}` → the preview shows the friendly error, and Save is refused
- [ ] Reset to default → the original text is back
- [ ] Edit `prompts/assistant.md` to change the tone → the next chat answer reflects it
- [ ] `pytest` (template render test) still passes after the edits
