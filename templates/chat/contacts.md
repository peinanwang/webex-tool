{#
  Reply to a people lookup.
  Placeholders:
    query: what was searched
    people: list; each has name, email, messages (how many they've sent you)
#}
{% if not people %}
I couldn't find anyone matching "{{ query }}". Try their email address.
{% else %}
People matching "{{ query }}":
{% for p in people %}
- **{{ p.name or p.email }}** ({{ p.email }})
{% endfor %}
{% endif %}
