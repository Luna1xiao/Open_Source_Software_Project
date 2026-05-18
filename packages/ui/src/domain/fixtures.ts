import type { DigestTemplate, Entry, Feed, Tag, UsageReport } from "./types";

export const feeds: Feed[] = [
  {
    id: "hn",
    title: "Hacker News",
    siteUrl: "https://news.ycombinator.com",
    feedUrl: "https://hnrss.org/frontpage",
    unreadCount: 8,
    status: "success"
  },
  {
    id: "swift",
    title: "Swift Evolution",
    siteUrl: "https://swift.org",
    feedUrl: "https://swift.org/blog/feed.xml",
    unreadCount: 3,
    status: "success"
  },
  {
    id: "design",
    title: "Design Systems Weekly",
    siteUrl: "https://example.com/design",
    feedUrl: "https://example.com/design/feed.xml",
    unreadCount: 5,
    status: "running"
  }
];

export const tags: Tag[] = [
  { id: "ai", name: "AI", aliases: ["llm", "agents"], usageCount: 12, unreadCount: 6 },
  { id: "ux", name: "UX", aliases: ["design"], usageCount: 9, unreadCount: 4 },
  { id: "swift", name: "Swift", aliases: ["apple"], usageCount: 7, unreadCount: 2 },
  { id: "infra", name: "Infrastructure", aliases: ["platform"], usageCount: 6, unreadCount: 1 },
  { id: "security", name: "Security", aliases: [], usageCount: 4, unreadCount: 1 }
];

