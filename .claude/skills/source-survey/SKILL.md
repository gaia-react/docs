---
name: source-survey
description: Walk the GAIA source repo and report what is new, changed, removed, or excluded relative to the last snapshot in .claude/audit/source-state.json. Run BEFORE writing or updating any docs page, when the user asks "what's new in gaia", "what changed since the last docs pass", "source survey", "what do we still need to document", or whenever the docs site may have drifted from gaia/. Outputs a structured drift report grouped by NEW / CHANGED / REMOVED / EXCLUDED / AUDIENCE-CHANGED / VERIFIED, with each item classified by audience (adopter / contributor / mixed). Idempotent. Runs survey.py; writes the snapshot but never commits it.
---

# source-survey

Idempotent drift detector for the GAIA documentation project. Walks the GAIA source surface at `~/Development/gaia-react/gaia/`, classifies every item as adopter or contributor, computes drift against the snapshot at `~/Development/gaia-react/docs/.claude/audit/source-state.json`, and prints a grouped report.

This skill does not write docs. It reports drift so the user can decide what to document.

## When to run

- Before starting a new docs page or section.
- After a `gaia/` change lands that might affect public surface.
- When the user asks "what's new", "what changed", "what still needs docs", "source survey", "drift check".
- Periodically (e.g., before each release of the docs site).

## Inputs

- `~/Development/gaia-react/gaia/`: the GAIA source tree. Read-only.
- `~/Development/gaia-react/gaia/.gaia/release-exclude`: path-level adopter/contributor split.
- `~/Development/gaia-react/docs/.claude/audit/source-state.json`: last snapshot. May be empty `{}` on first run.
- `~/Development/gaia-react/docs/.claude/audit/do-not-document.yml`: obscurity-by-design exclusions.
- `~/Development/gaia-react/docs/src/content/docs/`: the docs tree. Walked to compute "documented but not in source" cases.

## Outputs

- A structured markdown report printed to the conversation.
- The updated snapshot written directly to `~/Development/gaia-react/docs/.claude/audit/source-state.json`. Never print the JSON to chat.

## Run it

`survey.py` in this folder implements Steps 1 to 8. Run it from the docs repo root; never hand-walk the tree or hand-edit the snapshot.

```sh
python3 -I .claude/skills/source-survey/survey.py --ref <gaia ref> --write
```

- `--ref`: the gaia commit, tag, or branch to survey (default `HEAD` of the gaia checkout). Use the release tag for a release snapshot (`--ref v2.1.0`).
- `--write`: replace the snapshot after printing the report. Leave it off for a dry look; the report is the same either way, because drift is computed against the snapshot on disk before anything is written.
- `--gaia <path>`: the gaia checkout (default: `gaia/` next to this docs repo).
- `--verbose`: list every VERIFIED item.

The script reads the committed tree at `--ref` through `git archive`, so uncommitted or untracked files in the gaia checkout never reach a snapshot, and `gaia_commit` is the full SHA of that ref. Relay the report to the user with your read on it: which hits need a docs change, which are expected noise (Step 6 lists the known kinds).

The steps below are the contract the script implements. When you change one, change the script in the same commit, rerun it at the snapshot's own `gaia_commit`, and confirm VERIFIED covers every item before you trust the change.

## Procedure

### Step 1: Load the exclusion mechanisms

Read `~/Development/gaia-react/gaia/.gaia/release-exclude`. Strip comments (`#`) and blank lines. The remaining lines are tar-style exclude patterns that must be converted to a regex set. Conversion rules:

- Leading `/` is implicit (patterns are relative to gaia root).
- A bare path like `.claude/commands/gaia-release.md` matches that exact path.
- A path ending with no glob like `.gaia/cli/src` matches the directory and everything under it.
- `*` matches one path segment (no `/`); `**` is not used in this file but treat it as multi-segment if encountered.

Cache the resulting pattern set as `RELEASE_EXCLUDE`.

