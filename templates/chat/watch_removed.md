{#
  Reply after "/unwatch <word>".
  Placeholders:
    rules: the removed keyword/topic rules; each has id, value, match_type
#}
🗑️ Stopped watching {% for r in rules %}"**{{ r.value }}**" (rule #{{ r.id }}){{ ", " if not loop.last else "" }}{% endfor %}.
