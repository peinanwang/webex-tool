{#
  Reply to a message search ("what did Carol say today?").
  Placeholders:
    period: the time range searched, e.g. Mon Oct 26
    count: how many were found
    messages: list; each has time, sender, space, is_direct, text, category (high/regular/self), reason
#}
{% if count == 0 %}
No messages found ({{ period }}).
{% else %}
**{{ count }} message{{ "" if count == 1 else "s" }}** ({{ period }}):
{% for m in messages %}
- {{ m.time }} · **{{ m.sender }}**{% if not m.is_direct %} in {{ m.space }}{% endif %}: {{ m.text | truncate(160) }} ({{ "🔔 High" if m.category == "high" else ("sent by you" if m.category == "self" else "Regular") }})
{% endfor %}
{% endif %}
