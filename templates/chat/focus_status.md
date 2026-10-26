{#
  Reply to "am I in focus mode?" / "/status".
  Placeholders:
    on: true if focus mode is on
    since: when it was turned on, e.g. 14:05 (only when on)
    duration: how long it has been on, e.g. 1h 12m (only when on)
    counts: messages this session: counts.high, counts.regular (only when on)
#}
{% if on %}
🎯 **Focus is ON** since {{ since }} ({{ duration }}). So far: **{{ counts.high }}** high priority, **{{ counts.regular }}** waiting for your summary.
{% else %}
💬 **Focus is OFF.** Nothing notifies you. Say "focus on" (or `/focus on`) to start.
{% endif %}
