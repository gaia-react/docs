---
name: source-survey
description: Walk the GAIA source repo and report what is new, changed, removed, or excluded relative to the last snapshot in .claude/audit/source-state.json. Run BEFORE writing or updating any docs page, when the user asks "what's new in gaia", "what changed since the last docs pass", "source survey", "what do we still need to document", or whenever the docs site may have drifted from gaia/. Outputs a structured drift report grouped by NEW / CHANGED / REMOVED / EXCLUDED / AUDIENCE-CHANGED / VERIFIED, with each item classified by audience (adopter / contributor / mixed). Idempotent. Does not auto-update the snapshot; suggests a commit.
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

- `~/Development/gaia-react/gaia/` — the GAIA source tree. Read-only.
- `~/Development/gaia-react/gaia/.gaia/release-exclude` — path-level adopter/contributor split.
- `~/Development/gaia-react/docs/.claude/audit/source-state.json` — last snapshot. May be empty `{}` on first run.
- `~/Development/gaia-react/docs/.claude/audit/do-not-document.yml` — obscurity-by-design exclusions.
- `~/Development/gaia-react/docs/src/content/docs/` — the docs tree. Walked to compute "documented but not in source" cases.

## Outputs

- A structured markdown report printed to the conversation.
- A *suggested* updated snapshot (printed as a fenced JSON block). Do not write it. Tell the user how to commit it.

## Procedure

### Step 1 — Load the exclusion mechanisms

Read `~/Development/gaia-react/gaia/.gaia/release-exclude`. Strip comments (`#`) and blank lines. The remaining lines are tar-style exclude patterns that must be converted to a regex set. Conversion rules:

- Leading `/` is implicit (patterns are relative to gaia root).
- A bare path like `.claude/commands/gaia-release.md` matches that exact path.
- A path ending with no glob like `.gaia/cli/src` matches the directory and everything under it.
- `*` matches one path segment (no `/`); `**` is not used in this file but treat it as multi-segment if encountered.

Cache the resulting pattern set as `RELEASE_EXCLUDE`.

Read `~/Development/gaia-react/docs/.claude/audit/do-not-document.yml`. Cache the `exclusions` list as `DO_NOT_DOCUMENT`. Each entry has `path` (glob) or `name` (substring or glob), plus `reason`.

### Step 2 — Walk the surface layers

Walk all six layers below. For each item, capture a record:

