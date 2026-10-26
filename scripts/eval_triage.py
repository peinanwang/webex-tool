"""How well does AI triage match your corrections? Re-runs the AI on every message you've reviewed.

    python -m scripts.eval_triage

Use it after editing templates/prompts/triage.md or your focus profile. Each reviewed message is
classified again *without* itself as an example, and compared with your label.
"""

from shared import db, llm, triage_ai


def main() -> None:
    db.init_db()
    if not llm.is_configured():
        raise SystemExit("Set OPENAI_API_KEY in .env first.")
    labeled = db.labeled_examples(limit=500)
    if not labeled:
        raise SystemExit("No reviewed messages yet. Mark some in the Triage page (or in chat) first.")
    correct, misses = 0, []
    for row in labeled:
        others = [r for r in labeled if r["id"] != row["id"]][:10]
        decided = triage_ai.classify(row, examples=others)
        got = decided[0] if decided else "regular (AI unavailable)"
        if got == row["label"]:
            correct += 1
        else:
            misses.append((row, got))
    print(f"AI triage accuracy: {correct}/{len(labeled)} = {round(100 * correct / len(labeled))}%")
    for row, got in misses:
        print(f"  ✗ {row['person_email']} in {row['room_title']}: {row['text'][:70]!r} → AI {got}, you {row['label']}")


if __name__ == "__main__":
    main()