Read `~/Development/gaia-react/docs/.claude/audit/do-not-document.yml`. Cache the `exclusions` list as `DO_NOT_DOCUMENT`. Each entry has `path` (glob) or `name` (substring or glob), plus `reason`.

### Step 2: Walk the surface layers

Walk all five layers below. For each item, capture a record:

```
{
  "kind":         "command | skill | reference | cli-subcommand | hook | githook | rule | agent | workflow | wiki-page",
  "path":         "<path relative to gaia/>",
  "name":         "<canonical name; see per-layer rules>",
  "description":  "<one-line description if applicable, else null>",
  "audience":     "adopter | contributor | mixed",
  "marker_blocks": [[startLine, endLine], ...],  // only when audience == mixed
  "content_hash": "<sha256 of frontmatter + first 40 body lines (or full file for short files)>"
}
```

Audience determination per item:

1. If the item's path matches `RELEASE_EXCLUDE`, audience is `contributor`. Done.
2. Else if the file (when text) has a whole-line marker, `<!-- gaia:maintainer-only:start -->` in markdown or `# gaia:maintainer-only:start` in shell and YAML, audience is `mixed`. Capture each marker block's start and end line numbers. A marker quoted inside backticks in prose is not a marker.
3. Else audience is `adopter`.

Also tag each item with an `excluded_from_docs: true | false` flag. Set true if the item matches any entry in `DO_NOT_DOCUMENT`.

#### Layer 1: top-level slash commands

Path: `gaia/.claude/commands/*.md`. For each file:

- `kind = "command"`
- `name` = frontmatter `name`, falling back to filename without `.md`
- `description` = frontmatter `description`
- Path-level audience via `RELEASE_EXCLUDE` (e.g., `gaia-release.md` and `distribution-vet.md` are excluded → contributor). The `name` carries the leading slash (`/gaia-spec`).

#### Layer 2: skills

Paths: `gaia/.claude/skills/*/SKILL.md` (root harness) and `gaia/frontend/.claude/skills/*/SKILL.md` (frontend harness). Skip `react-doctor`: it installs per machine and is gitignored. `gaia/.claude/skills/gaia/` has no `SKILL.md`; its `references/` folder is Layer 3.

- `kind = "skill"`
- `name` = frontmatter `name`
- `path` = path relative to `gaia/`, so frontend skills start `frontend/.claude/skills/`
- `description` = frontmatter `description` (which holds trigger phrases)

#### Layer 3: workflow references

Path: `gaia/.claude/skills/gaia/references/**/*.md`. These are the workflows behind the `/gaia-*` slash commands (Layer 1). They are not invoked by name, so docs cite them through their command, never as `/gaia <sub>` (the 1.x form).

For each:

- `kind = "reference"`
- `name` = path under `references/` without `.md` (`spec`, `cleanse/apply`, `setup/per-machine`)
- `description` = first line of the file body that isn't frontmatter or a heading-only line (best-effort; falls back to the H1)
- Audience per Step 2; several are `mixed`.

#### Layer 4: bundled CLI

The binary `gaia/.gaia/cli/gaia` ships. The source `gaia/.gaia/cli/src/` is contributor-only.

The subcommand surface is parsed from the routers:

- Top-level: `gaia/.gaia/cli/src/index.ts`: read the `SUBCOMMAND_HANDLERS` keys. Never copy a list from this file; re-derive it every run (at gaia 2.1.0 it held `codify-ledger`, `codify-tally`, `fitness`, `init`, `labels`, `packages`, `ping`, `react-perf`, `residue-*`, `sandbox`, `scaffold`, `setup`, `update`, `update-deps`, `wiki`).
- Per-namespace: read the module each top-level handler is imported from (usually `<ns>/index.ts`; `codify-ledger` is `codify/ledger.ts`) for its own `SUBCOMMAND_HANDLERS` keys, or failing that its `sub === '<name>'` branches. Capture only routed subcommands, not library helpers that sit in the same folder. A handler with no subcommands is one record, `gaia <ns>`.
- The release namespace lives only in the contributor-only `.gaia/cli/gaia-maintainer` binary. Do not capture it: its subcommand list is obscured per `DO_NOT_DOCUMENT`.

