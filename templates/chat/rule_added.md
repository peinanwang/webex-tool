{#
  Reply after a rule is added.
  Placeholders:
    rule: the new rule (rule.id, rule.category, rule.match_type, rule.value)
#}
✅ Added rule **#{{ rule.id }}**: {% include "chat/rule_phrase.md" %}. It applies from the next message.
