# External reviews — drop-zone

Adversarial reviews from external tools land here. Each tool writes to its **own
subfolder** so outputs never collide:

- `reviews/codex/` — Codex (GPT‑5.5, reasoning effort `xhigh`)
- `reviews/gemini-3-pro/` — Antigravity · Gemini 3.1 Pro
- `reviews/gemini-3-flash/` — Antigravity · Gemini 3.5 Flash

Each subfolder should contain four files:
`adversarial-review.md`, `bugs.md`, `security.md`, `features.md`.

## How to act on them
After running the copy‑paste prompts (kept in the chat history and referenced from
`.handoff/CONTINUE.md`), tell Claude Code:

> **"read reviews/ and fix the confirmed issues + build the best features"**

Claude will **adversarially verify each finding before touching code** (external
reviews can hallucinate or re‑report already‑fixed issues — the repo has had 3
Codex cycles + an auth‑hardening pass; see `analysis/`), then implement fixes and
features with tests, and report what it confirmed vs. rejected.
