{#
  Reply to "show my summaries".
  Placeholders:
    summaries: list; each has id, kind_label, period, scope, delivered_at
#}
{% if not summaries %}
No summaries yet. Try "summarize what I missed today".
{% else %}
**Saved summaries:**
{% for s in summaries %}
- **#{{ s.id }}** {{ s.kind_label }} · {{ s.period }}{% if s.scope == "all" %} (everything){% endif %}{% if s.delivered_at %} · ✉️ emailed{% endif %}

{% endfor %}

Say "show summary 3" to read one.
{% endif %}
