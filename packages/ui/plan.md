# UI Implementation Plan

This plan tracks the front-end implementation in `packages/ui`. The product target is a Windows/Linux/macOS desktop UI with Mercury-compatible screens and behavior. Use `AGENT.md` as the implementation contract and `reference/mercury-ui` as the product reference.

## Phase 0: Workspace Foundation

- [x] Confirm or create the pnpm workspace package at `packages/ui`.
- [x] Choose and document the UI stack, desktop shell strategy, test runner, and styling approach.
- [x] Add package scripts for `dev`, `lint`, `typecheck`, `test`, and `build`.
- [x] Establish source structure for app shell, features, shared components, services, state, styles, tests, and localization.
- [x] Add shared design tokens for spacing, typography, colors, split panes, toolbar controls, panels, and modals.
- [x] Add local sample data/fixtures for feeds, entries, tags, notes, summaries, translation status, digest exports, and usage reports.

## Phase 1: App Shell and Navigation

- [x] Implement the three-pane shell: Sidebar -> Entry List -> Reader Detail.
- [x] Add resizable/persisted pane widths with sane minimums for desktop windows.
- [x] Add global toolbar search with feed-scoped search semantics.
- [x] Add selection state for feed scope, tag scope, entry query, selected entry, unread filter, and reader mode.
- [x] Implement empty/loading/error states for the shell.
- [x] Add keyboard navigation for search, list movement, entry selection, and modal/panel close.

Reference:

- `reference/mercury-ui/App/Views/ContentView.swift`
- `reference/mercury-ui/App/Views/ContentView+*.swift`
- `reference/mercury-ui/App/MercuryApp.swift`

## Phase 2: Sidebar

- [x] Implement Feeds/Tags segmented switch.
- [x] Implement Feeds view with `All Feeds`, `Starred`, per-feed rows, unread counts, and selected state.
- [x] Implement feed actions: add feed, edit feed, delete feed, import OPML, export OPML, sync.
- [x] Implement Tags view with search, Any/All match mode, multi-select, selection cap, and selected state.
- [x] Implement tag actions: rename, delete, validation, conflict feedback.
- [x] Add loading, empty, and error states for feeds/tags.

Reference:

- `reference/mercury-ui/Feed/Views/SidebarView.swift`
- `reference/mercury-ui/Feed/Views/FeedEditorSheet.swift`
- `reference/mercury-ui/Feed/Views/ImportOPMLSheet.swift`
- `reference/mercury-ui/Feed/AppModel+ImportExport.swift`

## Phase 3: Entry List

- [x] Implement scope-aware header titles, including `Entries` and `Starred`.
- [x] Implement unread-only toggle and query-scoped filtering.
- [x] Implement batch menu: mark read, mark unread, delete, export multiple digest.
- [x] Preserve Mercury's query-scoped batch read-state behavior.
- [x] Implement entry rows with unread indicator, title, optional feed source, metadata line, and selected state.
- [x] Implement pagination with an explicit load-more footer.
- [x] Add list loading, empty, error, disabled, and end-of-list states.

Reference:

- `reference/mercury-ui/Feed/Views/EntryListView.swift`
- `reference/mercury-ui/Feed/MarkReadPolicy.swift`
- `reference/mercury-ui/Core/Database/EntryQueryBuilder.swift`

## Phase 4: Reader Detail

- [x] Implement no-selection empty state.
- [x] Implement entry header with metadata, tag chips, and related entries toggle.
- [x] Implement horizontal related entries strip.
- [x] Implement Reader/Web/Dual reading modes.
- [x] Implement reader HTML surface and web URL/navigation chrome.
- [x] Implement toolbar actions: reading mode switch, translation toggle/clear, tags panel, note panel, theme panel, share/export menu.
- [x] Ensure mode changes preserve selection and panel state correctly.

Reference:

- `reference/mercury-ui/Reader/Views/ReaderDetailView.swift`
- `reference/mercury-ui/Reader/Views/ReaderDetailView+Toolbar.swift`
- `reference/mercury-ui/Reader/Views/ReadingMode.swift`
- `reference/mercury-ui/Reader/Views/WebView.swift`
- `reference/mercury-ui/Reader/Views/ReaderRelatedEntriesView.swift`

## Phase 5: Reader Panels and Agent Workflows

- [x] Implement tags panel with current tags, inline editor, suggestions, apply/remove states.
- [x] Implement note panel with Markdown editing and auto-save states.
- [x] Implement theme panel with quick themes, font family, font size, line height, content width, and preview behavior.
- [x] Implement summary panel with collapsed/expanded states, persisted height, loading/error/success states, and auto-summary behavior.
- [x] Implement translation runtime UI state: start/running/succeeded/failed, cached translation, clear translation, and reader-only mode behavior.
- [x] Route entry-bound summary, translation, and single-entry tagging notices to the reader surface.

