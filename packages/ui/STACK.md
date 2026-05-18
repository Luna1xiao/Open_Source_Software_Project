# UI Stack

The `ui` package implements a Mercury-compatible desktop reader surface with:

- Package manager: pnpm workspace package under `packages/ui`.
- Language: TypeScript.
- UI framework: React with Vite.
- Desktop shell strategy: web-first package, ready to be hosted by a cross-platform shell such as Tauri or Electron. Platform-specific shell hooks should live behind adapters in `src/services`.
- Styling: local CSS design tokens in `src/styles/tokens.css` plus app styles in `src/styles/app.css`.
- Icons: `lucide-react`.
- Tests: Vitest for state and policy helpers, with component tests available through Testing Library.

The package currently uses local fixtures and browser storage adapters so the complete UI can be run and validated before native data stores or desktop shell integration are introduced.
