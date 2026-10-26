{#
  Reply after a rule is paused or resumed.
  Placeholders:
    rule: the rule (rule.id, rule.enabled, ...)
#}
{% if rule.enabled %}▶️ Rule **#{{ rule.id }}** is back on{% else %}⏸️ Rule **#{{ rule.id }}** is paused{% endif %}: {% include "chat/rule_phrase.md" %}.
