# Packages UI Agent Guide

This file is the working contract for agents implementing the cross-platform Mercury-compatible front-end in `packages/ui`.

## 1. Mission

Build the UI for a Windows/Linux/macOS app that matches Mercury's feature surface, information architecture, and interaction behavior as closely as practical in a web/desktop front-end.

Mercury's SwiftUI implementation in `packages/ui/reference/mercury-ui` is the authoritative product reference. Treat it as source material for screens, behavior, copy, state transitions, and edge cases. Do not port Swift code directly unless the new stack explicitly supports that pattern; translate the behavior into the front-end architecture used in this package.

## 2. Communication and Documentation

- Communicate with the user in Chinese.
- Write code comments, repository documentation, commit messages, and test names in English unless the user explicitly asks for Chinese.
- Keep Markdown code references wrapped in backticks.
- Do not use emojis in code comments, documentation, or UI copy.

## 3. Platform and Scope

- Supported platforms: Windows, Linux, and macOS desktop.
- Do not add mobile-only flows, iOS assumptions, or SwiftUI/AppKit dependencies to this package.
- The front-end must live under `packages/ui` and must fit the repository's pnpm workspace/monorepo layout.
- Use platform-neutral UI behavior first. Platform-specific integrations must be isolated behind small adapters.
- If a native desktop shell is introduced, prefer a cross-platform shell such as Tauri/Electron with the UI still owned by this package.

## 4. Stack Rules

The stack may be scaffolded if it does not already exist. Prefer:

- Package manager: `pnpm`.
- Language: TypeScript.
- UI framework: React or another TypeScript-friendly framework already chosen in this workspace.
- Styling: a local design system with tokens/components; avoid one-off page-level styling.
- Icons: use the existing icon library if present; otherwise prefer `lucide-react`.
- Tests: unit tests for state/policy code and component tests for complex UI behavior. Use the package's existing test runner once it exists.

Before adding new dependencies, check `package.json`, workspace configuration, and existing package conventions. Add dependencies only when they reduce real implementation risk or match the chosen framework.

## 5. Product Reference Map

Use these Mercury files when implementing or reviewing parity:

| Area | Reference |
|---|---|
| App entry and shell | `reference/mercury-ui/App/MercuryApp.swift`, `reference/mercury-ui/App/Views/ContentView.swift` |
| App commands/status/feed actions | `reference/mercury-ui/App/Views/ContentView+*.swift` |
| Sidebar | `reference/mercury-ui/Feed/Views/SidebarView.swift` |
| Feed edit/import/export | `reference/mercury-ui/Feed/Views/FeedEditorSheet.swift`, `reference/mercury-ui/Feed/Views/ImportOPMLSheet.swift`, `reference/mercury-ui/Feed/AppModel+ImportExport.swift` |
| Entry list | `reference/mercury-ui/Feed/Views/EntryListView.swift` |
| Reader detail | `reference/mercury-ui/Reader/Views/ReaderDetailView.swift`, `reference/mercury-ui/Reader/Views/ReaderDetailView+Toolbar.swift` |
| Reader modes and web view | `reference/mercury-ui/Reader/Views/ReadingMode.swift`, `reference/mercury-ui/Reader/Views/WebView.swift` |
| Summary | `reference/mercury-ui/Reader/Views/ReaderSummaryView*.swift`, `reference/mercury-ui/Agent/Summary/*.swift` |
| Translation | `reference/mercury-ui/Reader/Views/ReaderTranslationView*.swift`, `reference/mercury-ui/Agent/Translation/*.swift` |
| Reader tags | `reference/mercury-ui/Reader/Views/ReaderTaggingPanelView.swift`, `reference/mercury-ui/Tags/*.swift` |
| Reader notes | `reference/mercury-ui/Digest/Views/ReaderNotePanelView.swift`, `reference/mercury-ui/Digest/Views/EntryNoteEditorView.swift` |
| Reader theme | `reference/mercury-ui/Reader/Views/ReaderThemePanelView.swift`, `reference/mercury-ui/Reader/Theme/ReaderTheme.swift` |
| Digest/export | `reference/mercury-ui/Digest/Views/*Digest*.swift`, `reference/mercury-ui/Digest/Shared/*.swift` |
| Settings | `reference/mercury-ui/App/Views/AppSettingsView.swift`, `reference/mercury-ui/Reader/Views/ReaderSettingsView.swift`, `reference/mercury-ui/Agent/Settings/*.swift` |
| Batch tagging and tag library | `reference/mercury-ui/App/Views/BatchTaggingSheetView*.swift`, `reference/mercury-ui/App/Views/TagLibrary*.swift`, `reference/mercury-ui/App/Views/TagRenameSheetView.swift` |
| Usage reports | `reference/mercury-ui/Usage/**/*.swift` |
| Localization | `reference/mercury-ui/Localizable.xcstrings` |

