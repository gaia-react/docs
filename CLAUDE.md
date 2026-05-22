# GAIA Docs

Public technical documentation for GAIA. Starlight (Astro). Served at docs.gaiareact.com. Deployed to GitHub Pages on push to `main`.

When reporting information to me, be extremely concise and sacrifice grammar for the sake of concision.

## What this project is (and is not)

- **Is** — public-facing technical reference: how GAIA works, how to install it, how to use rules / hooks / skills / commands / agents, configuration, troubleshooting.
- **Is not** — marketing. Hero copy, positioning, pricing, "why GAIA", landing-page narrative all belong in `~/Development/gaia-react/website/`. Don't drift into pitch mode.
- **Is not** — strategy or roadmap. Public roadmap copy lives in `website/`. Internal strategy lives in `studio/`. Don't surface either here.

## Adopter docs vs contributor docs (load-bearing)

GAIA has two audiences and the docs must keep them strictly separate:

- **Adopters** — people who ran `npx create-gaia my-app` and got a scaffolded project. They have only what shipped in the release tarball. They never run `/gaia-release`, never edit the CLI source, never see `.gaia/cli/health/`.
- **Contributors** — people working on the GAIA template repo itself, including the core maintainer (Steven) and any outside contributors. They have the full source, run releases, build the bundled CLI, run health audits, and have access to the full command and tooling surface.

**Public-facing term is "Contributors."** Internal source uses "maintainer-only" as a literal identifier (`gaia:maintainer-only` markers, `.gaia/release-exclude` comment text, `release.yml` step names) — keep that exact phrase when citing those mechanisms, but every user-facing surface (sidebar, URLs, page titles, prose) says "Contributors."

**Routing convention:**

- Adopter docs live at the top of `src/content/docs/`.
- Contributor docs live under `src/content/docs/contributors/`.
- The `/contributors/*` URL prefix is the audience signal. The sidebar groups them separately so adopters never wander into contributor territory.

**Source of truth for the split:** `~/Development/gaia-react/gaia/.gaia/release-exclude`. This file is the authoritative manifest of paths excluded from the adopter tarball. Read it before claiming anything ships or doesn't.

**Two exclusion mechanisms** (both stripped by `gaia release scrub` at release time):

