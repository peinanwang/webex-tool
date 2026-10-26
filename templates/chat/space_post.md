{#
  How every message from the assistant looks in the Webex Assistant space.
  All posts are sent as you, so Webex shows you as the sender of both your messages and the
  assistant's. This header is what tells them apart: keep something distinctive on the first line.
  (The web page doesn't use this; it shows the assistant's messages in their own bubbles.)
  Placeholders:
    body: the message itself (a reply, an alert, or a summary)
    kind: reply (an answer to you) or alert (an automatic post: High priority message, summary)
    assistant_name: the assistant's name, from ASSISTANT_NAME in .env (default: Webex Assistant)
#}
{% if kind == "alert" %}🔔{% else %}🤖{% endif %} **{{ assistant_name }}**
{{ body }}