If screenshots are added later, keep them under `packages/ui/reference/screenshots` and use them for visual validation. Do not assume a `/screenshots` folder exists at the repository root.

## 6. Required App Surface

Implement the product as an actual app screen, not a landing page.

The primary layout is a three-pane desktop reader:

1. Sidebar for Feeds/Tags.
2. Entry list.
3. Reader detail.

Required top-level surfaces:

- Global search with feed-scoped search behavior.
- Sidebar with Feeds/Tags segmented switch.
- Entry list with unread filtering, batch actions, pagination, and selection.
- Reader detail with Reader/Web/Dual modes.
- Reader toolbar panels for tags, notes, theme, translation, and sharing/export.
- Collapsible summary panel with persisted height.
- Digest share/export flows, including multi-entry export.
- Settings tabs: General, Reader, Agents, Digest.
- Batch tagging modal and tag library modal.
- Usage report and comparison screens.

## 7. Behavioral Contracts

Preserve these Mercury behaviors unless the user explicitly approves a change:

- Selecting a feed or virtual row updates entry scope and can auto-select the first entry.
- `All Feeds` and `Starred` are virtual sidebar rows.
- Unread-only filtering affects list query, batch actions, and first-entry selection.
- Batch read-state actions are query-scoped by feed scope, unread filter, and search filter; they are not page-scoped.
- Search targets entry title and summary by default.
- Feed switch or unread-filter toggle clears pinned unread-entry keep behavior; non-empty search disables keep injection.
- List rows use lightweight entry data; full entry data is detail-only.
- Entry list pagination exposes an explicit load-more footer.
- Reader modes are `Reader`, `Web`, and `Dual`.
- Translation is reader-only in v1 and follows the active reading mode.
- Clear translation is available when cached translated content exists.
- Summary generation remains serialized; auto-summary is confirm-on-enable with a debounce and no automatic retry.
- Summary panel expand/collapse state and height are persisted.
- Note editor auto-saves on entry switch and app/background lifecycle.
- Tag suggestions merge local/NLP and AI suggestions with caps.
- Tags panel, note panel, theme panel, and toolbar popovers use floating panel styling.
- Batch tagging and tag library are modal flows, not reader banners.
- Batch tagging uses its own fixed message area for notices/failures.
- Entry-bound summary, translation, and single-entry tagging notifications may surface in the reader area.

## 8. Screen Details

### Sidebar

- Segmented control: Feeds / Tags.
- Feeds view: `All Feeds`, `Starred`, per-feed rows, unread counts, add feed, import OPML, sync, export OPML.
- Tags view: tag search, Any/All match mode, multi-select with selection cap, rename/delete actions.
- Feed/tag operations should expose loading, empty, and error states.

### Entry List

- Header title changes by scope, including `Entries` and `Starred`.
- Controls: unread-only toggle and batch menu.
- Batch menu: mark read, mark unread, delete, export multiple digest.
- Rows: unread indicator, title, optional feed source, metadata line, selected state.
- Footer: load-more state, disabled/loading state, and end-of-list state.

### Reader Detail

