{#
  Used instead of the summary layout when there's nothing to summarize.
  Placeholders:
    kind_label: Summary / While you were focused / End of day
    period: e.g. Mon Oct 26
    scope: held or all
    counts: counts.high, counts.regular, counts.self
    data_starts_at: if set, there's no data before this time
    truncated: always false here
#}
## {{ kind_label }} · {{ period }}
Nothing to summarize: {% if scope == "held" %}no messages were held for you{% else %}no messages{% endif %} in this period. 🎉
{% if data_starts_at %}

_No data before {{ data_starts_at }} (Webex Focus wasn't running yet)._
{% endif %}
