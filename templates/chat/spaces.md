{#
  Reply to a space lookup.
  Placeholders:
    query: what was searched
    spaces: list; each has title, type (direct/group), messages
#}
{% if not spaces %}
I haven't seen any space matching "{{ query }}" yet (I only know spaces that have sent you messages).
{% else %}
Spaces matching "{{ query }}":
{% for s in spaces %}
- **{{ s.title }}** ({{ "1:1 chat" if s.type == "direct" else "space" }}, {{ s.messages }} messages)
{% endfor %}
{% endif %}
