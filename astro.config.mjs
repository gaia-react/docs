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
			sidebar: [
				{
					label: 'Getting started',
					items: [
						{ label: 'Quick Start', slug: 'index' },
						{ label: '/gaia-init', slug: 'getting-started/gaia-init' },
						{ label: '/setup-gaia-ci', slug: 'getting-started/setup-gaia-ci' },
						{ label: '/setup-cloned-gaia-project', slug: 'getting-started/setup-cloned-gaia-project' },
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
