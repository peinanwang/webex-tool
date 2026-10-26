{#
  Reply when focus mode is turned off. The "what you missed" summary follows separately.
  Placeholders:
    already: true if it was already off
    session_period: the focus session that just ended, e.g. Mon Oct 26, 13:00–15:10
#}
{% if already %}
Focus was already off.
{% else %}
✅ **Focus is OFF** ({{ session_period }}). I'm writing up what you missed; it'll appear here in a moment.
{% endif %}