Reference:

- `reference/mercury-ui/Reader/Views/ReaderTaggingPanelView.swift`
- `reference/mercury-ui/Digest/Views/ReaderNotePanelView.swift`
- `reference/mercury-ui/Digest/Views/EntryNoteEditorView.swift`
- `reference/mercury-ui/Reader/Views/ReaderThemePanelView.swift`
- `reference/mercury-ui/Reader/Views/ReaderSummaryView*.swift`
- `reference/mercury-ui/Reader/Views/ReaderTranslationView*.swift`
- `reference/mercury-ui/Agent/Summary/*.swift`
- `reference/mercury-ui/Agent/Translation/*.swift`

## Phase 6: Digest and Export

- [x] Implement single-entry share digest flow.
- [x] Implement single-entry export digest flow.
- [x] Implement multi-entry digest export from the entry-list batch menu.
- [x] Add template/options state, preview where practical, cancellation, success feedback, and failure feedback.
- [x] Preserve separation between digest composition policy and view components.

Reference:

- `reference/mercury-ui/Digest/Views/ReaderShareDigestSheetView.swift`
- `reference/mercury-ui/Digest/Views/ReaderExportDigestSheetView.swift`
- `reference/mercury-ui/Digest/Views/ExportMultipleDigestSheetView.swift`
- `reference/mercury-ui/Digest/Shared/*.swift`

## Phase 7: Settings

- [x] Implement tabbed settings: General, Reader, Agents, Digest.
- [x] General: language, sync concurrency, usage retention, tag system controls.
- [x] Reader: theme, typography, live preview.
- [x] Agents: provider, model, agent configuration, availability, route/fallback settings.
- [x] Digest: templates and export options.
- [x] Add validation and disabled/error states for provider/model configuration.

Reference:

- `reference/mercury-ui/App/Views/AppSettingsView.swift`
- `reference/mercury-ui/Reader/Views/ReaderSettingsView.swift`
- `reference/mercury-ui/Agent/Settings/*.swift`

## Phase 8: Tag System Management

- [x] Implement Batch Tagging modal with setup, run status, review, and apply steps.
- [x] Implement sheet-local notices/failures for Batch Tagging.
- [x] Implement Tag Library modal with split list/inspector layout.
- [x] Implement rename, merge, aliases, validation, and conflict states.
- [x] Ensure batch/tag-library flows do not use reader banners.

Reference:

- `reference/mercury-ui/App/Views/BatchTaggingSheetView*.swift`
- `reference/mercury-ui/App/Views/TagLibrary*.swift`
- `reference/mercury-ui/App/Views/TagRenameSheetView.swift`
- `reference/mercury-ui/Tags/*.swift`

## Phase 9: Usage Reports

- [x] Implement usage overview dashboard.
- [x] Implement provider usage report and comparison report.
- [x] Implement model usage report and comparison report.
- [x] Implement agent usage report and comparison report.
- [x] Add filters, empty/no-data states, loading states, and export/copy affordances if supported by the reference behavior.

Reference:

- `reference/mercury-ui/Usage/**/*.swift`

## Phase 10: Localization, Accessibility, and Parity Review

- [x] Add localization infrastructure for English and Simplified Chinese.
- [x] Replace hard-coded user-facing strings with localization keys.
- [x] Compare terminology against `reference/mercury-ui/Localizable.xcstrings`.
- [x] Verify keyboard navigation across shell, lists, panels, modals, and settings.
- [x] Verify focus management and accessible names for icon buttons and toolbar controls.
- [x] Verify contrast and layout in all reader themes.
- [x] Perform a parity review against the reference files for all required screens.

## Validation Checklist

Run these from the repository root once scripts exist:

```shell
pnpm install
pnpm --filter ui lint
pnpm --filter ui typecheck
pnpm --filter ui test
pnpm --filter ui build
```

Manual validation should cover:

- [x] Desktop three-pane layout at normal and narrow window sizes.
- [x] Feed and tag scope switching.
- [x] Search, unread filter, auto-selection, pagination, and batch actions.
- [x] Reader/Web/Dual mode switching.
- [x] Tags, notes, theme, summary, translation, and share/export panels.
- [x] Settings tabs.
- [x] Batch tagging and tag library modals.
- [x] Usage report screens.
- [x] English and Simplified Chinese UI.
