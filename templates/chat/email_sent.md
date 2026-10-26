{#
  Reply after a summary is "emailed". Email is mocked for now: it's saved to the outbox folder.
  Placeholders:
    summary_id: the summary's number
    to: the email address
    outbox_path: where the email file was saved
#}
✉️ Summary #{{ summary_id }} emailed to {{ to }}. (For now it's saved as `{{ outbox_path }}`; double-click it to open it in Mail.)
