---
title: Quick Start
layout: default
nav_order: 2
has_children: true
---

# Quick Start

Getting started with GAIA is easy. This guide will help you get up and running quickly.

## Installation

Make sure you have [Node.js](https://nodejs.org/en/) >=20.17.0 LTS installed, preferably via [nvm](https://github.com/nvm-sh/nvm).

All you need to do is run this installation command and follow the prompts.


```sh
npx create-remix@latest --template gaia-react/remix
```

### Install packages

```sh
npm install
```

### Setup Fix on Save in your IDE

Follow these [instructions](/docs/tech-stack/code-quality/#setup-fix-on-save).

## Development

Duplicate the `.env.example` file and name it `.env` (if you skipped this step during installation).

### Storybook

```sh
npm run storybook
```

### Remix

```sh
npm run dev
```

### Styling

This template comes with [Tailwind CSS](https://tailwindcss.com/) configured, with some configuration and utilities, which you can change to suit your project.

See the [Vite docs on css](https://vitejs.dev/guide/features.html#css) for more information.

### Icons

[FontAwesome](https://fontawesome.com/) is included. You're free to change it if you like.

### i18n

[Remix-i18next](https://github.com/sergiodxa/remix-i18next) is configured with examples.

Storybook is already configured with react-i18n support.

## Testing

GAIA comes with a full testing suite already configured.

### Unit and Integration

- [vitest](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)

```sh
  npm t
  // or
  npm run test
```

### Visual Regression

[Chromatic](https://chromatic.com)

You'll need to set your `CHROMATIC_PROJECT_TOKEN` env variable on your CI.

### E2E

[PlayWright](https://playwright.dev/docs/intro)

```sh
npx playwright test
```

Interactive mode:

```sh
npx playwright test --ui
```

## Deployment

GAIA comes with the default Remix deployment configuration. You can change this to whatever deployment process you prefer.

Here's the basic Remix deployment process:

```sh
npm run build
```

Then run the app in production mode:

```sh
npm start
```

You'll need to pick a host to deploy it to. Jacob Paris wrote a [great article](https://www.jacobparis.com/content/where-to-host-remix) on where to host your Remix app.

### DIY

If you're familiar with deploying Node applications, the built-in Remix app server is production-ready.

Make sure to deploy the output of `npm run build`

- `build/server`
- `build/client`
