"""Email — MOCKED for now: messages are written to the outbox folder instead of being sent.

Everything else calls send() (or send_summary()), so real delivery can be added later without
touching any other file.

Outbox (EMAIL_BACKEND=outbox, the only backend today) writes two files to OUTBOX_DIR:
- <name>.eml   a complete email (headers + plain text + HTML). Double-click it on macOS and it opens
               in Apple Mail looking exactly like the received email.
- <name>.html  just the body, for a quick look in a browser (the UI links to it).

For the coworker adding real delivery: add a function like `_send_smtp(to, subject, html, text)`
(smtplib + SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD settings) or `_send_graph(...)` (Microsoft
Graph sendMail), and pick it in send() based on config.EMAIL_BACKEND. Keep the return value a short
description of where it went; it's stored in summaries.delivered_to and shown in the UI.
"""

import html
import re
from email.message import EmailMessage
from email.utils import formatdate

import markdown as md

from shared import config, db
from shared.log import log
from shared.templates import render


def recipient() -> str:
    return config.EMAIL_TO or db.kv_get("my_email") or "me@localhost"


def _write_outbox(to: str, subject: str, html: str, text: str, basename: str) -> str:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"], msg["Date"] = subject, config.EMAIL_FROM, to, formatdate(localtime=True)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    config.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    eml = config.OUTBOX_DIR / f"{basename}.eml"
    eml.write_bytes(bytes(msg))
    (config.OUTBOX_DIR / f"{basename}.html").write_text(html, encoding="utf-8")
    shown = eml.relative_to(config.PROJECT_ROOT) if eml.is_relative_to(config.PROJECT_ROOT) else eml
    log(f"[email] wrote {shown} (to {to}) — outbox only, not actually sent")
    return str(shown)


def send(to: str, subject: str, html: str, text: str, basename: str) -> str:
    """Deliver one email. Returns where it went (for now: the outbox .eml path)."""
    if config.EMAIL_BACKEND != "outbox":
        log(f"[warn] EMAIL_BACKEND={config.EMAIL_BACKEND!r} isn't implemented yet; writing to the outbox")
    return _write_outbox(to, subject, html, text, basename)


def send_summary(summary: dict) -> str:
    """Email a saved summary row using templates/summary/email_*. Marks it delivered."""
    from shared.summary import summary_view
    view = summary_view(summary)
    values = {"kind_label": view["kind_label"], "period": view["period"], "summary_markdown": summary["markdown"],
              # Escape first: summaries quote other people's messages, which could contain HTML.
              "summary_html": md.markdown(html.escape(summary["markdown"], quote=False), extensions=["sane_lists"]),
              "ui_link": f"{config.UI_URL}/#/summaries?id={summary['id']}"}
    subject = render("summary/email_subject.txt", **values)
    slug = re.sub(r"[^a-z0-9]+", "-", f"{summary['period_start'][:10]} {summary['kind']} {summary['id']}".lower())
    where = send(recipient(), subject, render("summary/email_body.html", **values),
                 render("summary/email_body.txt", **values), slug.strip("-"))
    db.mark_summary_delivered(summary["id"], where)
    return where
