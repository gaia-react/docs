// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://docs.gaiareact.com',
	devToolbar: { enabled: false },
	integrations: [
		starlight({
			title: 'GAIA Docs',
			description: 'Documentation for GAIA. Order and focus for Claude Code.',
			customCss: ['./src/styles/theme.css'],
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
			sidebar: [
				{
					label: 'Getting started',
					items: [
						{ label: 'Quick Start', slug: 'index' },
						{ label: '/gaia-init', slug: 'getting-started/gaia-init' },
						{ label: '/setup-gaia-ci', slug: 'getting-started/setup-gaia-ci' },
						{ label: '/setup-gaia', slug: 'getting-started/setup-gaia' },
					],
				},
				{
					label: 'Commands',
					items: [
						{ label: 'Overview', slug: 'commands' },
						{ label: '/gaia plan', slug: 'commands/plan' },
						{ label: '/gaia spec', slug: 'commands/spec' },
						{ label: '/gaia handoff and pickup', slug: 'commands/handoff-pickup' },
						{ label: '/gaia audit', slug: 'commands/audit' },
						{ label: '/gaia forensics', slug: 'commands/forensics' },
						{ label: '/gaia wiki', slug: 'commands/wiki' },
						{ label: '/update-deps', slug: 'commands/update-deps' },
						{ label: '/update-gaia', slug: 'commands/update-gaia' },
					],
				},
				{
					label: 'Skills',
					items: [
						{ label: 'Overview', slug: 'skills' },
						{ label: 'Code skills', slug: 'skills/code' },
						{ label: 'Scaffolders', slug: 'skills/scaffolders' },
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
