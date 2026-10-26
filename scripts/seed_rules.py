"""Create a starting set of rules for the demo.

    python -m scripts.seed_rules --important b@example.com
    python -m scripts.seed_rules --important b@example.com --ignore-space "Random" --reset

Always adds:
- notify mention        (an @mention of A always pings, even inside a space with a digest rule)
- notify keyword=urgent (change with --keyword)
Plus one `notify sender=<email>` per --important, and `ignore space=<title>` per --ignore-space.
"""

import argparse

from shared.db import add_rule, delete_all_rules, init_db, list_rules
from shared.rules import describe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--important", action="append", default=[], metavar="EMAIL",
                        help="sender whose messages always ping A (repeatable)")
    parser.add_argument("--keyword", default="urgent", help="keyword that always pings A (default: urgent)")
    parser.add_argument("--ignore-space", action="append", default=[], metavar="TITLE",
                        help="space whose messages are ignored (repeatable)")
    parser.add_argument("--reset", action="store_true", help="delete all existing rules first")
    args = parser.parse_args()

    init_db()
    if args.reset:
        delete_all_rules()

    add_rule("notify", "mention")
    add_rule("notify", "keyword", args.keyword)
    for email in args.important:
        add_rule("notify", "sender", email)
    for title in args.ignore_space:
        add_rule("ignore", "space", title)

    print("Rules now:")
    for rule in list_rules():
        state = "" if rule["enabled"] else "  (disabled)"
        print(f"  {rule['action']:<7} {describe(rule)}{state}")


if __name__ == "__main__":
    main()
