// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import llmsTxt from 'starlight-llms-txt';
import rehypeExternalLinks from 'rehype-external-links';

// https://astro.build/config
export default defineConfig({
	site: 'https://docs.gaiareact.com',
	devToolbar: { enabled: false },
	// Links to other sites open in a new tab.
	markdown: {
		rehypePlugins: [
			[
				rehypeExternalLinks,
				{
					target: '_blank',
					rel: ['noopener', 'noreferrer'],
					// Screen readers announce the new tab.
					content: {
						type: 'element',
						tagName: 'span',
						properties: { className: ['sr-only'] },
						children: [{ type: 'text', value: ' (opens in a new tab)' }],
					},
				},
			],
		],
	},
	// Old 1.x URLs. GitHub Pages serves static files only, so Astro emits a
	// meta-refresh page at each old path.
	redirects: {
		'/commands': '/workflow/',
		'/commands/spec': '/workflow/spec/',
		'/commands/plan': '/workflow/plan/',
		'/commands/forensics': '/workflow/forensics/',
		'/commands/audit': '/maintenance/cleanse/',
		'/commands/harden': '/maintenance/codify/',
		'/commands/fitness': '/maintenance/fitness/',
		'/commands/wiki': '/maintenance/wiki/',
		'/commands/update-deps': '/maintenance/update-deps/',
		'/commands/update-gaia': '/maintenance/update-gaia/',
		'/commands/handoff-pickup': '/workflow/work-lifecycle/#resuming-long-work',
		'/getting-started/setup-gaia-ci': '/getting-started/setup-gaia/',
		'/getting-started/setup-cloned-gaia-project': '/getting-started/setup-gaia/',
		'/contributors/health-audit': '/contributors/#before-a-release',
	},
	integrations: [
		starlight({
			title: 'GAIA Docs',
			description: 'Documentation for GAIA. Order and focus for Claude Code.',
			customCss: ['./src/styles/theme.css'],
			// Keep our bespoke src/pages/404.astro; don't let Starlight inject its own.
			disable404Route: true,
			editLink: {
				baseUrl: 'https://github.com/gaia-react/docs/edit/main/src/content/docs/',
			},
			components: {
				Header: './src/overrides/Header.astro',
				MobileMenuFooter: './src/overrides/MobileMenuFooter.astro',
				PageSidebar: './src/overrides/PageSidebar.astro',
			},
			social: [
				{
					icon: 'github',
					label: 'GitHub',
					href: 'https://github.com/gaia-react/gaia',
				},
			],
			plugins: [
				// Generates /llms.txt, /llms-full.txt, /llms-small.txt, and per-set files
				// so Claude Code (and other agents) can ingest these docs cleanly.
				llmsTxt({
					projectName: 'GAIA',
					description:
						'GAIA is a React and TypeScript foundation that ships with a Claude Code layer: slash commands, skills, hooks, rules, agents, commit gates, and a pre-merge audit that give Claude structure and focus when working in the codebase. Scaffold a project with `npx create-gaia my-app`. This documentation covers installing GAIA, upgrading from 1.x, and using its commands, skills, gates, and supporting machinery.',
					details: [
						'GAIA has two audiences.',
						'',
						'Adopters run `npx create-gaia` and get a scaffolded project with the commands, skills, hooks, rules, and agents that ship in the release.',
						'',
						'Contributors work on the GAIA repo itself and additionally have the release tooling, bundled CLI internals, maintainer CI workflows, and wiki internals documented under `contributors/`.',
						'',
						'The abridged documentation below covers adopter surface only. Contributor documentation is available as a separate set.',
					].join('\n'),
					// Lead with install, then follow the sidebar order.
					promote: [
						'index*',
						'getting-started/**',
						'workflow/**',
						'maintenance/**',
						'skills/**',
						'reference/**',
					],
					// Push contributor pages to the end of llms-full.txt (they sort near
					// the top alphabetically otherwise).
					demote: ['contributors/**'],
					// Keep contributor-only surface out of the compact adopter file.
					exclude: ['contributors/**'],
					customSets: [
						{
							label: 'Contributor documentation',
							paths: ['contributors/**'],
							description:
								'for people working on the GAIA repo itself: maintainer CI workflows, the bundled CLI, releases, and wiki internals. Not needed if you installed GAIA with `npx create-gaia`.',
						},
					],
				}),
			],
			sidebar: [
				{
					label: 'Getting started',
					items: [
						{ label: 'Quick Start', slug: 'index' },
						{ label: '/gaia-init', slug: 'getting-started/gaia-init' },
						{ label: '/setup-gaia', slug: 'getting-started/setup-gaia' },
						{ label: 'Onboarding, as you build', slug: 'getting-started/onboarding' },
						{ label: 'Project layout', slug: 'getting-started/project-layout' },
						{ label: 'Deployment', slug: 'getting-started/deployment' },
						{ label: 'Upgrading from 1.x', slug: 'getting-started/upgrading' },
					],
				},
				{
					label: 'Workflow',
					items: [
						{ label: 'Overview', slug: 'workflow' },
						{ label: 'Work lifecycle', slug: 'workflow/work-lifecycle' },
						{ label: 'Notebook', slug: 'workflow/notebook' },
						{ label: 'Statusline', slug: 'workflow/statusline' },
						{ label: 'Test-driven development', slug: 'workflow/tdd' },
						{ label: 'Code Audit Team', slug: 'workflow/code-audit-team' },
						{ label: 'Tech debt', slug: 'workflow/tech-debt' },
						{ label: 'Git hooks and conventions', slug: 'workflow/git-conventions' },
						{ label: '/gaia-spec', slug: 'workflow/spec' },
						{ label: '/gaia-plan', slug: 'workflow/plan' },
						{ label: '/gaia-forensics', slug: 'workflow/forensics' },
					],
				},
				{
					label: 'Maintenance',
					items: [
						{ label: 'Overview', slug: 'maintenance' },
						{ label: '/update-gaia', slug: 'maintenance/update-gaia' },
						{ label: '/update-deps', slug: 'maintenance/update-deps' },
						{ label: '/gaia-cleanse', slug: 'maintenance/cleanse' },
						{ label: '/gaia-codify', slug: 'maintenance/codify' },
						{ label: '/gaia-debt', slug: 'maintenance/debt' },
						{ label: '/gaia-residue', slug: 'maintenance/residue' },
						{ label: '/gaia-wiki', slug: 'maintenance/wiki' },
						{ label: '/gaia-fitness', slug: 'maintenance/fitness' },
						{ label: '/gaia-serena-sync', slug: 'maintenance/serena-sync' },
					],
				},
				{
					label: 'Skills',
					items: [
						{ label: 'Overview', slug: 'skills' },
						{ label: 'Code skills', slug: 'skills/code' },
						{ label: 'Scaffolders', slug: 'skills/scaffolders' },
						{ label: 'React performance', slug: 'skills/react-performance' },
					],
				},
				{
					label: 'Reference',
					items: [
						{ label: 'Gates', slug: 'reference/gates' },
						{ label: 'Hooks', slug: 'reference/hooks' },
						{ label: 'Rules', slug: 'reference/rules' },
						{ label: 'Agents', slug: 'reference/agents' },
						{ label: 'Cost and usage ledger', slug: 'reference/cost' },
						{ label: 'Token efficiency', slug: 'reference/token-efficiency' },
						{ label: 'Labels', slug: 'reference/labels' },
						{ label: 'Telemetry', slug: 'reference/telemetry' },
						{ label: '.gaia folder', slug: 'reference/gaia-folder' },
					],
				},
				{
					label: 'Contributors',
					collapsed: true,
					items: [
						{ label: 'Overview', slug: 'contributors' },
						{ label: 'CI workflows', slug: 'contributors/ci' },
						{ label: 'CLI surface', slug: 'contributors/cli' },
						{ label: 'Release', slug: 'contributors/release' },
						{ label: 'Wiki internals', slug: 'contributors/wiki' },
					],
				},
			],
		}),
	],
});
