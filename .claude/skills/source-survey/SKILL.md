---
name: source-survey
description: Walk the GAIA source repo and report what is new, changed, removed, or excluded relative to the last snapshot in .claude/audit/source-state.json. Run BEFORE writing or updating any docs page, when the user asks "what's new in gaia", "what changed since the last docs pass", "source survey", "what do we still need to document", or whenever the docs site may have drifted from gaia/. Outputs a structured drift report grouped by NEW / CHANGED / REMOVED / EXCLUDED / AUDIENCE-CHANGED / VERIFIED, with each item classified by audience (adopter / contributor / mixed). Idempotent. Runs survey.py; replaces the snapshot only with --write and never commits it.
---

# source-survey

Idempotent drift detector for the GAIA documentation project. Walks the GAIA source surface at `~/Development/gaia-react/gaia/`, classifies every item as adopter, contributor, or mixed, computes drift against the snapshot at `~/Development/gaia-react/docs/.claude/audit/source-state.json`, and prints a grouped report.

This skill does not write docs. It reports drift so the user can decide what to document.

## When to run

- Before starting a new docs page or section.
- After a `gaia/` change lands that might affect public surface.
- When the user asks "what's new", "what changed", "what still needs docs", "source survey", "drift check".
- Before each docs release, at the release tag, with `--write`.

## Inputs

- `~/Development/gaia-react/gaia/`: the GAIA source tree. Read-only.
- `~/Development/gaia-react/gaia/.gaia/release-exclude`: path-level adopter / contributor split.
- `~/Development/gaia-react/gaia/.gaia/release-scrub.yml`: which files have `gaia:maintainer-only` blocks stripped at release, and with which marker.
- `~/Development/gaia-react/docs/.claude/audit/source-state.json`: last snapshot. May be missing or `{}` on first run.
- `~/Development/gaia-react/docs/.claude/audit/do-not-document.yml`: obscurity-by-design exclusions.
- `~/Development/gaia-react/docs/src/content/docs/`: the docs tree, walked for DOC-ORPHAN and UNDOCUMENTED.

## Outputs

- A structured markdown report printed to the conversation.
- With `--write`, the snapshot replaced at `~/Development/gaia-react/docs/.claude/audit/source-state.json`. Never print the JSON to chat.

## Run it

`survey.py` in this folder implements Steps 1 to 8. Run it from the docs repo root; never hand-walk the tree or hand-edit the snapshot.

```sh
python3 -I .claude/skills/source-survey/survey.py --ref <gaia ref> --write
```

- `--ref`: the gaia commit, tag, or branch to survey (default `HEAD` of the gaia checkout). Use the release tag for a release snapshot (`--ref v2.1.0`).
- `--write`: replace the snapshot after printing the report. Leave it off for a dry look; the report is the same either way, because drift is computed against the snapshot on disk before anything is written.
- `--gaia <path>`: the gaia checkout (default: `gaia/` next to this docs repo).
- `--verbose`: list every VERIFIED item.

Needs Python with tarfile extraction filters (3.12+, or the 3.8.17+ / 3.11.4+ backports). The script reads the committed tree at `--ref` through `git archive`, so uncommitted or untracked files in the gaia checkout never reach a snapshot, and `gaia_commit` is the full SHA of that ref. Relay the report to the user with your read on it: which hits need a docs change, which are expected noise (Step 6 lists the known kinds), and any ambiguity that points at a gaia bug.

The steps below are the contract the script implements. When you change one, change the script in the same commit, rerun it at the snapshot's own `gaia_commit`, and explain every item that leaves VERIFIED before you trust the change.

## Procedure

### Step 1: Load the exclusion mechanisms

**release-exclude.** Read `.gaia/release-exclude`. Skip comments (`#`) and blank lines. Each remaining line is a literal path relative to the gaia root, matching that path and everything under it: the release CLI compiles each line to `^<path>(/|$)` and rejects globs. A line with a glob character is reported under ambiguities. Cache the set as `RELEASE_EXCLUDE`.

**release-scrub.** Read `.gaia/release-scrub.yml`. Keep each `marker-strip` transform: its `paths` globs (`**/` spans any directories, `*` stays inside one segment), its `start` marker and its `end` marker. Cache them as `SCRUB`. A missing file or an incomplete transform is an ambiguity.

