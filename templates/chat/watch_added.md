{#
  Reply after "/watch <word>" or "/topic <phrase>".
  Placeholders:
    rule: the keyword/topic rule (rule.id, rule.match_type, rule.value)
    already: true if it was already being watched
#}
{% if already %}👀 Already watching {% else %}👀 Now watching {% endif %}{% if rule.match_type == "topic" %}the topic **{{ rule.value }}** (judged by AI){% else %}the keyword "**{{ rule.value }}**"{% endif %}: those messages are 🔔 High priority (rule #{{ rule.id }}).
