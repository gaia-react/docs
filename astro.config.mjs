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
			components: {
				Header: './src/overrides/Header.astro',
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
						{ label: '/gaia-init walkthrough', slug: 'getting-started/gaia-init' },
						{ label: '/setup-gaia walkthrough', slug: 'getting-started/setup-gaia' },
					],
				},
				{
					label: 'Commands',
					items: [{ label: 'Overview', slug: 'commands' }],
				},
				{
					label: '/gaia',
					items: [
						{ label: 'Overview', slug: 'gaia' },
						{ label: '/gaia plan', slug: 'gaia/plan' },
						{ label: '/gaia spec', slug: 'gaia/spec' },
						{ label: '/gaia audit', slug: 'gaia/audit' },
						{ label: '/gaia handoff and pickup', slug: 'gaia/handoff-pickup' },
						{ label: '/gaia forensics', slug: 'gaia/forensics' },
						{ label: '/gaia wiki', slug: 'gaia/wiki' },
					],
				},
				{
					label: 'Skills',
					items: [
						{ label: 'Overview', slug: 'skills' },
						{ label: 'Code skills', slug: 'skills/code' },
						{ label: 'Scaffolders', slug: 'skills/scaffolders' },
						{ label: 'Maintenance', slug: 'skills/maintenance' },
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
						{ label: 'Release', slug: 'contributors/release' },
						{ label: 'Health audit', slug: 'contributors/health-audit' },
						{ label: 'CLI surface', slug: 'contributors/cli' },
						{ label: 'CI workflows', slug: 'contributors/ci' },
						{ label: 'Wiki internals', slug: 'contributors/wiki' },
					],
				},
			],
		}),
	],
});
