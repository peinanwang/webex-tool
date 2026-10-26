{#
  Reply to "/help" (and a good first message to read).
  Placeholders:
    llm_ready: true when the AI is set up (an OpenAI key is configured)
#}
**Here's what I can do.** Ask in plain words, for example:
- "notify me when Bob writes" · "anything in Random can wait" · "always notify me when I'm @mentioned"
- "what did Carol say today?" · "what did I miss?" · "summarize everything since Monday" · "email me that"
- "Carol's last message was actually important" · "what do you think is important to me?"

**Quick commands** (instant, work even without AI):
- `/mode` focus mode on or off? · `/mode on` · `/mode off`
- `/profile` what I pay attention to · `/profile <your words>` change it · `/profile explain` how the AI reads it
- `/watch` your keywords · `/watch <word>` always notify me about it · `/unwatch <word>` · `/topic <subject>` (judged by AI)
- `/rules` all rules · `/rule off 3` · `/rule on 3` · `/rule delete 3`
- `/summary` what I missed today · `/summary all` everything · `/summary focus` the last focus session
{% if not llm_ready %}

_The AI isn't set up yet, so only the quick commands work right now._
{% endif %}
