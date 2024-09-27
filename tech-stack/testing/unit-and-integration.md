---
title: Unit & Integration
layout: default
parent: Testing
nav_order: 1
has_children: false
---

# Vitest + React Testing Library

For unit and integration testing, GAIA comes with [vitest](https://vitest.dev/) and [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/).

## Configuration

Vitest is configured in the `vitest.config.js` file in the root of the project. You can add custom configurations to this file.

Vitest is configured to look for tests anywhere in the `app` folder, following the `*.test.{ts,tsx}` pattern.

In the `test` folder, you will find all the setup files for vitest, React Testing Library, and MSW.

## MSW - Mock Service Worker

GAIA comes with [MSW](https://mswjs.io/), which allows you to mock your API requests in your tests.

It also includes [@mswjs/data](https://github.com/mswjs/data#readme) which allows you to create interactive mocks for the data in your tests.


## test folder

The test folder contains the setup, configuration, and mocks for tests.

- `handlers` contains the MSW handlers for the API requests.
- `mocks` contains the data mocks for tests
- `stubs` contains storybook stubs
- `msw.server.ts` - This is used by Remix's `entry.server.tsx` file to optionally use the MSW server in non-production environments when the environment variable `MSW_ENABLED=true`.
- `rtl.tsx` - This sets up the React Testing Library to cleanup after each test and include the i18n strings.
- `setup.ts` - This is the vitest setup file
- `test.server.ts` - This is the MSW setup file when running in vitest
- `worker.ts` - This is the MSW setup file for the service worker that includes handlers
