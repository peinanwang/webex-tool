{#
  Instructions for "/profile explain": the AI sums up how it decides what's urgent for the user
  (users see the result, not these instructions).
  Placeholders:
    profile: the user's focus profile
    rules: the user's enabled rules; each has category (high/regular), match_type, value
    examples: messages the user corrected; each has sender, space, text, label (high/regular)
#}
You help a person who uses an assistant to filter their Webex messages while they focus. Explain, in short plain bullets, how you would decide what deserves to interrupt them (High) and what can wait for their summary (Regular).

Base it on:
- Their focus profile, in their words: "{{ profile }}"
{% if rules %}
- Their rules (these always win):
{% for r in rules %}
  - {{ r.category }} when {{ r.match_type }}{% if r.value %} = "{{ r.value }}"{% endif %}

{% endfor %}
{% endif %}
{% if examples %}
- How they corrected past decisions:
{% for e in examples %}
  - {{ e.sender }} in {{ e.space }}: "{{ e.text }}" → {{ e.label }}
{% endfor %}
{% endif %}

Write each bullet in under 12 words, in second person ("messages from your manager"). In "learned", only state patterns that the corrections really show. Leave it empty if there are no corrections.