For each subcommand, capture:

- `kind = "cli-subcommand"`
- `name` = `gaia <ns> <sub>` or `gaia <ns> <group> <sub>` for nested groups (e.g., `gaia wiki state-init`)
- `path` = the subcommand's own `<sub>.ts` file next to the routing module if present; else the routing module
- `description` = the rest of that namespace's line in the top-level `HELP_TEXT` block of `src/index.ts`, or null when the line has nothing after the name
- `audience` per the rules above (note: source files are all under `.gaia/cli/src/` which is `RELEASE_EXCLUDE`d, but the *behavior* ships in the binary; treat the audience field as the **invocation audience**: i.e., who can run the command: not the source-shipping audience)

Mark any name containing `_internal-` as `excluded_from_docs: true` per `DO_NOT_DOCUMENT`.

#### Layer 5: supporting machinery

Walk these globs and capture each file:

- Hooks: `gaia/.claude/hooks/*.sh` → `kind = "hook"`, `name` = filename. `description` = first non-shebang comment line if present, else null.
- Git hooks: `gaia/.githooks/*` → `kind = "githook"`, `name` = filename (`pre-push` is contributor-only).
- Rules: `gaia/.claude/rules/*.md`, `gaia/.claude/rules/maintainers/*.md` (contributor-only) and `gaia/frontend/.claude/rules/*.md` → `kind = "rule"`, `name` = basename without `.md` for root rules, `maintainers/<basename>` for the maintainer folder, `frontend:<basename>` for frontend rules (`frontend:i18n`), `description` = frontmatter `description` or H1.
- Agents: `gaia/.claude/agents/*.md` → `kind = "agent"`, `name` = frontmatter `name`, `description` = frontmatter `description`. Plus the frontend auditor's extension files, `gaia/frontend/.claude/agents/code-audit-frontend/*.md`, with `name` = `code-audit-frontend/<basename>`.
- CI workflows: `gaia/.github/workflows/*.yml` → `kind = "workflow"`, `name` = filename, `description` = top-level `name:` field in the yaml.
- Wiki pages: `gaia/wiki/**/*.md` → `kind = "wiki-page"`, `name` = `path` (the full `wiki/...` form, e.g. `wiki/concepts/Forensics.md`; the snapshot keys on it, so any other form turns every page into a false NEW + REMOVED pair), `description` = frontmatter `description` if present, else H1.

### Step 3: Compute content hash deterministically

Per record, the `content_hash` must be reproducible:

```sh
# For .md files:
{ awk '/^---$/{c++; if(c==2){exit}; next} c==1{print}' "$FILE";  \
  awk '/^---$/{c++; if(c==2){next}} c>=2' "$FILE" | head -n 40; } \
  | shasum -a 256 | awk '{print $1}'
```

For files with no frontmatter (hooks, workflows, ts), hash the full file if under 200 lines; otherwise the first 40 non-blank lines after any leading comment block. State the chosen rule once at the top of the report so the user knows.

For `cli-subcommand` records that map to a directory rather than a file, hash the namespace `index.ts` instead.

### Step 4: Walk the docs side

Find every `.md` and `.mdx` under `~/Development/gaia-react/docs/src/content/docs/`. For each file, extract referenced GAIA things via best-effort regex:

