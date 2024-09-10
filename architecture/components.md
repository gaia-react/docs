---
title: Components
layout: default
parent: Architecture
nav_order: 2
---

# Components folder

The components folder is for shared components that are used throughout the application.

GAIA uses the following structure for components folders:

- PascalCase for folder names
- `index.tsx` for the main component file
- `styles.module.css` for component styles 
- `types.ts` for component types (when necessary)
- `utils.ts` for component utility functions (when necessary)

Within a component folder, you can also add the following folders when necessary:

- `assets` - Component-specific assets
- `hooks` - Component-specific hooks go
- `state` - Component-specific state management (Context/Provider, for example)
- `tests` - Storybook stories and Vitest tests

Child components are placed in their own PascalCase folder inside their parent folder. A common practice in GAIA is to "lift" a child component only up to its highest level where it is shared.

This structure makes it easy to find and work with components, and to understand how they are used in the application. It also makes refactoring and moving components around easier and more predictable.

The naming conventions for component folders are enforced by ESLint, so components will always be consistent throughout the project.