1. **Path-level exclusion** — entire files / directories listed in `.gaia/release-exclude`. Examples: `.claude/commands/gaia-release.md`, `.claude/commands/health-audit.md`, `.claude/rules/_internal/`, `.gaia/tests/`, `.gaia/cli/src/`, `.gaia/cli/health/`, `wiki/entities/`, `wiki/meta/`, `wiki/concepts/Release Workflow.md`, `wiki/decisions/Bundle-time Scrub.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `README.md`, `SUPPORTERS.md`.
2. **Block-level exclusion** — content between `<!-- gaia:maintainer-only:start -->` and `<!-- gaia:maintainer-only:end -->` markers inside files that DO ship (currently used in `wiki/`, `.claude/`, `.specify/extensions/gaia/`). The shipped file is a subset of the source.

**The hard rule:** an adopter docs page must not reference any path, command, skill, agent, rule, or behavior that is excluded by either mechanism. A leak is a category-A failure — worse than a stale fact, because it signposts contributor-only content the adopter cannot have.

**The inverse rule (softer):** a contributor docs page should not duplicate what's already in the adopter docs. Cross-link instead.

## GAIA's actual surface (verified 2026-05-08, but volatile — re-check before publishing)

GAIA's invocation surface is layered. Knowing the layering is essential to documenting it correctly.

**Layer 1 — top-level slash commands** at `gaia/.claude/commands/*.md`:

| Adopter | Contributor-only |
|---|---|
| `/gaia-init`, `/setup-cloned-gaia-project` | `/gaia-release`, `/health-audit` |

**Layer 2 — top-level skills** at `gaia/.claude/skills/*/SKILL.md`. All adopter-shipped:

- `gaia` — *router*, see Layer 3 below
- Code skills: `react-code`, `typescript`, `tailwind`, `tdd`, `playwright-cli`, `eslint-fixes`, `skeleton-loaders`
- Scaffolders: `new-component`, `new-hook`, `new-route`, `new-service`
- Maintenance: `update-deps`, `update-gaia`

**Layer 3 — `/gaia` skill sub-routes** at `gaia/.claude/skills/gaia/references/*.md` (or `references/wiki/*.md`). Adopter-shipped. Invoked as `/gaia <sub>`:

- `/gaia plan` — orchestrator + per-task subagents
- `/gaia spec` — frozen-UAT spec workflow with operational primitives
- `/gaia audit` — codebase audit
- `/gaia handoff`, `/gaia pickup` — context transfer
- `/gaia forensics` — bug-report bridge with redacting/classifying flow
- `/gaia wiki sync | consolidate | lint` (or no arg = full chain) — wiki maintenance. Renamed from `/wiki-*` in PR #121 to dodge `claude-obsidian:wiki-lint` plugin collision.

**Layer 4 — spec-kit extension commands** at `gaia/.specify/extensions/gaia/commands/*.md`. Adopter-shipped, registered through spec-kit (v0.8.5) namespace `speckit.gaia.*`:

- `/speckit.gaia.spec`, `/speckit.gaia.constitution-check`, `/speckit.gaia.lint`, `/speckit.gaia.self-review`, `/speckit.gaia.spec-close`, `/speckit.gaia.uat-write`, `/speckit.gaia.wiki-promote`

**Layer 5 — bundled CLI** at `gaia/.gaia/cli/gaia` (binary, ships) with subcommand surface:

- `gaia scaffold {component|hook|route|service}`
- `gaia wiki {state|commit-classify|state-bump|log-prepend|page-index|orphans|near-collisions|dead-paths|state-init|sync land}`
- `gaia update merge`
- `gaia release {preflight|bump|changelog|scrub-wiki|manifest|commit-and-tag|scrub|runtime-deps}` (release subcommands are mostly contributor-relevant; the binary ships either way)
- `gaia setup {status|mark-step|finalize|link-worktree}`
- `gaia mentorship {status|enable|disable|...}` *(do not document the protected display-rule path — obscurity-by-design)*
- `gaia telemetry {emit|parse-stdin|parse-trailer}`
- `gaia init {strip-branding|configure-i18n|rename|wire-statusline|finalize|resume}`

CLI source (`.gaia/cli/src/`, `__tests__/`, `test-fixtures/`, `health/`) is contributor-only.

**Layer 6 — supporting machinery**:

| Surface | Adopter-shipped | Contributor-only |
|---|---|---|
| Hooks (`.claude/hooks/*.sh`) | All currently shipped (block-* / check-* / wiki-* / audit-stamp-trailer / pr-merge-audit-check / telemetry-task-postuse / intercept-init) | none |
| Rules (`.claude/rules/*.md`) | 16 top-level (accessibility, api-service, code-search, coding-guidelines, i18n, instruction-files, knip, playwright, quality-gate, routes, shell-cwd, state-pattern, storybook, tailwind, wiki-style) | `.claude/rules/_internal/` (convention exists, dir currently empty) |
| Agents (`.claude/agents/`) | `code-review-audit` | none currently |
| CI workflows (`.github/workflows/`) | `chromatic.yml`, `tests.yml`, `code-review-audit.yml`, `forensics-triage.yml` | `release.yml`, `cli-tests.yml`, `distribution.yml` |
| Wiki (`gaia/wiki/`) | most of `modules/`, `concepts/`, `decisions/` | `entities/`, `meta/`, `concepts/Release Workflow.md`, `decisions/Bundle-time Scrub.md`, plus any block inside `<!-- gaia:maintainer-only:start/end -->` markers |
| Templates | `.gaia/templates/README.md` (regenerated for adopters at scaffold) | repo `README.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORTERS.md` |

**Things that are protected by obscurity (do NOT document anywhere public):**

- The mentorship-display rule path or contract (`.gaia/cli/src/mentorship/display-rule.ts` and what it injects)
- The shape of the protected telemetry stream path (`events-*.jsonl` patterns under `~/.claude/projects/<slug>/gaia/telemetry/mentorship/`)

When in doubt, grep `.gaia/release-exclude`. When a wiki page itself ships but contains `gaia:maintainer-only` blocks, treat those blocks as nonexistent for adopter purposes.

## References

- **Brand voice** — `~/Development/gaia-react/studio/branding/VOICE.md` — read before writing any docs copy. Voice rules apply to public-facing docs (no em dashes, no AI tells, no borrowed-field jargon, concrete numbers, etc.).
- **Brand identity** — `~/Development/gaia-react/studio/branding/IDENTITY.md` — read before writing copy that makes claims about what GAIA is or who it's for. Naming conventions live here.
- **Brand design** — `~/Development/gaia-react/studio/branding/DESIGN.md` — palette, typography, motion. Consult before adding visual assets or custom components.
- **Product source** — `~/Development/gaia-react/gaia/` — the GAIA app itself. **Source of truth for what to document.** Verify every feature claim, command name, hook behavior, skill trigger, and config option against the actual code before publishing. Studio does not track gaia source — that's this project's job.
- **Product wiki** — `~/Development/gaia-react/gaia/wiki/` — start at `gaia/wiki/index.md`. High-level architecture catalog and feature index. Use to discover what exists before reading the source.
- **Agentic Design audit** — `~/Development/gaia-react/studio/strategy/research/AGENTIC_DESIGN.md` — authoritative pattern-by-pattern evaluation. Consult before writing or revising any agentic-design page. Earlier "ReAct" / "four canonical patterns" framings are retired.

The `studio/` vault is the singular location for voice/branding/positioning knowledge. Don't copy any of it into this repo. Reference by path.

## Voice — docs adaptation

Studio's `VOICE.md` covers marketing, docs, and in-app strings together. For docs specifically:

- **Reference register, not pitch register.** Procedural and declarative. "Run `/gaia audit` to check the current branch." Not "Unleash the power of `/gaia audit`."
- **Voice rules still apply.** No em dashes anywhere. No AI tells (delve, tapestry, leveraging, seamless, robust, powerful). No borrowed-field jargon (substrate, paradigm, ecosystem, fabric). Grep for `—` before publishing.
- **Concrete over vague.** Real command names, real flags, real file paths, real numbers. Not "various options."
- **Code blocks are honest.** Examples should run. If a snippet won't work as written, it doesn't belong.
- **No "we" / "our team."** Either declarative ("GAIA installs…") or second-person instructional ("Run `pnpm install`…"). "Built by Steven Sacks" stays in marketing surfaces, not docs.

## Writing discipline for adjacent surfaces

Some adopter-facing commands and wiki pages internally reference mechanisms that are listed in `docs/.claude/audit/do-not-document.yml`. When a docs page covers one of these surfaces, the page must describe what the user sees and does without naming the deferred / obscured mechanism behind it.

**The rule:** name the user-visible behavior, not the mechanism.

**Current adjacent surfaces and how to handle them:**

- **`/gaia-init`** — has a mentorship opt-in step. Describe it as *"opt into an optional adaptation feature"* (or skip the step entirely from the public flow). Do not name `gaia mentorship`, the display rule, the protected memory store, or any of the `_internal-*` subcommands. Do not describe what mentorship does mechanically.
- **`/setup-cloned-gaia-project`** — mentions mentorship in its bootstrap. Same handling as `/gaia-init`.
- **`wiki/hot.md`, `wiki/index.md`** — both ship and contain references to telemetry / mentorship in their bodies. If you write a page that derives from or links to these, drop the telemetry / mentorship lines from your derivation. Treat the source as if those lines weren't there.
- **`/gaia spec`, `/gaia plan`, spec-close** — incidentally mention telemetry-emit calls inside their flows. Document the user flow without explaining what gets emitted, where, or why.

**The registry is `docs/.claude/audit/do-not-document.yml`.** Before writing about any adopter command, hook, skill, or wiki page, check whether any deferred / obscured name appears in the source you're documenting. If yes, the page needs muting at write time. The `docs-audit` agent will also flag this on review, but writers should catch it first.

**This is distinct from the leak rule.** A leak is citing a *contributor-only path* in adopter docs (worse — out-of-bounds entirely). Adjacent-surface muting is citing an *adopter-shipped* mechanism the project has decided not to surface yet (deferred / obscurity-by-design). Both are reportable, but adjacent-surface mentions are easier to overlook because the source path is technically fair game.

## Verification protocol

Before documenting anything:

1. **Identify the audience.** Is this page adopter-facing (top of `src/content/docs/`) or contributor-facing (`src/content/docs/contributors/`)? Different rules apply.
2. **For adopter pages**: verify against the adopter-shipped subset only. Read `.gaia/release-exclude` first; if the path you're about to cite is excluded, the claim is a leak — kill it. Treat content inside `<!-- gaia:maintainer-only:start --> ... <!-- gaia:maintainer-only:end -->` blocks in shipped files as nonexistent.
3. **For contributor pages**: full `gaia/` tree is fair game.
4. Find the supporting code — components in `gaia/app/`, claude-side machinery in `gaia/.claude/` (rules, skills, hooks, agents, commands).
5. If `gaia/wiki/` has a page, read it for context — but treat the source as authoritative if they conflict.
6. Run-or-read the actual file to confirm behavior matches what you're about to write.
7. Cite version-specific behavior with the gaia version it was verified against where it matters.

If a claim can't be grounded in the source, don't write it. Open a question instead.

## Starlight conventions

- Content lives in `src/content/docs/`. Each `.md` / `.mdx` file becomes a route at the same path.
- Sidebar registered in `astro.config.mjs`. Adding a new page means adding a sidebar entry — don't rely on autogenerate unless you've configured it.
- Frontmatter follows Starlight's `docsSchema()` (`src/content.config.ts`). At minimum: `title`, `description`. Use `sidebar.order` for explicit ordering when needed.
- Images go in `src/assets/` and are imported. Static files (favicon, `CNAME`) go in `public/`.
- Site config: `astro.config.mjs`. `site` is `https://docs.gaiareact.com` — don't change without coordination.

## Local commands

```sh
npm install
npm run dev      # http://localhost:4321
npm run build    # production build → ./dist
npm run preview  # preview the build
```

Pushes to `main` deploy via `.github/workflows/deploy.yml`. PRs build but do not deploy.

## When in doubt

- Voice question → read `studio/branding/VOICE.md`.
- Feature-claim question → read the source in `gaia/`.
- Positioning / framing question → it probably belongs on `website/`, not here. Ask before drifting.
