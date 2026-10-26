{#
  Reply after you correct (or confirm) how a message was categorized.
  Placeholders:
    message: the message: message.sender, message.text, message.category, message.feedback
#}
👍 Got it: **{{ message.sender }}**'s "{{ message.text | truncate(60) }}" {% if message.feedback == "correct" %}was categorized correctly{% elif message.feedback == "should_be_high" %}should have been **High priority**{% else %}should have been **Regular**{% endif %}. I'll use this to triage better.
