"""Create a starting set of rules for the demo.

    python -m scripts.seed_rules --important b@example.com
    python -m scripts.seed_rules --important b@example.com --regular-space "Random" --reset

Always adds:
- high mention          (an @mention of A is always high, even inside a space with a regular rule)
- high keyword=urgent   (change with --keyword)
Plus one `high sender=<email>` per --important, and `regular space=<title>` per --regular-space.
"""

import argparse

from shared.db import add_rule, delete_all_rules, init_db, list_rules
from shared.rules import describe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--important", action="append", default=[], metavar="EMAIL",
                        help="sender whose messages are always high priority (repeatable)")
    parser.add_argument("--keyword", default="urgent", help="keyword that makes a message high (default: urgent)")
    parser.add_argument("--regular-space", action="append", default=[], metavar="TITLE",
                        help="space whose messages are regular, even @mentions without a mention rule (repeatable)")
    parser.add_argument("--reset", action="store_true", help="delete all existing rules first")
    args = parser.parse_args()

    init_db()
    if args.reset:
        delete_all_rules()

    add_rule("high", "mention")
    add_rule("high", "keyword", args.keyword)
    for email in args.important:
        add_rule("high", "sender", email)
    for title in args.regular_space:
        add_rule("regular", "space", title)

    print("Rules now:")
    for rule in list_rules():
        state = "" if rule["enabled"] else "  (disabled)"
        print(f"  {rule['category']:<7} {describe(rule)}{state}")


if __name__ == "__main__":
    main()
