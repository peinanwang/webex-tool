# Templates: the words Webex Focus uses

Every message Webex Focus sends comes from a file in this folder: alerts, chat replies, summaries, the email, and even the instructions the AI follows. Change the words here and the product changes. No code needed.

The easiest way to edit is the **Templates** page in the Webex Focus web app (`http://localhost:8000/#/templates`). It shows a live preview and won't let you save a broken template. You can also edit the files in any text editor.

## The folders

| Folder | What's in it | Who sees it |
|---|---|---|
| `notify/` | The alert when a High priority message arrives (Webex Assistant post + desktop notification) | You, in Webex and on your desktop |
| `chat/` | The assistant's replies: rules, focus mode, search results, help, errors | You, in the Webex Assistant chat |
| `summary/` | The layout of summaries, and the summary email | You, in chat, the Summaries page, and email |
| `prompts/` | Instructions for the AI (persona, how to summarize, how to triage) | Only the AI |

## How a template works

```
🔔 **{{ sender }}** in **{{ space }}**
> {{ text }}
```

- Text outside `{{ }}` is printed as is. Change it freely.
- `{{ sender }}` is a **placeholder**: it's replaced by a real value. The list of placeholders is at the top of each file, between `{#` and `#}` (that part is a comment and is never shown).
- `{% if is_direct %}…{% else %}…{% endif %}` shows one wording or another. Keep each `{% if %}` paired with its `{% endif %}`, and each `{% for %}` with `{% endfor %}`.
- `**bold**`, `_italic_`, `- bullet` are Markdown, which Webex shows as formatting.

## Five common edits

1. **Change the alert wording**: `notify/assistant_post.md`, and `notify/desktop_title.txt` / `desktop_body.txt` for the pop-up.
2. **Change the help text**: `chat/help.md`.
3. **Reorder the summary sections**: in `summary/summary.md`, move the whole `{% if highlights %} … {% endif %}` block (or the action items / by space block).
4. **Change the assistant's tone**: `prompts/assistant.md`, e.g. "Answer in a cheerful, emoji-friendly tone."
5. **Make triage stricter or looser**: `prompts/triage.md`, e.g. "Only choose high for emergencies." Then ask a developer to run `python -m scripts.eval_triage` to see whether accuracy improved.

## If something breaks

- In the web page, **Save** refuses a template that doesn't work and tells you why (e.g. "`{{ sendr }}` isn't a known placeholder. Did you mean `{{ sender }}`?"). **Reset to default** brings back the original.
- After editing a file directly, run `pytest tests/test_templates.py`. It renders every template with the example values in `samples.yaml`.
- If you add a new placeholder to a template, the code must provide it. Ask a developer.
