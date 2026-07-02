// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import llmsTxt from 'starlight-llms-txt';

// https://astro.build/config
export default defineConfig({
	site: 'https://docs.gaiareact.com',
	devToolbar: { enabled: false },
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
						'GAIA is a React and TypeScript framework that ships with a Claude Code configuration layer: slash commands, skills, hooks, rules, and agents that give Claude structure and focus when working in the codebase. Scaffold a project with `npx create-gaia my-app`. This documentation covers installing GAIA and using its commands, skills, and supporting machinery.',
					details: [
						'GAIA has two audiences.',
						'',
						'Adopters run `npx create-gaia` and get a scaffolded project with the commands, skills, hooks, rules, and agents that ship in the release.',
						'',
						'Contributors work on the GAIA template repo itself and additionally have the release tooling, bundled CLI internals, CI workflows, and wiki internals documented under `contributors/`.',
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
								'for people working on the GAIA template repo itself: CI workflows, the bundled CLI, releases, health audits, and wiki internals. Not needed if you installed GAIA with `npx create-gaia`.',
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
					],
				},
				{
					label: 'Workflow',
					items: [
						{ label: 'Overview', slug: 'workflow' },
						{ label: '/gaia-spec', slug: 'workflow/spec' },
						{ label: '/gaia-plan', slug: 'workflow/plan' },
						{ label: '/gaia-handoff', slug: 'workflow/handoff' },
						{ label: '/gaia-pickup', slug: 'workflow/pickup' },
						{ label: '/gaia-forensics', slug: 'workflow/forensics' },
					],
				},
				{
					label: 'Maintenance',
					items: [
						{ label: 'Overview', slug: 'maintenance' },
						{ label: 'GAIA CI', slug: 'maintenance/gaia-ci' },
						{ label: '/gaia-fitness', slug: 'maintenance/fitness' },
						{ label: '/gaia-audit', slug: 'maintenance/audit' },
						{ label: '/gaia-debt', slug: 'maintenance/debt' },
						{ label: '/gaia-harden', slug: 'maintenance/harden' },
						{ label: '/gaia-wiki', slug: 'maintenance/wiki' },
						{ label: '/update-deps', slug: 'maintenance/update-deps' },
						{ label: '/update-gaia', slug: 'maintenance/update-gaia' },
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
						{ label: 'Hooks', slug: 'reference/hooks' },
						{ label: 'Rules', slug: 'reference/rules' },
						{ label: 'Agents', slug: 'reference/agents' },
					],
				},
				{
					label: 'Contributors',
					collapsed: true,
					items: [
						{ label: 'Overview', slug: 'contributors' },
						{ label: 'CI workflows', slug: 'contributors/ci' },
						{ label: 'CLI surface', slug: 'contributors/cli' },
						{ label: 'Health audit', slug: 'contributors/health-audit' },
						{ label: 'Release', slug: 'contributors/release' },
						{ label: 'Wiki internals', slug: 'contributors/wiki' },
					],
				},
			],
		}),
	],
});
