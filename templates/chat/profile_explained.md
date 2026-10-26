{#
  Reply to "/profile explain" (or "what do you think is important to me?"): the AI's own reading of
  your priorities, from your focus profile, rules, and corrections.
  Placeholders:
    urgent: list of things that interrupt you (High)
    can_wait: list of things that wait for your summary (Regular)
    learned: list of patterns learned from your corrections (may be empty)
    profile: your focus profile text
    ai_written: false if the AI couldn't be reached (only the profile is shown then)
#}
{% if ai_written %}
**Here's how I read your priorities:**

🔔 **I'll interrupt you for**
{% for u in urgent %}
- {{ u }}
{% endfor %}

💤 **This can wait for your summary**
{% for c in can_wait %}
- {{ c }}
{% endfor %}
{% if learned %}

📚 **Learned from your corrections**
{% for l in learned %}
- {{ l }}
{% endfor %}
{% endif %}

Not right? Change it with `/profile <your words>`, or correct messages in Triage.
{% else %}
🤖 I can't reach the AI right now, so here's your profile as written:
> {{ profile }}
{% endif %}