```
{
  "kind":         "command | skill | sub-route | spec-kit-cmd | cli-subcommand | hook | rule | agent | workflow | wiki-page",
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
2. Else if the file (when text) contains a `<!-- gaia:maintainer-only:start -->` marker, audience is `mixed`. Capture each marker block's start and end line numbers.
3. Else audience is `adopter`.

Also tag each item with an `excluded_from_docs: true | false` flag. Set true if the item matches any entry in `DO_NOT_DOCUMENT`.

#### Layer 1 — top-level slash commands

Path: `gaia/.claude/commands/*.md`. For each file:

- `kind = "command"`
- `name` = frontmatter `name`, falling back to filename without `.md`
- `description` = frontmatter `description`
- Path-level audience via `RELEASE_EXCLUDE` (e.g., `gaia-release.md` and `health-audit.md` are excluded → contributor).

#### Layer 2 — top-level skills

Path: `gaia/.claude/skills/*/SKILL.md` (one folder per skill, except `gaia/` whose sub-routes are Layer 3).

- `kind = "skill"`
- `name` = frontmatter `name`
- `description` = frontmatter `description` (which holds trigger phrases)

The `gaia` skill itself is captured as one Layer 2 item (the router). Its sub-routes are captured as Layer 3.

#### Layer 3 — `/gaia` skill sub-routes

Paths:

- `gaia/.claude/skills/gaia/references/*.md` → invoked as `/gaia <basename-without-md>`
- `gaia/.claude/skills/gaia/references/wiki/*.md` → invoked as `/gaia wiki <basename-without-md>`

Skip the `references/forensics/` and `references/wiki/` *folders* themselves (the .md files inside are the surface; folder-level subfolders without a sibling .md are sub-namespaces).

For each:

- `kind = "sub-route"`
- `name` = `/gaia <basename>` for top-level; `/gaia wiki <basename>` for the `wiki/` subfolder
- `description` = first line of the file body that isn't frontmatter or a heading-only line (best-effort; falls back to the H1)
- All adopter unless `RELEASE_EXCLUDE` says otherwise.

#### Layer 4 — spec-kit extension commands

Authoritative source: `gaia/.specify/extensions/gaia/extension.yml`. The `provides.commands[]` array is the canonical name list. Use the `name` field from that yaml verbatim (e.g., `speckit.gaia.spec`). The frontmatter `name:` in the underlying `.md` files uses hyphenated form (`speckit-gaia-spec`) which is a spec-kit registration artifact — prefer the dotted form from `extension.yml` for the `name` field.

For each entry:

- `kind = "spec-kit-cmd"`
- `name` = the dotted form from `extension.yml`
- `path` = `.specify/extensions/gaia/<file>` (file pulled from yaml)
- `description` = `description` from yaml entry; fall back to the file's frontmatter description
- All adopter unless `RELEASE_EXCLUDE` says otherwise.

If `extension.yml` and the on-disk `.md` set diverge (e.g., a yaml entry references a missing file, or vice versa), record the divergence as a separate ambiguity item rather than fabricating data.

#### Layer 5 — bundled CLI

The binary `gaia/.gaia/cli/gaia` ships. The source `gaia/.gaia/cli/src/` is contributor-only.

The subcommand surface is parsed from the routers:

- Top-level: `gaia/.gaia/cli/src/index.ts` — read `SUBCOMMAND_HANDLERS` keys: `init`, `mentorship`, `release`, `scaffold`, `setup`, `telemetry`, `update`, `wiki`. Plus the special-cased `_internal-fetch-coaching` (always treat as obscured per `DO_NOT_DOCUMENT`).
- Per-namespace: read each `gaia/.gaia/cli/src/<ns>/index.ts` for its handler keys.

Per-namespace specifics (parse from the corresponding `index.ts`):

- `mentorship`: `enable`, `disable`, `purge`, `status`; `analytics` group with `enable | disable | dry-run`; `_internal-assert-memory-rules`, `_internal-provision-dirs`, `_internal-write-config` (all `_internal-*` are excluded by `DO_NOT_DOCUMENT`).
- `release`: `preflight`, `bump`, `changelog`, `scrub-wiki`, `manifest`, `scrub`, `runtime-deps`, `commit-and-tag`. `release-exclude` does NOT exclude these from the binary (the binary ships), but `scrub`, `runtime-deps`, and the rest of `release` are functionally maintainer-only because `/gaia-release` (the consumer) is contributor-only. Mark `audience: adopter` (the binary surface ships) and add a note `consumer_audience: contributor` for the release subcommands so a future docs author can decide.
- `wiki`: `state`, `commit-classify`, `state-init`, `state-bump`, `log-prepend`, `page-index`, `orphans`, `near-collisions`, `dead-paths`; plus `sync` group with `land`. All adopter.
- `scaffold`: `component`, `hook`, `route`, `service`. Adopter.
- `update`: `merge`. Adopter.
- `setup`: `status`, `mark-step`, `finalize`, `link-worktree`. Adopter.
- `telemetry`: parse the `if (subcommand === '...')` lines from `gaia/.gaia/cli/src/telemetry/index.ts`. As of 2026-05-08 these are `emit`, `compute-profile`, `parse-stdin`. The directory also contains `parse-trailer.ts`, but it is a library helper not a routed subcommand; do not capture it as a `cli-subcommand`. Always re-derive from `index.ts` rather than the directory listing. Adopter audience.
- `init`: `strip-branding`, `configure-i18n`, `rename`, `wire-statusline`, `finalize`, `resume`. Adopter.

For each subcommand, capture:

- `kind = "cli-subcommand"`
- `name` = `gaia <ns> <sub>` or `gaia <ns> <group> <sub>` for nested groups (e.g., `gaia mentorship analytics enable`)
- `path` = the corresponding `<ns>/<sub>.ts` file under `.gaia/cli/src/` if present; else `<ns>/index.ts`
- `description` = the line from the `HELP_TEXT` block in the namespace's `index.ts` matching this subcommand (best-effort grep)
- `audience` per the rules above (note: source files are all under `.gaia/cli/src/` which is `RELEASE_EXCLUDE`d, but the *behavior* ships in the binary; treat the audience field as the **invocation audience** — i.e., who can run the command — not the source-shipping audience)

Mark any name containing `_internal-` as `excluded_from_docs: true` per `DO_NOT_DOCUMENT`.

#### Layer 6 — supporting machinery

Walk these globs and capture each file:

- Hooks: `gaia/.claude/hooks/*.sh` → `kind = "hook"`, `name` = filename. `description` = first non-shebang comment line if present, else null.
- Rules: `gaia/.claude/rules/*.md` → `kind = "rule"`, `name` = basename without `.md`, `description` = frontmatter `description` or H1. Plus `gaia/.claude/rules/_internal/*.md` (currently empty by convention — list as zero items if absent, do not error).
- Agents: `gaia/.claude/agents/*.md` → `kind = "agent"`, `name` = frontmatter `name`, `description` = frontmatter `description`.
- CI workflows: `gaia/.github/workflows/*.yml` → `kind = "workflow"`, `name` = filename, `description` = top-level `name:` field in the yaml.
- Wiki pages: `gaia/wiki/**/*.md` → `kind = "wiki-page"`, `name` = relative path under `wiki/`, `description` = frontmatter `description` if present, else H1.

### Step 3 — Compute content hash deterministically

Per record, the `content_hash` must be reproducible:

```sh
# For .md files:
{ awk '/^---$/{c++; if(c==2){exit}; next} c==1{print}' "$FILE";  \
  awk '/^---$/{c++; if(c==2){next}} c>=2' "$FILE" | head -n 40; } \
  | shasum -a 256 | awk '{print $1}'
