"""The cheap-model test (roadmap section 10.1: "20 real posts, the sentences side by side; I choose").

    uv run python -m agents.eye.modeltest                      20 posts the Eye has read, the default cheap model against Sonnet 5.5
    uv run python -m agents.eye.modeltest 20 default gpt-6-sol the number of posts, then the two models
    uv run python -m agents.eye.modeltest --reveal             which model was "A" and which "B"

It takes random posts from `articles` (run some real passes first) and writes nothing to them (only `ai_calls`). Which model wrote
which sentence is hidden until --reveal."""

from __future__ import annotations

import json
import random
import sys

from agents.eye import sentence
from shared import ai, config, runlog
from shared import db as dbmod

KEY = "eye-modeltest-key.json"


def main(argv: list[str], rng: random.Random | None = None) -> str:
    key_path = config.data_dir() / KEY
    if argv == ["--reveal"]:
        return key_path.read_text() if key_path.exists() else "No test has been run yet."
    count = int(argv[0]) if argv else 20
    models = argv[1:3] if len(argv) >= 3 else ["default", "sonnet-5.5"]
    if models[0] == models[1]:
        raise SystemExit("choose two different models")
    rng = rng or random.Random()
    conn = dbmod.connect()
    try:
        posts = conn.execute("SELECT id, site, title, full_text FROM articles WHERE text_missing = 0 AND length(full_text) > 300").fetchall()
        if len(posts) < count:
            raise SystemExit(f"Only {len(posts)} usable posts in `articles`; run some real passes first (python -m agents.eye).")
        out = ["CHEAP-MODEL TEST — which sentence is more accurate and more neutral? Models are hidden (A / B)."]
        key = {}
        with runlog.run("eye-modeltest") as run:
            for n, (article_id, site, title, text) in enumerate(rng.sample(posts, count), 1):
                order = [0, 1]
                rng.shuffle(order)
                out.append(f"\n=== {n}. [{site}] {title}\n    {text[:300].replace(chr(10), ' ')}…")
                for slot, idx in zip("AB", order):
                    model = None if models[idx] == "default" else models[idx]
                    try:
                        line = sentence.write(title, text, run=run, conn=conn, model=model, only_first=True)
                    except (ai.AIError, ValueError) as error:
                        line = f"(no answer: {error})"
                    out.append(f"  {slot}: {line}")
                    key[f"{n}. article {article_id} {slot}"] = models[idx]
        key_path.write_text(json.dumps(key, indent=1))
        out.append("\nWhich is better, A or B? Then: uv run python -m agents.eye.modeltest --reveal")
        return "\n".join(out)
    finally:
        conn.close()


if __name__ == "__main__":
    print(main(sys.argv[1:]))
