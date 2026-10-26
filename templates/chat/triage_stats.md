{#
  Reply to "how accurate was triage?".
  Placeholders:
    period: the time range
    total: messages from others in the period
    high: how many were High priority
    regular: how many were Regular
    needs_review: AI decisions you haven't reviewed yet
    overall: overall.reviewed, overall.correct, overall.accuracy (percent, or none if nothing reviewed)
    rules: same numbers for rule decisions
    ai: same numbers for AI decisions
    defaults: same numbers for default decisions
#}
**Triage, {{ period }}:** {{ total }} messages · 🔔 {{ high }} high · {{ regular }} regular

{% if overall.reviewed %}
You reviewed {{ overall.reviewed }}: **{{ overall.accuracy }}% correct**{% if ai.reviewed %} (AI: {{ ai.accuracy }}%){% endif %}{% if rules.reviewed %} (rules: {{ rules.accuracy }}%){% endif %}.
{% else %}
You haven't reviewed any yet. Tell me when one is wrong ("that was important"), or use the Triage page.
{% endif %}
{% if needs_review %}

{{ needs_review }} AI decision{{ "" if needs_review == 1 else "s" }} waiting for review.
{% endif %}