```

For files with no frontmatter (hooks, workflows, ts), hash the full file if under 200 lines; otherwise the first 40 non-blank lines after any leading comment block. State the chosen rule once at the top of the report so the user knows.

For `cli-subcommand` records that map to a directory rather than a file, hash the namespace `index.ts` instead.

### Step 4 — Walk the docs side

Find every `.md` and `.mdx` under `~/Development/gaia-react/docs/src/content/docs/`. For each file, extract referenced GAIA things via best-effort regex:

- Slash commands: `/[a-z][a-z0-9-]*` and `/gaia [a-z-]+( [a-z-]+)?`
- Skill names: backtick-wrapped tokens that match a known top-level skill name.
- Source paths: backtick-wrapped tokens beginning with `gaia/`, `.claude/`, `.gaia/`, `.specify/`, or `wiki/`.
- Spec-kit commands: `/speckit.gaia.<name>` or `speckit.gaia.<name>`.
- CLI invocations: `gaia <subcommand>` patterns inside fenced code blocks or backticks.

Build a set `DOCUMENTED` of `(kind, name)` tuples that the docs reference. Best-effort is fine; do not block on parser perfection.

### Step 5 — Load the previous snapshot

Read `~/Development/gaia-react/docs/.claude/audit/source-state.json`. If it does not exist or is empty / `{}`, treat the previous state as no items — every current item will report as NEW.

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

### Step 6 — Compute drift

Match current items to previous items by the composite key `(kind, name, path)`. For each match, classify:

- **VERIFIED** — both records exist; `content_hash`, `description`, and `audience` all match.
- **CHANGED** — both records exist; `content_hash` or `description` differs; `audience` unchanged.
- **AUDIENCE-CHANGED** — both records exist; `audience` differs (e.g., adopter → contributor or contributor → adopter or anything → mixed). High-priority signal.
- **NEW** — current record exists, no matching previous record, AND not in `DO_NOT_DOCUMENT`.
- **REMOVED** — previous record exists, no matching current record. (If it is in `DO_NOT_DOCUMENT`, still report as REMOVED — removing an excluded item is normal but worth surfacing.)
- **EXCLUDED** — current record exists AND matches `DO_NOT_DOCUMENT`. Always categorize EXCLUDED items here regardless of whether they are NEW / CHANGED / VERIFIED. The point of this category is "we know we are deliberately ignoring this".

Cross-reference docs:

- For each item in `DOCUMENTED` that has no matching current source record, mark it as a **DOC-ORPHAN** (documented but no longer in source).
- For each adopter-audience source item NOT in `DOCUMENTED` and NOT in `DO_NOT_DOCUMENT`, flag as **UNDOCUMENTED** (this overlaps with NEW for first-run snapshots — keep them separate categories so the meaning is explicit).

### Step 7 — Print the report

Markdown only. No preamble. Use this exact structure. Empty sections collapse.

```
source-survey — <ISO date>
gaia path: ~/Development/gaia-react/gaia
docs path: ~/Development/gaia-react/docs/src/content/docs
release-exclude patterns: <count>
do-not-document entries: <count>
hash rule: frontmatter + first 40 body lines (sha256)

