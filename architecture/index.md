---
title: Architecture
layout: default
nav_order: 4
has_children: true
---

# Architecture

GAIA's architecture is designed to be easy to maintain, extend, and understand.

Inside the `app` folder, you will find the following structure:

- `assets`
- `components`
- `hooks`
- `language`
- `pages`
- `routes`
- `services`
- `sessions.server`
- `state`
- `styles`
- `types`
- `utils`
- `validators`

Along with the following files

- `entry.client.tsx` and `entry.server.tsx` are required for Remix. They have everything set up for i18n, environment variables, and MSW.
- `root.tsx` - is required by Remix.
- `env.server.ts` - Zod schemas for environment variables.
- `i18n.ts` and `i18next.server.ts` - i18n setup files.