**do-not-document.** Read `.claude/audit/do-not-document.yml`. Each entry has `path` or `name`, plus `reason`. A `path` entry matches as a glob or as a prefix (the path itself or anything under it). A `name` entry matches as a glob anywhere in the name (`_internal-*` matches `gaia foo _internal-bar`). Cache the list as `DO_NOT_DOCUMENT`.

### Step 2: Walk the surface layers

Walk the layers below, sorted by path. For each item, capture a record:

```
{
  "kind":          "command | skill | skill-file | reference | cli-subcommand | hook | hook-lib | githook | rule | agent | doctrine | instruction | workflow | wiki-page",
  "path":          "<path relative to gaia/>",
  "name":          "<canonical name; see per-layer rules>",
  "description":   "<one line, or null>",
  "audience":      "adopter | contributor | mixed",
  "marker_blocks": [[startLine, endLine], ...],  // only when audience == mixed
  "content_hash":  "<sha256 of the whole file>",
  "excluded_from_docs": false
}
```

Audience per item:

1. If the path matches `RELEASE_EXCLUDE`, audience is `contributor`. Done.
2. Else, for each `SCRUB` transform whose `paths` match the file, find its blocks the way gaia's `release/marker-strip.ts` does: a line containing the start marker opens a block, a line containing the end marker closes it, a line containing both is a one-line block. If any block is found, audience is `mixed`; record each block's start and end line.
3. Else audience is `adopter`.

Ambiguities from this step, each a likely gaia bug worth raising:

- A marker line that also carries other text: the scrub drops that text with the marker.
- An end with no start, or a start never closed.
- A whole-line marker in a file no `SCRUB` transform covers: the block ships verbatim to adopters.

Set `excluded_from_docs` when the item matches `DO_NOT_DOCUMENT`.

#### Layer 1: top-level slash commands

`.claude/commands/*.md` → `kind = "command"`, `name` = `/` + frontmatter `name` (fallback: filename without `.md`), `description` = frontmatter `description`. `gaia-release.md` and `distribution-vet.md` are release-excluded, so contributor.

#### Layer 2: skills

`.claude/skills/**` and `frontend/.claude/skills/**`, except `.claude/skills/gaia/references/` (Layer 3) and the per-machine, gitignored `frontend/.claude/skills/react-doctor`.

- Each `SKILL.md` → `kind = "skill"`, `name` = frontmatter `name`, `description` = frontmatter `description` (it holds the trigger phrases).
- Every other file (references, templates, scripts) → `kind = "skill-file"`, `name` = path, `description` = frontmatter `description`, else H1, else the first prose line. Some carry maintainer-only blocks, so they are surveyed like any shipped file.

#### Layer 3: workflow references

`.claude/skills/gaia/references/**/*.md`. These are the workflows behind the `/gaia-*` slash commands. They are not invoked by name, so docs cite them through their command, never as `/gaia <sub>` (the 1.x form).

`kind = "reference"`, `name` = path under `references/` without `.md` (`spec`, `cleanse/apply`, `setup/per-machine`), `description` = the first body line that is not blank or a heading, falling back to the H1.

#### Layer 4: bundled CLI

The binary `.gaia/cli/gaia` ships; its source `.gaia/cli/src/` is contributor-only. The subcommand surface is parsed from the routers, never copied from a list:

- **Top level:** `src/index.ts`. Its router table is the object passed as `handlers:` to `createSubcommandRouter` or to `lookupOwn(...)`. Each key is a namespace; its handler's relative import names the namespace's module (`fitness/index.ts`, `codify/ledger.ts`, `residue/tally.ts`).
- **A module routes subcommands** when it passes a table to `lookupOwn(...)` or `handlers:` (keys and shorthand keys both count), or failing that has `sub|subcommand|action === '<name>') return <handler>(` branches. A `=== '<name>') {` branch handled inline routes to the same module.
- **Nested groups:** a subcommand whose own module routes again is walked the same way, up to three words deep (`gaia wiki chain begin`, `gaia codify-ledger snapshot record`).
- **A namespace whose module routes nothing** is one record, `gaia <ns>`.
- The release namespace lives only in the contributor-only `.gaia/cli/gaia-maintainer` binary. Do not capture it: its subcommand list is obscured per `DO_NOT_DOCUMENT`.

Per record:

