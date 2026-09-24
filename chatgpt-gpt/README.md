# Setting up the Custom GPT

This lets a colleague without Python or a terminal run the *research* step
(browsing brand websites, scoring capabilities) inside ChatGPT and get back
an evidence CSV they hand to whoever runs the local `benchmark` tool. The GPT
does not run the Python tool itself — ChatGPT's Custom GPTs can't execute
this repo's code or write to this git history; it only produces the CSV
input. Ingesting, reporting, diffing and the competitive-positioning section
still happen locally with `python3 -m benchmark ...`.

## What's in this folder

- `instructions.md` — paste this into the GPT's "Instructions" field.
- `csv-output-format.md` — upload as a knowledge file (defines the exact CSV the GPT must output).

## Setup steps (chatgpt.com, requires a paid ChatGPT plan that supports Custom GPTs)

1. Go to chatgpt.com → **Explore GPTs** → **Create**.
2. Switch to the **Configure** tab (skip the conversational builder).
3. **Name**: `Indonesia Automotive Digital Benchmark`.
4. **Description**: `Research digital capabilities of automotive brand websites in Indonesia and output an evidence CSV.`
5. **Instructions**: paste the full contents of `instructions.md`.
6. **Conversation starters**, suggested:
   - `Research Toyota, Honda and Mitsubishi's finance calculators and configurators in Indonesia.`
   - `Compare test-drive booking across BYD, Honda and Mitsubishi Indonesia.`
7. **Knowledge**: upload these files:
   - `csv-output-format.md` (from this folder)
   - `SKILL.md` (from `../indonesia-automotive-digital-benchmark (1)/skills/indonesia-auto-benchmark/SKILL.md`)
   - `capability-taxonomy.md` (from `.../skills/indonesia-auto-benchmark/references/capability-taxonomy.md`)
   - `scoring-evidence.md` (from `.../skills/indonesia-auto-benchmark/references/scoring-evidence.md`)
8. **Capabilities**: turn ON **Web Browsing**. Turn OFF Code Interpreter and image generation (not needed, and Code Interpreter cannot reach this local git repo anyway).
9. Save as private ("Only me") or share within your org, per your usual policy for internal tools.

## Using it

1. Open the GPT, tell it which brands and which capabilities to research this session (keep it to a handful at a time — a full 14-category run across many brands is too large for one conversation).
2. Let it browse and build the evidence table.
3. At the end, it outputs one CSV code block. Copy it into a file, e.g. `oct_2026.csv`.
4. Hand that file to whoever runs the local tool:
   ```
   python3 -m benchmark ingest oct_2026.csv --date 2026-10-15
   python3 -m benchmark report --focus-brand Mitsubishi
   ```

## Limits to know about

- ChatGPT's web browsing tool renders pages differently from a real browser session — it may not be able to click through multi-step JS-heavy flows (configurators, calculators) the way an interactive session can. Treat anything it couldn't fully click through as `Partial`/`?`, per its instructions.
- Each ChatGPT conversation is stateless — it has no memory of past runs and can't see this repo's git history. Re-brief it each session.
- It cannot write files into this repository or run `git commit` — a human still runs the local `ingest`/`report` step.
