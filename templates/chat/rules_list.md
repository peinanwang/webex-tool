{#
  Reply to "show my rules" / "/rules".
  Placeholders:
    rules: list of rules; each has id, category, match_type, value, enabled
#}
{% if not rules %}
You don't have any rules yet. Try: "notify me when Bob writes".
{% else %}
**Your rules** (when several match, High wins):
{% for rule in rules %}
- **#{{ rule.id }}** {% include "chat/rule_phrase.md" %}{% if not rule.enabled %} _(paused)_{% endif %}

{% endfor %}
{% endif %}