- Slash commands: `/[a-z][a-z0-9-]*` and `/gaia [a-z-]+( [a-z-]+)?`
- Skill names: backtick-wrapped tokens that match a known top-level skill name.
- Source paths: backtick-wrapped tokens beginning with `.claude/`, `.gaia/`, `frontend/`, `wiki/`, `.githooks/` or `.github/`. Only a path under a surface folder (commands, skills, hooks, rules, agents, workflows, githooks, wiki) can be an orphan; any other missing path is a file the adopter's project creates at run time (`.gaia/local/*`, `settings.local.json`). The per-machine `react-doctor` skill is never in the tree, so it is skipped.
- CLI invocations: `gaia <subcommand>` patterns inside fenced code blocks or backticks.

Build a set `DOCUMENTED` of `(kind, name)` tuples that the docs reference. Best-effort is fine; do not block on parser perfection.

### Step 5: Load the previous snapshot

Read `~/Development/gaia-react/docs/.claude/audit/source-state.json`. If it does not exist or is empty / `{}`, treat the previous state as no items: every current item will report as NEW.

The snapshot schema:

```json
{
  "version": 1,
  "captured_at": "<ISO date>",
  "gaia_commit": "<sha or null>",
  "items": [
    { "kind": "...", "path": "...", "name": "...", "description": "...",
      "audience": "...", "content_hash": "...", "excluded_from_docs": false }
    , ...
  ]
}
```

### Step 6: Compute drift

Match current items to previous items by the composite key `(kind, name, path)`. For each match, classify:

- **VERIFIED**: both records exist; `content_hash`, `description`, and `audience` all match.
- **CHANGED**: both records exist; `content_hash` or `description` differs; `audience` unchanged.
- **AUDIENCE-CHANGED**: both records exist; `audience` differs (e.g., adopter → contributor or contributor → adopter or anything → mixed). High-priority signal.
- **NEW**: current record exists, no matching previous record, AND not in `DO_NOT_DOCUMENT`.
- **REMOVED**: previous record exists, no matching current record. (If it is in `DO_NOT_DOCUMENT`, still report as REMOVED: removing an excluded item is normal but worth surfacing.)
- **EXCLUDED**: current record exists AND matches `DO_NOT_DOCUMENT`. Always categorize EXCLUDED items here regardless of whether they are NEW / CHANGED / VERIFIED. The point of this category is "we know we are deliberately ignoring this".

Cross-reference docs:

- For each item in `DOCUMENTED` that has no matching current source record, mark it as a **DOC-ORPHAN** (documented but no longer in source).
- For each adopter-audience source item NOT in `DOCUMENTED` and NOT in `DO_NOT_DOCUMENT`, flag as **UNDOCUMENTED** (this overlaps with NEW for first-run snapshots: keep them separate categories so the meaning is explicit). Wiki pages, workflow references and the `code-audit-frontend/*` extension files are reached through their command, the wiki or the parent auditor, so they are never flagged. CLI subcommands collapse to one count line: Claude runs them, and pages name one only where the reader needs it.

Known noise, not a docs bug: `getting-started/upgrading.mdx` names retired 1.x commands in its "What changed in the commands" table, so they show as DOC-ORPHAN on every run.

### Step 7: Print the report

Markdown only. No preamble. Use this exact structure. Empty sections collapse.

