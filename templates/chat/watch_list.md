{#
  Reply to "/watch" (no word) or "what am I watching?".
  Placeholders:
    keywords: watched keywords; each has id, value, category, enabled
    topics: watched topics (judged by AI); each has id, value, category, enabled
#}
{% if not keywords and not topics %}
You're not watching any keywords or topics yet. Try `/watch outage` or `/topic the Q3 launch`.
{% else %}
**You're watching:**
{% for k in keywords %}
- 🔤 "**{{ k.value }}**" (keyword, rule #{{ k.id }}){% if k.category == "regular" %} → Regular{% endif %}{% if not k.enabled %} _(paused)_{% endif %}

{% endfor %}
{% for t in topics %}
- 🧠 **{{ t.value }}** (topic, judged by AI, rule #{{ t.id }}){% if t.category == "regular" %} → Regular{% endif %}{% if not t.enabled %} _(paused)_{% endif %}

{% endfor %}

Remove one with `/unwatch <word>`.
{% endif %}
