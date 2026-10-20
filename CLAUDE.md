# GAIA Docs

Public technical documentation for GAIA. Starlight (Astro). Served at docs.gaiareact.com. Deployed to GitHub Pages on push to `main`.

## Response style

Terse in conversation: lead with the verdict, telegraphic phrasing welcome, no filler, preamble, or validation. Brevity cuts filler, never coverage. Docs pages and substantial copy stay complete.

Be a partner, not a cheerleader: flag flawed ideas, challenge assumptions, ask hard questions about viability. Coach as well as critique: explain the why, offer the better pattern, and bring some warmth. Relentless pushback wears thin. The goal is to enjoy the work and do great work together.

## What this project is (and is not)

- **Is**: public-facing technical reference: how GAIA works, how to install it, how to use rules / hooks / skills / commands / agents, configuration, troubleshooting.
- **Is not**: marketing. Hero copy, positioning, pricing, "why GAIA", landing-page narrative all belong in `~/Development/gaia-react/website/`. Don't drift into pitch mode.
- **Is not**: strategy or roadmap. Public roadmap copy lives in `website/`. Internal strategy lives in `studio/`. Don't surface either here.

## Adopter docs vs contributor docs (load-bearing)

GAIA has two audiences and the docs must keep them strictly separate:

- **Adopters**: people who ran `npx create-gaia my-app` and got a scaffolded project. They have only what shipped in the release tarball. They never run `/gaia-release`, never edit the CLI source, never see `.gaia/cli/health/`.
- **Contributors**: people working on the GAIA template repo itself, including the core maintainer (Steven) and any outside contributors. They have the full source, run releases, build the bundled CLI, run health audits, and have access to the full command and tooling surface.

**Public-facing term is "Contributors."** Internal source uses "maintainer-only" as a literal identifier (`gaia:maintainer-only` markers, `.gaia/release-exclude` comment text); keep that exact phrase when citing those mechanisms, but every user-facing surface (sidebar, URLs, page titles, prose) says "Contributors."

**Routing convention:**

- Adopter docs live at the top of `src/content/docs/`.
- Contributor docs live under `src/content/docs/contributors/`.
- The `/contributors/*` URL prefix is the audience signal. The sidebar groups them separately so adopters never wander into contributor territory.

**Source of truth for the split:** `~/Development/gaia-react/gaia/.gaia/release-exclude`. This file is the authoritative manifest of paths excluded from the adopter tarball. Read it before claiming anything ships or doesn't.

**Two exclusion mechanisms** (both stripped by `gaia release scrub` at release time):

