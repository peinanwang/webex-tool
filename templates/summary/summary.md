{#
  The layout of every summary (in chat, in the Summaries page, and in the email).
  The AI writes the content (headline, highlights, points, action items); this file decides how it looks.
  Placeholders:
    kind_label: Summary / While you were focused / End of day
    period: e.g. Mon Oct 26, 09:00–17:30
    scope: held (only messages you missed) or all (everything)
    counts: counts.high, counts.regular, counts.self (messages you sent)
    headline: one sentence, the most important thing
    highlights: list of key points
    action_items: list; each has what, who (who asked), due (may be empty)
    by_space: list; each has space and points (a list)
    truncated: true if there were too many messages to include them all
    data_starts_at: if set, there's no data before this time
    ai_written: false if the AI was unavailable (the content is then just the latest messages)
#}
## {{ kind_label }} · {{ period }}
{{ counts.high }} high priority · {{ counts.regular }} regular{% if scope == "all" %} · {{ counts.self }} sent by you{% endif %}


**{{ headline }}**
{% if highlights %}

### Highlights
{% for h in highlights %}
- {{ h }}
{% endfor %}
{% endif %}
{% if action_items %}

### Action items for you
{% for a in action_items %}
- {{ a.what }} (_{{ a.who }}_{% if a.due %}, due {{ a.due }}{% endif %})
{% endfor %}
{% endif %}
{% if by_space %}

### By space
{% for s in by_space %}
**{{ s.space }}**
{% for p in s.points %}
- {{ p }}
{% endfor %}

{% endfor %}
{% endif %}
{% if truncated %}
_Only the first 300 messages are included._
{% endif %}
{% if data_starts_at %}
_No data before {{ data_starts_at }} (Webex Focus wasn't running yet)._
{% endif %}
{% if not ai_written %}
_The AI wasn't available, so this lists the latest messages instead of a written summary._
{% endif %}