- Empty state when no entry is selected.
- Entry header with title, source metadata, tag chips, and related entries toggle.
- Related entries strip as horizontal cards.
- Reader mode renders cleaned reader HTML.
- Web mode renders original URL with URL/navigation chrome.
- Dual mode renders reader and web panes side by side.
- Toolbar actions: mode switch, translation toggle/clear, tags panel, note panel, theme panel, share/export menu.

### Reader Panels

- Tags panel: inline tag editor, current tags, suggestions, apply/remove states.
- Note panel: Markdown editor, auto-save status, dirty/saving/saved/error states.
- Theme panel: quick theme choices, font family, font size, line height, content width, live preview where applicable.
- Summary panel: collapsed/expanded states, resizable height, loading/error/empty/success states.

### Digest and Export

- Single-entry share digest.
- Single-entry export digest.
- Multi-entry export from the entry-list batch flow.
- Export flows need template/options state, preview where practical, success/failure feedback, and cancellation.

### Settings

- General: language, sync concurrency, usage retention, tag system controls.
- Reader: theme, typography, live preview.
- Agents: provider/model/agent configuration, availability status, route/fallback settings.
- Digest: template and export options.

### Tag System

- Batch tagging: multi-step modal with configuration, run status, review, and apply.
- Tag library: split view with tag list and inspector.
- Tag rename/merge/aliases must preserve validation and conflict states.

### Usage Reports

- Overview report.
- Provider, model, and agent usage reports.
- Comparison reports by provider/model/agent.
- Empty, loading, and no-data states.

## 9. Localization

- All user-facing strings must be localizable.
- Required locales: English and Simplified Chinese (`zh-Hans`).
- Use stable message keys instead of hard-coded UI strings.
- Use `reference/mercury-ui/Localizable.xcstrings` to understand existing copy and terminology.
- Do not localize debug-only developer diagnostics unless they are shown to users.

## 10. Design and Accessibility

- Preserve Mercury's dense desktop-reader layout: restrained, information-rich, and optimized for repeated reading workflows.
- Do not build a marketing hero page or decorative dashboard as the first screen.
- Use icons for common toolbar actions and add accessible labels/tooltips.
- Keep page sections unframed; use cards only for repeated items, modals, panels, and genuinely framed tools.
- Avoid nested cards.
- Use stable dimensions for split panes, rows, toolbar buttons, and controls so state changes do not shift layout unexpectedly.
- Ensure text does not overlap or overflow on narrow desktop windows.
- Support keyboard navigation for selection, list movement, search, modal close, and common toolbar actions.
- Maintain sufficient contrast in all themes.

## 11. State and Architecture

- Keep UI state, domain state, persistence, and service adapters separated.
- Model Mercury concepts explicitly: feed scope, tag scope, entry query, selected entry, reader mode, task/run status, digest options, usage filters.
- Prefer shared policy/state helpers for behavior that appears in multiple screens.
- Do not duplicate task lifecycle, prompt fallback, message projection, or export policy logic in individual components.
- Long-running operations must have explicit states: idle, queued/running, success, failure, cancelled when applicable.
- Agent/runtime work should expose user-facing status through approved UI surfaces, not ad-hoc alerts scattered across components.

## 12. Validation

Run validation from the repository root unless package scripts require otherwise.

Expected checks once the package is scaffolded:

```shell
pnpm install
pnpm --filter ui lint
pnpm --filter ui typecheck
pnpm --filter ui test
pnpm --filter ui build
```

If script names differ, use the closest package-defined equivalents and document the difference in your final response. Keep validation output free of errors and avoid introducing warnings.

For UI work, verify:

- Three-pane layout at desktop widths.
- Narrow desktop/window behavior.
- Reader/Web/Dual modes.
- Modal and panel open/close behavior.
- Localization switching for English and Simplified Chinese.
- Empty/loading/error states for each major surface.

## 13. Definition of Done

A task is not done until:

- The implemented screen or behavior is traceable to the Mercury reference file(s).
- User-facing strings are localizable.
- Loading, empty, error, and disabled states are handled where relevant.
- Cross-platform assumptions are documented or isolated behind adapters.
- Tests or focused manual validation cover the changed behavior.
- `plan.md` is updated when the task changes milestone status or scope.