1. **Path-level exclusion**: entire files / directories listed in `.gaia/release-exclude`. Examples: `.claude/commands/gaia-release.md`, `.claude/commands/distribution-vet.md`, `.claude/skills/release-notes`, `.claude/agents/code-audit-maintainer-*.md`, `.claude/rules/maintainers/`, `.gaia/tests/`, `.gaia/scripts/tests/`, `.gaia/cli/src/`, `.gaia/cli/health/`, `.githooks/pre-push`, `wiki/entities/`, `wiki/meta/`, `wiki/concepts/Release Workflow.md`, `wiki/decisions/Bundle-time Scrub.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `README.md`, `SUPPORTERS.md`.
2. **Block-level exclusion**: content between `<!-- gaia:maintainer-only:start -->` and `<!-- gaia:maintainer-only:end -->` markers inside files that DO ship (currently used in `wiki/`, `.claude/` (for example `.claude/rules/pr-merge.md`), `.gaia/audit-ci.yml`, and `.githooks/pre-commit`). The shipped file is a subset of the source.

**The hard rule:** an adopter docs page must not reference any path, command, skill, agent, rule, or behavior that is excluded by either mechanism. A leak is a category-A failure, worse than a stale fact, because it signposts contributor-only content the adopter cannot have.

**The inverse rule (softer):** a contributor docs page should not duplicate what's already in the adopter docs. Cross-link instead.

## GAIA's actual surface (verified against gaia `36065df9`, 2026-10-21, GAIA 2.0.0; volatile, re-check before publishing)

GAIA 2.0.0 is a pnpm workspace: the shared harness at the root (`.claude/`, `.gaia/`, `.githooks/`, `.github/`, `wiki/`, root `CLAUDE.md`) and the React app plus its frontend-only harness in `frontend/` (`frontend/app/`, `frontend/.claude/{rules,skills,agents}`, `frontend/CLAUDE.md`). Every 1.x `app/...` path is now `frontend/app/...`. Releases ship as `gaia-bundle-<tag>.tar.gz` with a `.sha256`.

**Layer 1: slash commands** at `gaia/.claude/commands/*.md`:

| Adopter | Contributor-only |
|---|---|
| `/gaia-init`, `/setup-gaia` (replaces `/setup-gaia-ci` and `/setup-cloned-gaia-project`), `/gaia-spec`, `/gaia-plan`, `/gaia-debt`, `/gaia-residue`, `/gaia-cleanse` (was `/gaia-audit`), `/gaia-codify` (was `/gaia-harden`), `/gaia-fitness`, `/gaia-forensics`, `/gaia-serena-sync` | `/gaia-release`, `/distribution-vet` |

User-only commands set `disable-model-invocation` (`/gaia-init`, `/setup-gaia`, `/gaia-fitness`, `/gaia-forensics`, `/gaia-codify`, `/gaia-residue`, `/gaia-serena-sync`). `/health-audit`, `/gaia-handoff` and `/gaia-pickup` are removed.

**Layer 2: skills.** Root `gaia/.claude/skills/*/SKILL.md`: `gaia-wiki`, `update-deps`, `update-gaia` (skill-backed slash commands), `file-tech-debt`, `naming-conventions`, `tdd`, plus the `gaia/` references folder (no slash entry). Frontend `gaia/frontend/.claude/skills/`: `a11y-fixes`, `eslint-fixes`, `gaia-react-perf`, `new-component`, `new-hook`, `new-route`, `new-service`, `playwright-cli`, `react-code`, `skeleton-loaders`, `tailwind`, `tdd-react`, `typescript`. `react-doctor` installs per machine under `frontend/.claude/skills/` (gitignored). Contributor-only: the `release-notes` skill.

**Layer 3: workflow references** at `gaia/.claude/skills/gaia/references/`: `spec.md` (+`spec/`), `plan.md` (+`plan/`), `fitness.md`, `cleanse.md` (+`cleanse/`), `codify.md`, `debt.md` (+`debt/`), `residue.md`, `serena-sync.md`, `forensics.md` (+`forensics/`), `wiki.md` (+`wiki/`), `setup/`, `isolation.md`, `work-lifecycle.md`, `cost-record.md`. Contributor-only blocks inside them are marked `gaia:maintainer-only`.

spec-kit is gone: no `.specify/`, no `speckit.*` commands. The spec lifecycle lives in `.gaia/scripts/spec/`, `.gaia/templates/spec/` and `references/spec/`. Specs, plans and research live in the gitignored `.notebook/` at the main checkout.

**Layer 4: bundled CLI** at `gaia/.gaia/cli/gaia` (ships): `scaffold`, `react-perf reduce`, `wiki` (state, commit-classify, state-init, state-bump, log-prepend, page-index, orphans, near-collisions, dead-paths, frontmatter, empty-sections, broken-links, chain), `fitness`, `labels sync`, `packages sync-settings`, `codify-ledger`, `codify-tally`, `update`, `update-deps`, `init`, `setup`, `sandbox`, `ping`, `residue-tally`, `residue-cursor`, `residue-record`. `gaia --help` is authoritative. The release namespace lives only in `.gaia/cli/gaia-maintainer` (contributor-only). CLI source (`.gaia/cli/src/`, `test-fixtures/`, configs) and `.gaia/cli/health/` are contributor-only.

**Layer 5: supporting machinery**:

| Surface | Adopter-shipped | Contributor-only |
|---|---|---|
| Hooks (`.claude/hooks/*.sh`, registered in `.claude/settings.json`; `frontend/.claude/settings.json` is generated from it plus an overlay) | All shipped: guards (`block-*`, `pr-merge-audit-check`, `red-verify-commit-check`, `worthiness-presence-check`, `audit-loop-bound`), recorders and context injectors, `provision-worktree`, `usage-capture`, `wiki-session-start` | none |
| Native git hooks (`.githooks/`) | `pre-commit`, `commit-msg` | `pre-push` |
| Rules | Root `.claude/rules/` (ambient-context-resolution, code-comments, code-search, coding-guidelines, context-discipline, file-placement, guards-must-fail, issue-claim, no-abbreviations, pr-merge, quality-gate, serena-cc-override, shell-cwd, subagent-dispatch, user-questions, wiki-style, working-doc-ids); frontend `frontend/.claude/rules/` (accessibility, api-service, coding-guidelines-react, design-baseline, i18n, playwright, ports, react-router-docs, routes, shadcn-ui, state-pattern, storybook, tailwind) | `.claude/rules/maintainers/`, `.claude/rules/bats-assertions.md` |
| Agents (`.claude/agents/`) | `code-audit-frontend` (+ `frontend/.claude/agents/code-audit-frontend/` extensions), `code-audit-github-workflows`, `audit-loop-unit`, `audit-light-reviewer`, `worthiness-evaluator`, `uat-fidelity-judge`, `fitness-judge` | `code-audit-maintainer-node`, `code-audit-maintainer-shell` |
| CI workflows (`.github/workflows/`) | `tests.yml`, `chromatic.yml`, `pr-conventions.yml` (advisory) | `release.yml`, `cli-tests.yml`, `audit-ci-tests.yml`, `shell-lint.yml`, `forensics-triage.yml`. No Claude-on-Actions workflow exists any more (GAIA CI is removed). |
| Wiki (`gaia/wiki/`) | most of `modules/`, `concepts/`, `decisions/` | `entities/`, `meta/`, and the individual pages `.gaia/release-exclude` lists (Release Workflow, Release-Notes, Bundle-time Scrub, CLI-Binary-Split, Folding Shell Scripts into the CLI Binary, Forensics Triage Workflow, Sharded CI Test Matrix, Shell Guard Fixture Discrimination, Local Test Runtime, Dependabot as a Data Source), plus every `gaia:maintainer-only` block |
| Governance | `.gaia/templates/README.md` (regenerated at scaffold) | repo `README.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORTERS.md`, `.github/CODEOWNERS`, `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`, `.github/FUNDING.yml`, `.gaia/project.json` |

**Things that are protected by obscurity (do NOT document anywhere public):** CLI subcommand names beginning `_internal-`, and the `gaia-maintainer release*` subcommand list. The mentorship layer is removed in 2.0.0, so its old protections are moot. See `docs/.claude/audit/do-not-document.yml`.

When in doubt, grep `.gaia/release-exclude`. When a wiki page itself ships but contains `gaia:maintainer-only` blocks, treat those blocks as nonexistent for adopter purposes.

## References

- **Brand voice**: `~/Development/gaia-react/studio/branding/VOICE.md`: read before writing any docs copy. Voice rules apply to public-facing docs (no em dashes, no AI tells, no borrowed-field jargon, concrete numbers, etc.).
- **Brand identity**: `~/Development/gaia-react/studio/branding/IDENTITY.md`: read before writing copy that makes claims about what GAIA is or who it's for. Naming conventions live here.
- **Brand design**: `~/Development/gaia-react/studio/branding/DESIGN.md`: palette, typography, motion. Consult before adding visual assets or custom components.
- **Product source**: `~/Development/gaia-react/gaia/`: the GAIA app itself. **Source of truth for what to document.** Verify every feature claim, command name, hook behavior, skill trigger, and config option against the actual code before publishing. Studio does not track gaia source: that's this project's job.
- **Product wiki**: `~/Development/gaia-react/gaia/wiki/`: start at `gaia/wiki/index.md`. High-level architecture catalog and feature index. Use to discover what exists before reading the source.
- **Agentic Design audit**: `~/Development/gaia-react/studio/strategy/research/AGENTIC_DESIGN.md`: authoritative pattern-by-pattern evaluation. Consult before writing or revising any agentic-design page. Earlier "ReAct" / "four canonical patterns" framings are retired.

The `studio/` vault is the singular location for voice/branding/positioning knowledge. Don't copy any of it into this repo. Reference by path.

## Voice: docs adaptation

Studio's `VOICE.md` covers marketing, docs, and in-app strings together. For docs specifically:

- **Reference register, not pitch register.** Procedural and declarative. "Run `/gaia-cleanse` to review memory and auto-loaded files." Not "Unleash the power of `/gaia-cleanse`."
- **Voice rules still apply.** No em dashes anywhere. No AI tells (delve, tapestry, leveraging, seamless, robust, powerful). No borrowed-field jargon (substrate, paradigm, ecosystem, fabric). Grep for `—` before publishing.
- **Plain language.** Readers are engineers, but their experience varies widely. Explain in everyday words, keep jargon and internal vocabulary to a minimum, define an unavoidable term the first time a page uses it, and split long sentences. Plainer is often shorter; it never drops a fact.
- **Concrete over vague.** Real command names, real flags, real file paths, real numbers. Not "various options."
- **Code blocks are honest.** Examples should run. If a snippet won't work as written, it doesn't belong.
- **No "we" / "our team."** Either declarative ("GAIA installs…") or second-person instructional ("Run `pnpm install`…"). "Built by Steven Sacks" stays in marketing surfaces, not docs.

## Writing discipline for adjacent surfaces

Some adopter-facing commands and wiki pages internally reference mechanisms that are listed in `docs/.claude/audit/do-not-document.yml`. When a docs page covers one of these surfaces, the page must describe what the user sees and does without naming the deferred / obscured mechanism behind it.

**The rule:** name the user-visible behavior, not the mechanism.

**Current adjacent surfaces and how to handle them:**

- **The usage ping** (`gaia ping`, sent by `/gaia-init`, `/setup-gaia`, `/update-gaia` and the 2.0.0 migration). Documented as opt-out on the Telemetry page (`reference/telemetry.mdx`), which lists the three events and the categorical fields each adds: one fire-and-forget POST to telemetry.gaiareact.com with a few categorical fields, a pseudonymous per-install `projectId`, the GAIA version and a coarse platform, never paths or free text, turned off with `GAIA_TELEMETRY_PING_DISABLE=1`. Describe it in those terms only; do not document the server side, the payload schema beyond that, or how `projectId` is derived.
- **The local usage ledger** (`.gaia/local/telemetry/usage.jsonl`) is documented on `reference/cost.mdx`. It is local-only and is not the ping.
- The 1.x mentorship layer (and its `gaia mentorship` verbs, display rule and opt-in step) is removed in 2.0.0. Do not describe it; mention its removal only where the CHANGELOG makes it adopter-actionable.

**The registry is `docs/.claude/audit/do-not-document.yml`.** Before writing about any adopter command, hook, skill, or wiki page, check whether any deferred / obscured name appears in the source you're documenting. If yes, the page needs muting at write time. The `docs-audit` agent will also flag this on review, but writers should catch it first.

**This is distinct from the leak rule.** A leak is citing a *contributor-only path* in adopter docs (worse: out-of-bounds entirely). Adjacent-surface muting is citing an *adopter-shipped* mechanism the project has decided not to surface yet (deferred / obscurity-by-design). Both are reportable, but adjacent-surface mentions are easier to overlook because the source path is technically fair game.

## Verification protocol

Before documenting anything:

1. **Identify the audience.** Is this page adopter-facing (top of `src/content/docs/`) or contributor-facing (`src/content/docs/contributors/`)? Different rules apply.
2. **For adopter pages**: verify against the adopter-shipped subset only. Read `.gaia/release-exclude` first; if the path you're about to cite is excluded, the claim is a leak; kill it. Treat content inside `<!-- gaia:maintainer-only:start --> ... <!-- gaia:maintainer-only:end -->` blocks in shipped files as nonexistent.
3. **For contributor pages**: full `gaia/` tree is fair game.
4. Find the supporting code: app code in `gaia/frontend/app/`, root harness in `gaia/.claude/` (rules, skills, hooks, agents, commands), frontend harness in `gaia/frontend/.claude/` (read `gaia/frontend/CLAUDE.md` first).
5. If `gaia/wiki/` has a page, read it for context, but treat the source as authoritative if they conflict.
6. Run-or-read the actual file to confirm behavior matches what you're about to write.
7. Cite version-specific behavior with the gaia version it was verified against where it matters.

If a claim can't be grounded in the source, don't write it. Open a question instead.

## Starlight conventions

- Content lives in `src/content/docs/`. Each `.md` / `.mdx` file becomes a route at the same path.
- Sidebar registered in `astro.config.mjs`. Adding a new page means adding a sidebar entry; don't rely on autogenerate unless you've configured it.
- Frontmatter follows Starlight's `docsSchema()` (`src/content.config.ts`). At minimum: `title`, `description`. Use `sidebar.order` for explicit ordering when needed.
- Asides: `tip` (green, shield icon) is reserved for safety and privacy callouts. Use `note` for ordinary tips and `caution` for warnings.
- Images go in `src/assets/` and are imported. Static files (favicon, `CNAME`) go in `public/`.
- Site config: `astro.config.mjs`. `site` is `https://docs.gaiareact.com`; don't change without coordination.

## Local commands

```sh
pnpm install
pnpm dev      # http://localhost:4321
pnpm build    # production build → ./dist
pnpm preview  # preview the build
```

Pushes to `main` deploy via `.github/workflows/deploy.yml`. PRs build but do not deploy.

## When in doubt

- Voice question → read `studio/branding/VOICE.md`.
- Feature-claim question → read the source in `gaia/`.
- Positioning / framing question → it probably belongs on `website/`, not here. Ask before drifting.
