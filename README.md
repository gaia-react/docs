# GAIA Docs

Documentation site for [GAIA](https://github.com/gaia-react/gaia), served at [docs.gaiareact.com](https://docs.gaiareact.com).

Built with [Starlight](https://starlight.astro.build) on Astro. Deployed to GitHub Pages on every push to `main`.

## Local development

```sh
npm install
npm run dev      # localhost:4321
npm run build    # production build → ./dist
npm run preview  # preview the build
```

## Structure

- `src/content/docs/` — Markdown/MDX content. Each file becomes a route.
- `src/assets/` — images embedded in content.
- `public/` — static assets (favicon, `CNAME`, etc.).
- `astro.config.mjs` — site config, sidebar, Starlight options.

## Deploy

Pushes to `main` trigger `.github/workflows/deploy.yml`. PRs build but do not deploy.
