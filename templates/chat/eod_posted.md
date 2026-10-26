{#
  Posted automatically with the end-of-day summary (at 23:59).
  Placeholders:
    day: the day, e.g. Mon Oct 26
    summary: the summary text (from summary/summary.md)
    outbox_path: where the email was saved (email is mocked for now)
#}
🌙 **End-of-day summary for {{ day }}** (emailed to you; for now saved as `{{ outbox_path }}`)

{{ summary }}
