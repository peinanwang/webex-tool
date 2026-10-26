{#
  Reply to "/profile" (or "what's my focus profile?"), and after the profile is changed.
  Shows everything the assistant pays attention to besides who-sent-it rules.
  Placeholders:
    profile: the focus profile text (what's urgent for you, in your words; used by the AI)
    updated: true right after it was changed
    ai_triage_on: true if AI triage is running
    keywords: watched keywords; each has id, value, category, enabled
    topics: watched topics (judged by AI); each has id, value, category, enabled
    corrections: how many messages you've reviewed (the AI learns from these)
#}
{% if updated %}✅ Updated. {% endif %}**What I pay attention to**

**Your focus profile** (the AI uses this when no rule decides):
> {{ profile }}

**Watched keywords** (exact text, always): {% if keywords %}{% for k in keywords %}"{{ k.value }}"{% if not k.enabled %} _(paused)_{% endif %}{{ ", " if not loop.last else "" }}{% endfor %}{% else %}none yet. Add one with `/watch outage`{% endif %}

**Watched topics** (judged by AI): {% if topics %}{% for t in topics %}{{ t.value }}{% if not t.enabled %} _(paused)_{% endif %}{{ ", " if not loop.last else "" }}{% endfor %}{% else %}none yet. Add one with `/topic the Q3 launch`{% endif %}

**Learned from** {{ corrections }} correction{{ "" if corrections == 1 else "s" }} you made in Triage.
{% if not ai_triage_on %}

_AI triage is off right now, so only your rules and keywords decide._
{% endif %}

Change it: `/profile <your words>` · See how the AI reads it: `/profile explain`
