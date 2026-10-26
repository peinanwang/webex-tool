{#
  One rule in plain English. Used inside other templates (rules list, rule added, ...).
  Placeholders:
    rule: the rule: rule.id, rule.category (high/regular), rule.match_type, rule.value, rule.enabled
#}
{% if rule.match_type == "sender" %}messages from **{{ rule.value }}**{% elif rule.match_type == "space" %}anything in **{{ rule.value }}**{% elif rule.match_type == "keyword" %}messages containing "**{{ rule.value }}**"{% elif rule.match_type == "mention" %}when I'm **@mentioned**{% else %}anything about **{{ rule.value }}** _(judged by AI)_{% endif %} → {% if rule.category == "high" %}🔔 **High priority**{% else %}**Regular**{% endif %}
