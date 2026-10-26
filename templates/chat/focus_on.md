{#
  Reply when focus mode is turned on.
  Placeholders:
    already: true if it was already on
    since: when it was turned on, e.g. 14:05
#}
{% if already %}
🎯 Focus was already on (since {{ since }}).
{% else %}
🎯 **Focus is ON.** I'll only interrupt you for high-priority messages. Everything else waits for your summary.
{% endif %}