export const entries: Entry[] = [
  {
    id: "e1",
    feedId: "hn",
    title: "A practical guide to serialized agent work queues",
    summary: "An engineering note on preventing duplicate model work while preserving visible progress.",
    author: "M. Chen",
    url: "https://example.com/agent-work-queues",
    publishedAt: "2026-05-15T03:12:00.000Z",
    isRead: false,
    isStarred: true,
    tagIds: ["ai", "infra"],
    readerHtml:
      "<h1>A practical guide to serialized agent work queues</h1><p>Serialized queues keep summary generation predictable, especially when users switch entries quickly.</p><p>The key is to separate request ownership, resumable cache state, and visible task phase.</p>",
    webPreview: "https://example.com/agent-work-queues",
    relatedEntryIds: ["e4", "e7"],
    note: "Check whether our summary panel should expose owner state.",
    summaryText: "Serialized queues reduce duplicated model work and make cancellation easier to reason about.",
    translationHtml:
      "<h1>序列化智能体工作队列实践指南</h1><p>序列化队列让摘要生成更可预测，尤其是在用户快速切换条目时。</p>",
    translationStatus: "success"
  },
  {
    id: "e2",
    feedId: "swift",
    title: "Reader mode rendering pipelines in desktop apps",
    summary: "A walkthrough of reader extraction, markdown conversion, and HTML theming.",
    author: "A. Rivera",
    url: "https://example.com/reader-pipelines",
    publishedAt: "2026-05-14T14:40:00.000Z",
    isRead: false,
    isStarred: false,
    tagIds: ["swift"],
    readerHtml:
      "<h1>Reader mode rendering pipelines in desktop apps</h1><p>A reader pipeline usually normalizes redirects, extracts readable content, and applies a stable theme.</p>",
    webPreview: "https://example.com/reader-pipelines",
    relatedEntryIds: ["e5"],
    note: "",
    summaryText: "",
    translationStatus: "idle"
  },
  {
    id: "e3",
    feedId: "design",
    title: "Dense layouts that still breathe",
    summary: "Patterns for three-pane tools that prioritize scanning, comparison, and repeated work.",
    author: "R. Lin",
    url: "https://example.com/dense-layouts",
    publishedAt: "2026-05-13T21:24:00.000Z",
    isRead: true,
    isStarred: false,
    tagIds: ["ux"],
    readerHtml:
      "<h1>Dense layouts that still breathe</h1><p>Desktop reader tools benefit from compact controls, stable row heights, and predictable split panes.</p>",
    webPreview: "https://example.com/dense-layouts",
    relatedEntryIds: ["e6"],
    note: "Good reference for split-pane minimums.",
    summaryText: "Stable dimensions and restrained visual hierarchy keep dense workflows comfortable.",
    translationStatus: "idle"
  },
  {
    id: "e4",
    feedId: "hn",
    title: "OPML import edge cases",
    summary: "How duplicate feeds, missing titles, and site-name fallbacks affect import flows.",
    author: "N. Patel",
    url: "https://example.com/opml-edge-cases",
    publishedAt: "2026-05-12T10:05:00.000Z",
    isRead: false,
    isStarred: false,
    tagIds: ["infra"],
    readerHtml:
      "<h1>OPML import edge cases</h1><p>Import flows need explicit replace behavior and clear feedback for feeds that cannot be verified.</p>",
    webPreview: "https://example.com/opml-edge-cases",
    relatedEntryIds: ["e1"],
    note: "",
    summaryText: "",
    translationStatus: "idle"
  },
  {
    id: "e5",
    feedId: "swift",
    title: "Translation slots and cached reader content",
    summary: "Reader-only translation can follow the active layout without mutating the original article.",
    author: "J. Park",
    url: "https://example.com/translation-slots",
    publishedAt: "2026-05-11T12:00:00.000Z",
    isRead: true,
    isStarred: true,
    tagIds: ["ai", "swift"],
    readerHtml:
      "<h1>Translation slots and cached reader content</h1><p>Translation slots should be keyed by entry, language, and mode so cached content can be cleared safely.</p>",
    webPreview: "https://example.com/translation-slots",
    relatedEntryIds: ["e2"],
    note: "",
    summaryText: "Translation remains reader-only and cache clearing should be explicit.",
    translationStatus: "success"
  },
  {
    id: "e6",
    feedId: "design",
    title: "Designing modal tag libraries",
    summary: "Split inspectors make rename, merge, aliases, and conflicts understandable.",
    author: "T. Wong",
    url: "https://example.com/tag-libraries",
    publishedAt: "2026-05-10T08:30:00.000Z",
    isRead: false,
    isStarred: false,
    tagIds: ["ux", "security"],
    readerHtml:
      "<h1>Designing modal tag libraries</h1><p>A modal tag library keeps global tag maintenance separate from entry-bound tagging work.</p>",
    webPreview: "https://example.com/tag-libraries",
    relatedEntryIds: ["e3"],
    note: "",
    summaryText: "",
    translationStatus: "idle"
  },
  {
    id: "e7",
    feedId: "hn",
    title: "Usage reports for provider routing",
    summary: "Provider, model, and agent comparisons reveal fallback quality and cost patterns.",
    author: "K. Smith",
    url: "https://example.com/usage-routing",
    publishedAt: "2026-05-09T18:10:00.000Z",
    isRead: false,
    isStarred: false,
    tagIds: ["ai"],
    readerHtml:
      "<h1>Usage reports for provider routing</h1><p>Comparison reports are most useful when they show requests, tokens, quality, and period-over-period deltas.</p>",
    webPreview: "https://example.com/usage-routing",
    relatedEntryIds: ["e1"],
    note: "",
    summaryText: "Usage reports should cover providers, models, agents, and comparisons.",
    translationStatus: "idle"
  }
];

export const digestTemplates: DigestTemplate[] = [
  { id: "share", title: "Share Digest", includeSummary: true, includeNotes: true, includeTags: true },
  { id: "export", title: "Export Digest", includeSummary: true, includeNotes: true, includeTags: true },
  { id: "multiple", title: "Export Multiple Digest", includeSummary: true, includeNotes: false, includeTags: true }
];

export const usageReports: UsageReport[] = [
  {
    id: "openai",
    title: "OpenAI",
    subtitle: "Provider usage",
    provider: "OpenAI",
    model: "gpt-5.2",
    agent: "Summary",
    buckets: [
      { day: "May 9", promptTokens: 1200, completionTokens: 900, requests: 8, failures: 0 },
      { day: "May 10", promptTokens: 1640, completionTokens: 1210, requests: 11, failures: 1 },
      { day: "May 11", promptTokens: 980, completionTokens: 740, requests: 6, failures: 0 },
      { day: "May 12", promptTokens: 2200, completionTokens: 1710, requests: 14, failures: 1 },
      { day: "May 13", promptTokens: 1920, completionTokens: 1500, requests: 12, failures: 0 },
      { day: "May 14", promptTokens: 2500, completionTokens: 1860, requests: 16, failures: 0 }
    ]
  }
];
