{#
  Post in your Webex Assistant space when a High priority message arrives (focus mode on).
  Placeholders:
    sender: display name of the person who wrote
    sender_email: their email
    space: space title (for 1:1 chats, the other person's name)
    is_direct: true for a 1:1 chat, false for a group space
    mentioned_me: true if the message @mentions you
    text: the message text
    reason: why it's High priority (which rule, or the AI's reason)
    time: when it was sent, e.g. 14:05
    link: opens this message in the Webex Focus web page
#}
🔔 **{{ sender }}** {% if is_direct %}messaged you{% else %}{% if mentioned_me %}mentioned you {% endif %}in **{{ space }}**{% endif %} · {{ time }}

> {{ text | replace("\n", "\n> ") }}

_Why: {{ reason }}_
