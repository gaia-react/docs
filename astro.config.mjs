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
					label: 'Start here',
					items: [{ label: 'Introduction', slug: 'index' }],
				},
			],
		}),
	],
});
