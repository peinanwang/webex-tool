# Phase 10 — AI live triage

**Status: built 2026-10-26** (automated tests pass). Hands-on checks: [VERIFY.md](../VERIFY.md).

Rules handle the known cases (Bob, "urgent", @mentions). The AI handles the rest: a message no rule matched is classified by the LLM using A's **focus profile** and A's past corrections. The Triage tab (Phase 8) is how we measure whether it helps.

## Learn first
- **LLM classification**: we send one message plus instructions and get back `{"category": "high" | "regular", "reason": "…"}` through `llm.extract()` (the forced tool call from Phase 6). It can use a smaller, faster model than the chat, because it runs on every unmatched message.
- **Few-shot examples**: a handful of real past messages with the right answer ("A marked this High"). Including A's corrections in the prompt is the simplest way to make the AI learn A's taste, with no training involved.
- **Deterministic first**: rules always run before the AI, and the AI never overrides a rule. If the LLM is slow (over 3 s) or down, the message falls back to the defaults, so triage never blocks.
- **Evaluation**: A's feedback labels are a test set. `eval_triage.py` re-runs the classifier on them and prints accuracy, so a teammate can edit `templates/prompts/triage.md` and see whether it got better.

## Action items

- [ ] Config: `AI_TRIAGE=on|off`, `TRIAGE_MODEL` (defaults to `LLM_MODEL`; set it to a smaller OpenAI model to cut cost and latency), `TRIAGE_TIMEOUT=3`
- [ ] Focus profile: `kv.focus_profile` + tools `get_focus_profile` / `set_focus_profile`, plus a textarea on the Rules tab
- [ ] `shared/triage_ai.py`: `classify(message, profile, examples) -> (category, reason)`, prompt from `templates/prompts/triage.md`
  - [ ] Examples: the last 10 corrected messages (`should_be_high` / `should_be_regular`) plus a few confirmed ones
  - [ ] Timeout or error → `None` (the caller falls back to the default)
- [ ] Pipeline order: rules → @mention default (`high`) → AI (if on) → `regular`. AI results get `decided_by='ai'` and `reason='ai: <short reason>'`
- [ ] `topic` match type for rules ("anything about the Q3 launch"): checked by the same classifier call ("does this match any of these topics?")
- [ ] Triage tab: "AI" badge, "Needs review" = AI-decided and not yet reviewed, accuracy split into rules vs. AI
- [ ] `scripts/eval_triage.py`: runs `classify` over all feedback-labeled messages, then prints accuracy and the misses
- [ ] Cost guard: skip AI for A's own messages, the assistant space, and messages under 3 characters. Log the daily call count

## Checkpoint
- [ ] Profile: "outages and production issues are urgent; social chat isn't"
- [ ] With no matching rule, C sends "prod is down for EU customers" → `high`, `ai: reports a production outage`, and a notification
- [ ] C sends "lunch at 12?" → `regular`
- [ ] Mark one AI decision wrong → it shows up as an example in the next classification prompt (debug log)
- [ ] `python -m scripts.eval_triage` prints accuracy
- [ ] Set `AI_TRIAGE=off` or remove the key → messages fall back to `default` instantly, and nothing breaks