```
source-survey: <ISO date>
gaia path: ~/Development/gaia-react/gaia
docs path: ~/Development/gaia-react/docs/src/content/docs
release-exclude patterns: <count>
do-not-document entries: <count>
hash rule: frontmatter + first 40 body lines (sha256)

## counts by layer
- commands: <n> (adopter <a>, contributor <c>, mixed <m>)
- skills: <n> (...)
- references: <n> (...)
- cli-subcommands: <n> (...)
- hooks: <n> (...)
- rules: <n> (...)
- agents: <n> (...)
- workflows: <n> (...)
- wiki-pages: <n> (...)

## AUDIENCE-CHANGED (high priority)
### adopter → contributor
- <kind> <name> at <path>: was adopter, now contributor (excluded by release-exclude line <#>)
### contributor → adopter
- <kind> <name> at <path>: was contributor, now adopter
### → mixed
- <kind> <name> at <path>: now contains gaia:maintainer-only block(s) at lines <a>-<b>

## NEW (in source, not in snapshot, not excluded)
### adopter
- <kind> <name> at <path>
  description: <one line>
### contributor
- <kind> <name> at <path>
### mixed
- <kind> <name> at <path>; marker blocks at <ranges>

## CHANGED (description or content drift)
### adopter
- <kind> <name> at <path>
  was-hash: <prev>
  now-hash: <curr>
  description-changed: <yes|no>
### contributor
- ...
### mixed
- ...

## REMOVED (in snapshot, not in source)
- <kind> <name> at <path> (was <audience>)

## EXCLUDED (matched do-not-document.yml)
- <kind> <name> at <path>
  reason: <reason from yaml>

## VERIFIED
- count: <n>
  (full list available with --verbose; omitted by default)

## DOC-ORPHAN (documented but no longer in source)
- docs page <docs path>:<line> references <kind> <name> which no longer exists in gaia/

## UNDOCUMENTED (adopter source items with no docs reference)
- <kind> <name> at <path>

## ambiguities (unresolved during survey)
- <one-line description of an item the survey couldn't classify with confidence>
```

### Step 8: Write the snapshot to disk

`--write` replaces `~/Development/gaia-react/docs/.claude/audit/source-state.json` and prints `snapshot written: N items -> .claude/audit/source-state.json (gaia <sha>)`. Do NOT print the JSON to chat.

### Step 9: Tell the user it's done

End with one line confirming the file was written and the gaia commit it was captured against.

## Idempotency rules

- Sort all walks by path before processing.
- Sort all output lists alphabetically by `(kind, name, path)`.
- Hash inputs deterministically (no timestamps inside the hash).
- The `captured_at` field in the suggested snapshot is the only non-deterministic value; document this as a known exception.
- If the user runs the skill twice in a row with no source change, the report bodies must match line-for-line except for `captured_at`.

## What this skill does NOT do

- Does not write to `~/Development/gaia-react/gaia/`.
- Does not write to `~/Development/gaia-react/docs/src/content/docs/`.
- Does not auto-commit `source-state.json`. The user accepts the snapshot explicitly.
- Does not audit voice (that is `voice-check`).
- Does not audit factual claims in existing docs (that is the `docs-audit` agent).
- Does not infer behavior. If an item cannot be classified, list it under `ambiguities` instead of guessing.

## Common surface-walk hazards

- Folders under `gaia/.claude/skills/gaia/references/` (`spec/`, `plan/`, `cleanse/`, `debt/`, `forensics/`, `wiki/`, `setup/`) are not records; the `.md` files inside are.
- `gaia/.claude/skills/<name>/` may contain files other than `SKILL.md` (e.g., `references/`, supporting markdown). Only `SKILL.md` is the surface record at Layer 2.
- The `gaia` binary CLI source is excluded from the adopter tarball, but the binary itself ships. Source-survey reports CLI subcommands by their *invocation* audience (who can run the command) and notes when the consumer of a subcommand is contributor-only (e.g., `release` subcommands).
- `gaia/wiki/.obsidian/` is not surface; skip it.
- Files inside a `gaia:maintainer-only` block (either marker form) are not stripped from the file on disk; they are stripped only at release time by `gaia release scrub`. Source-survey must read both halves to compute `audience: mixed`.

## Reading list

- `~/Development/gaia-react/gaia/.gaia/release-exclude`: the path-level adopter / contributor split.
- `~/Development/gaia-react/gaia/wiki/concepts/Release Workflow.md`: narrative explanation of the distribution boundary (contributor-only file, but readable for context).
- `~/Development/gaia-react/docs/CLAUDE.md`: the docs project's audience rules.
- `~/Development/gaia-react/studio/branding/VOICE.md`: voice rules. This skill itself is procedural, but any prose it generates obeys voice rules (no em dashes, no AI tells, no borrowed-field jargon).