- `kind = "cli-subcommand"`, `name` = `gaia <ns> [<group>] <sub>`.
- `path` = the module the handler is imported from; else `<sub>.ts` next to the router; else the router itself.
- `description` = that subcommand's entry in its router's own `HELP_TEXT`: the two-space-indented line naming it plus its continuation lines, whitespace collapsed. For a `gaia <ns>` record: the first paragraph of the module's `HELP_TEXT`, else the rest of its line in the top-level `HELP_TEXT`.
- `audience` = `adopter` for every record. This is the **invocation audience** (who can run it), not the source-shipping audience.
- An unresolvable import, a missing router table, or a table with no parsed keys is an ambiguity, never a crash.

#### Layer 5: supporting machinery

- **Hooks:** `.claude/hooks/*.sh` → `kind = "hook"`, `name` = filename, `description` = first comment line after the shebang that is not a `shellcheck` directive.
- **Hook libraries:** `.claude/hooks/lib/*` → `kind = "hook-lib"`, `name` = filename, `description` = frontmatter `description` or H1 for `.md`, first comment line otherwise.
- **Git hooks:** `.githooks/*` → `kind = "githook"`, `name` = filename, `description` = first comment line. `pre-push` is contributor-only.
- **Rules:** `.claude/rules/*.md`, `.claude/rules/maintainers/*.md` (contributor-only) and `frontend/.claude/rules/*.md` → `kind = "rule"`, `name` = basename for root rules, `maintainers/<basename>`, or `frontend:<basename>` (`frontend:i18n`); `description` = frontmatter `description` or H1.
- **Agents:** `.claude/agents/*.md` → `kind = "agent"`, `name` = frontmatter `name`, `description` = frontmatter `description`. Plus the frontend auditor's extension files, `frontend/.claude/agents/code-audit-frontend/*.md`, as `code-audit-frontend/<basename>`.
- **Doctrine:** `.claude/doctrine/*.md` (injected by hooks) → `kind = "doctrine"`, `name` = basename.
- **Instructions:** `frontend/.claude/instructions/*.md` (runbooks Claude follows on request) → `kind = "instruction"`, `name` = basename.
- **CI workflows:** `.github/workflows/*.yml` → `kind = "workflow"`, `name` = filename, `description` = top-level `name:`.
- **Wiki pages:** `wiki/**/*.md` minus `wiki/.obsidian/` → `kind = "wiki-page"`, `name` = the full `wiki/...` path (the snapshot keys on it, so any other form turns every page into a false NEW + REMOVED pair), `description` = frontmatter `description`, else H1.

### Step 3: Hash content

`content_hash` is the sha256 of the whole file, so an edit anywhere is drift. Earlier snapshots hashed only frontmatter plus 40 body lines; that hashed every frontmatter-less file to the same value and missed most edits to long files.

### Step 4: Walk the docs side

Read every `.md` and `.mdx` under `src/content/docs/`. Pages under `contributors/` count for DOC-ORPHAN but not for UNDOCUMENTED. Inside backtick spans, look for:

- **Slash commands:** a span whose first token is `/<name>`. It is an orphan when it is not a current command or skill but was one in the previous snapshot, or carries a GAIA prefix (`/gaia-`, `/setup-`, `/update-`, `/speckit.`). Claude Code built-ins (`/clear`) never match.
- **Skills:** a span that is exactly a skill name from the previous snapshot that no longer exists.
- **CLI:** a span starting `gaia <ns> [<sub>]` whose namespace, or subcommand under a routed namespace, does not exist.
- **Source paths:** a span under a surface folder (`.claude/{commands,skills,hooks,rules,agents,doctrine}/`, the matching `frontend/.claude/` folders, `.github/workflows/`, `.githooks/`, `wiki/`) that is missing from the tree. Any other missing path is a file the adopter's project creates at run time (`.gaia/local/*`, `settings.local.json`), and the per-machine `react-doctor` skill is skipped.

### Step 5: Load the previous snapshot

Read `.claude/audit/source-state.json`. If it is missing or `{}`, every current item reports as NEW. Schema:

```json
{
  "version": 1,
  "captured_at": "<ISO date>",
  "gaia_commit": "<full sha>",
  "items": [ { "kind": "...", "path": "...", "name": "...", "description": "...",
               "audience": "...", "content_hash": "...", "excluded_from_docs": false } ]
}
```

Records that match `DO_NOT_DOCUMENT` are never written to the snapshot: their names are what the registry protects, and the snapshot is committed.

### Step 6: Compute drift

Match current items to previous items by `(kind, name, path)`:

- **EXCLUDED:** matches `DO_NOT_DOCUMENT`, whatever else is true. Reported by kind and path only, never by name.
- **NEW:** no previous record.
- **AUDIENCE-CHANGED:** `audience` differs. High priority.
- **CHANGED:** `content_hash`, `description`, or `marker_blocks` differs.
- **VERIFIED:** all of those match.
- **REMOVED:** a previous record with no current match.

Cross-reference docs:

- **DOC-ORPHAN:** every Step 4 hit.
- **UNDOCUMENTED:** an adopter or mixed item that no adopter page names as a whole word. Wiki pages, references, skill files, hook libraries, doctrine and the `code-audit-frontend/*` extension files are reached through their command, the wiki or their parent, so they are never flagged. CLI subcommands collapse to one count line: Claude runs them, and pages name one only where the reader needs it.

Known noise, not a docs bug: `getting-started/upgrading.mdx` names retired 1.x commands in its "What changed in the commands" table, so they show as DOC-ORPHAN on every run.

### Step 7: Print the report

Markdown only, no preamble, empty sections collapse:

```
source-survey: <ISO date>
gaia path: <gaia checkout> @ <short sha>
docs path: src/content/docs
release-exclude patterns: <count>
release-scrub marker transforms: <count>
do-not-document entries: <count>
hash rule: sha256 of the whole file

## counts by layer
- <kind>: <n> (adopter <a>, contributor <c>, mixed <m>)

## AUDIENCE-CHANGED (high priority)
### <was> -> <now>
- <kind> <name> at <path>: was <a>, now <b> (release-exclude line <#> | gaia:maintainer-only blocks at <ranges>)

## NEW (in source, not in snapshot, not excluded)
### adopter | contributor | mixed
- <kind> <name> at <path>
  description: <one line>

## CHANGED (description or content drift)
### adopter | contributor | mixed
- <kind> <name> at <path>
  was-hash: <12 chars>  now-hash: <12 chars>
  description-changed: <yes|no>
  marker-blocks: <old> -> <new>        (only when they differ)

## REMOVED (in snapshot, not in source)
- <kind> <name> at <path> (was <audience>)

## EXCLUDED (matched do-not-document.yml; never written to the snapshot)
- <kind> at <path> (name withheld)
  reason: <reason>

## VERIFIED
- count: <n>                          (--verbose lists them)

## DOC-ORPHAN (documented but no longer in source)
- <page>:<line> references <command|skill|CLI|path> <name>

## UNDOCUMENTED (adopter source items no adopter page names)
- <kind> <name> at <path>
- cli-subcommand: <n> not named on any adopter page (...)

## ambiguities (unresolved during survey)
- <one line>
```

`<name> at <path>` drops the `at <path>` part when the name is the path (wiki pages, skill files).

### Step 8: Write the snapshot

`--write` replaces the snapshot atomically (temp file, then rename) and prints `snapshot written: N items -> .claude/audit/source-state.json (gaia <sha>)`. Never print the JSON to chat.

### Step 9: Tell the user

End with one line: whether the snapshot was written, and the gaia commit it was captured against. Never commit it; the user accepts the snapshot.

## Idempotency rules

- Walks are sorted by path; records by `(kind, name, path)`.
- Hashes have no timestamp input.
- `captured_at` is the only value that changes between two runs on the same ref; the report body matches line for line apart from its date.

## What this skill does NOT do

- Does not write to `~/Development/gaia-react/gaia/` or to `src/content/docs/`.
- Does not commit `source-state.json`.
- Does not audit voice (that is `voice-check`) or factual claims in pages (that is the `docs-audit` agent).
- Does not infer behavior. What it cannot classify goes under ambiguities.

## Common surface-walk hazards

- Folders under `.claude/skills/gaia/references/` are not records; the `.md` files inside are.
- CLI source is release-excluded, but the binary ships, so CLI records carry the invocation audience.
- `gaia:maintainer-only` blocks are not stripped on disk, only at release, and only in files a `release-scrub.yml` transform covers. Read the whole file to find them.

## Reading list

- `~/Development/gaia-react/gaia/.gaia/release-exclude` and `.gaia/release-scrub.yml`: the adopter / contributor split.
- `~/Development/gaia-react/gaia/wiki/concepts/Release Workflow.md`: the distribution boundary in prose (contributor-only, readable for context).
- `~/Development/gaia-react/docs/CLAUDE.md`: the docs project's audience rules.
- `~/Development/gaia-react/studio/branding/VOICE.md`: voice rules for any prose this skill produces.
