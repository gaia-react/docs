---
name: voice-check
description: Audit drafted or existing docs content against GAIA brand voice rules. Use this skill BEFORE publishing any new docs page, after editing copy, or when the user asks for a voice review, "voice check", "AI tell scan", "before I commit this", or mentions em dashes / AI tells / brand voice. Also trigger when the user says "check this for voice", "is this on-brand", or "scan for voice issues". Operates on .md / .mdx files in src/content/docs/ by default; accepts a path argument for a specific file.
---

# voice-check

Audit docs content against `~/Development/gaia-react/studio/branding/VOICE.md` (canonical voice rules — read it before running this skill if you have not in this session).

## When to run

- Before committing new docs.
- After substantial edits to existing pages.
- On request: "voice check", "scan for AI tells", "is this on-brand".

## Scope

By default, scan all `.md` / `.mdx` files under `src/content/docs/`. If the user passes a path or filename, scan that file only.

## Procedure

Run greps in this order. Report findings grouped by category, with file:line refs. Do not auto-fix — surface findings and let the user decide.

### 1. Em dashes — category-A check

```sh
grep -rn '—' src/content/docs/
```

Any hit is a violation. No exceptions for prose, alt text, code comments, or frontmatter. UI glyphs that mean "absent" must be en dashes (`–`).

### 2. AI tells — category-A check

```sh
grep -rniE 'delve|tapestry|in the realm of|it'\''s worth noting|leveraging|seamless|robust|powerful|unleash|supercharge|effortless' src/content/docs/
```

Flag every hit. These are the top AI giveaways. "Powerful" and "robust" are empty hype adjectives — replace with the concrete capability or delete.

### 3. Buildup-then-add parallelism

Hard to grep cleanly. Read for `not just X, but Y, and Z` shape. Examples:
- "Not just fast, but reliable, and easy to use." → bad.
- "Specs first. Tests second. Code last." → good (parallel triplet, equal weight).

### 4. Borrowed-field jargon

```sh
grep -rniE '\bsubstrate\b|\bparadigm\b|\becosystem\b|\bfabric\b' src/content/docs/
```

Replacements: substrate → stack; paradigm → approach; ecosystem → name the actual thing; fabric → system / structure.

### 5. Junior-dev / "like a child" framing

```sh
grep -rniE 'junior dev|like a child|train(ing)? (it|the ai|claude) up|teaching (it|claude)' src/content/docs/
```

GAIA framing: AI is an expert that isn't human, not a junior in need of training-up. Reframe around human-vs-not-human distinctions.

### 6. Marketing register in reference docs

```sh
grep -rniE '\bgame[- ]chang(er|ing)\b|\brevolutioniz|\bnext[- ]gen\b|\bcutting[- ]edge\b|\bbest[- ]in[- ]class\b' src/content/docs/
```

Docs are reference register. Procedural and declarative, not pitch.

### 7. Founder-byline check

```sh
grep -rniE '^|[^t]By Steven Sacks' src/content/docs/
```

If a byline appears, it must read "Built by Steven Sacks" — builder voice, not publisher voice.

### 8. "We" / "our team" in docs

```sh
grep -rniE '\b(we|our team|our docs|we'\''ve|we'\''re)\b' src/content/docs/
```

Docs use declarative ("GAIA installs…") or second-person ("Run `pnpm install`…"). "We" creeps in. Flag for review — context decides whether each instance is OK.

### 9. Semicolons in body copy (advisory)

```sh
grep -rn ';' src/content/docs/ | grep -vE '\.ts|\.tsx|\bclassName\b|\.css|frontmatter'
```

Two short declaratives almost always read better. Flag advisory — let user decide.

### 10. "Agentic" / "agents" in headlines and section headers

```sh
grep -rnE '^#{1,3} .*\b(agentic|agents?|subagents?)\b' src/content/docs/
```

Buzzword posture: fluency-signal in body copy where accurate, NOT in H1/H2/H3 headers. Exception: `agentic-design` deep-dive surface (URL itself is the SEO landing).

## Report format

Output a single grouped report:

```
voice-check report — <N> files scanned

## category-A (must fix before publish)
- src/content/docs/install.mdx:24 — em dash in body
- src/content/docs/intro.md:7 — "powerful workflow"

## advisory (read and decide)
- src/content/docs/usage.mdx:12 — semicolon in body copy
- src/content/docs/intro.md:33 — "we" in declarative passage

clean: src/content/docs/index.mdx
```

Group by severity. Empty categories collapse. End with the list of clean files.

## What this skill does NOT do

- Does not auto-edit. Surface findings, let the user accept or reject each.
- Does not replace reading `VOICE.md`. The grep list is a tripwire, not the full ruleset. Subtle voice issues (over-promising, missed earned drama, wrong register) need human review.
- Does not check identity claims (audience, positioning) — that's the documentation-audit agent's job.
