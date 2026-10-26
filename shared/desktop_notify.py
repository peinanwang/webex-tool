"""Desktop notifications: the real alert for high-priority messages.

Posts made through the integration are sent as A, and Webex never notifies you about your own
messages, so our Python process pops up the alert itself.

DESKTOP_NOTIFIER picks the backend (`auto` chooses by operating system):
- terminal-notifier  macOS, preferred if installed (`brew install terminal-notifier`); clicking the
                     notification opens a link (the message in the Webex Focus UI).
- osascript          macOS, built in. Shows up under "Script Editor" in System Settings → Notifications.
- windows            Windows toast via the `win11toast` package.
- off                Log only (tests, CI).

Message text comes from other people, so it is always passed as a separate argument, never pasted
into a script (that would let a message containing quotes break or inject AppleScript).

    python -m shared.desktop_notify "Title" "Body"      # quick manual test
"""

import shutil
import subprocess
import sys

from shared import config
from shared.log import log

MAX_BODY = 200

# AppleScript that reads the title and body from its arguments (item 1 / item 2 of argv).
_APPLESCRIPT = [
    "-e", "on run argv",
    "-e", 'display notification (item 2 of argv) with title (item 1 of argv) sound name "default"',
    "-e", "end run",
]


def backend() -> str:
    choice = config.DESKTOP_NOTIFIER.strip().lower()
    if choice != "auto":
        return choice
    if sys.platform == "darwin":
        return "terminal-notifier" if shutil.which("terminal-notifier") else "osascript"
    if sys.platform == "win32":
        return "windows"
    return "off"


def show(title: str, body: str, open_url: str | None = None) -> bool:
    """Show a notification. Returns False (and logs) on failure; never raises."""
    body = body if len(body) <= MAX_BODY else body[: MAX_BODY - 1] + "…"
    kind = backend()
    try:
        if kind == "terminal-notifier":
            cmd = ["terminal-notifier", "-title", title, "-message", body, "-sound", "default"]
            if open_url:
                cmd += ["-open", open_url]
            done = subprocess.run(cmd, timeout=10, capture_output=True, text=True)
            if done.returncode == 0:
                return True
            # Usually "Notifications are not allowed for this application" (macOS permission).
            # Still show the alert through the built-in route, and say how to fix the preferred one.
            reason = (done.stderr or done.stdout).strip() or f"exit status {done.returncode}"
            log(f"[warn] terminal-notifier failed ({reason}). Allow it in System Settings → Notifications → "
                "terminal-notifier. Using osascript for now.")
            kind = "osascript"
        if kind == "osascript":
            subprocess.run(["osascript", *_APPLESCRIPT, title, body], check=True, timeout=10, capture_output=True)
        elif kind == "windows":
            from win11toast import notify  # installed only on Windows (see requirements.txt)
            notify(title, body, on_click=open_url) if open_url else notify(title, body)
        else:
            log(f"[desktop:off] {title}: {body}")
        return True
    except Exception as exc:
        log(f"[error] desktop notification ({kind}) failed: {exc}")
        return False


if __name__ == "__main__":
    args = sys.argv[1:] or ["Webex Focus", "Desktop notifications work."]
    print(f"Backend: {backend()}")
    print("Shown." if show(args[0], args[1] if len(args) > 1 else "", config.UI_URL) else "Failed (see above).")