## counts by layer
- commands: <n> (adopter <a>, contributor <c>, mixed <m>)
- skills: <n> (...)
- sub-routes: <n> (...)
- spec-kit-cmds: <n> (...)
- cli-subcommands: <n> (...)
- hooks: <n> (...)
- rules: <n> (...)
- agents: <n> (...)
- workflows: <n> (...)
- wiki-pages: <n> (...)

## AUDIENCE-CHANGED (high priority)
### adopter → contributor
- <kind> <name> at <path> — was adopter, now contributor (excluded by release-exclude line <#>)
### contributor → adopter
- <kind> <name> at <path> — was contributor, now adopter
### → mixed
- <kind> <name> at <path> — now contains gaia:maintainer-only block(s) at lines <a>-<b>

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

### Step 8 — Print the suggested next snapshot

Append to the report:

```
## suggested next snapshot
```

Then a fenced JSON block matching the snapshot schema with the current items. Do NOT write to disk.

### Step 9 — Tell the user how to commit

End with this exact line, swapping in the actual command if the user has already wired one:

```
To accept this snapshot, copy the JSON block above to ~/Development/gaia-react/docs/.claude/audit/source-state.json. Re-running source-survey with no source change must produce identical output.
```

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

- `gaia/.claude/skills/gaia/references/forensics/` and `gaia/.claude/skills/gaia/references/wiki/` are sub-namespace folders. Iterate the `.md` files inside; do not treat the folder itself as a sub-route.
- `gaia/.specify/extensions/gaia/test/` is excluded by `release-exclude`. Do not include test files as spec-kit-cmd records.
- `gaia/.claude/skills/<name>/` may contain files other than `SKILL.md` (e.g., `references/`, supporting markdown). Only `SKILL.md` is the surface record at Layer 2.
- The `gaia` binary CLI source is excluded from the adopter tarball, but the binary itself ships. Source-survey reports CLI subcommands by their *invocation* audience (who can run the command) and notes when the consumer of a subcommand is contributor-only (e.g., `release` subcommands).
- `gaia/wiki/.obsidian/` is not surface; skip it.
- Files inside a `<!-- gaia:maintainer-only:start --> ... <!-- gaia:maintainer-only:end -->` block are not stripped from the file on disk; they are stripped only at release time by `gaia release scrub`. Source-survey must read both halves to compute `audience: mixed`.
- `gaia/.gaia/cli/src/_internal-fetch-coaching` does not exist as a file; it is a special-case top-level CLI subcommand handled inline in `gaia/.gaia/cli/src/index.ts`. Capture it as a virtual record with `path = ".gaia/cli/src/index.ts"`.

## Reading list

- `~/Development/gaia-react/gaia/.gaia/release-exclude` — the path-level adopter / contributor split.
- `~/Development/gaia-react/gaia/wiki/concepts/Release Workflow.md` — narrative explanation of the distribution boundary (contributor-only file, but readable for context).
- `~/Development/gaia-react/docs/CLAUDE.md` — the docs project's audience rules.
- `~/Development/gaia-react/studio/branding/VOICE.md` — voice rules. This skill itself is procedural, but any prose it generates obeys voice rules (no em dashes, no AI tells, no borrowed-field jargon).
