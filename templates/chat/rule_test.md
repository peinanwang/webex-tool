{#
  Reply to "would I get pinged if ...?" (a dry run with the current rules).
  Placeholders:
    category: high or regular
    reason: which rule decided, or "default" / "default:mention"
    decided_by: rule or default
    ai_would_decide: true if no rule matches and AI triage would decide for real
    focus_on: true if focus mode is on right now
    text: the sample message
    sender: the sample sender email
    space: the sample space
#}
{% if category == "high" %}🔔 That would be **High priority**{% else %}That would be **Regular** (held for your summary){% endif %}, because {% if decided_by == "rule" %}{{ reason }} matches{% elif reason == "default:mention" %}you're @mentioned and no rule says otherwise{% else %}no rule matches{% endif %}.
{% if ai_would_decide %}

_No rule matches, so for a real message the AI would decide, based on your focus profile._
{% endif %}
{% if category == "high" and not focus_on %}

_Focus is off right now, so it wouldn't ping you until you turn focus on._
{% endif %}
