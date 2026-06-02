import type { components } from "@mercury/shared-types";

import type { Entry, Feed, Tag } from "../../domain/types";

export function toUiFeed(feed: components["schemas"]["Feed"]): Feed {
  return {
    id: feed.id,
    title: feed.title,
    siteUrl: feed.site_url,
    feedUrl: feed.feed_url,
    unreadCount: feed.unread_count,
    status: feed.status
  };
}

export function toUiTag(tag: components["schemas"]["Tag"]): Tag {
  return {
    id: tag.id,
    name: tag.name,
    aliases: tag.aliases,
    usageCount: tag.usage_count,
    unreadCount: tag.unread_count
  };
}

export function toUiEntry(entry: components["schemas"]["Entry"]): Entry {
  return {
    id: entry.id,
    feedId: entry.feed_id,
    title: entry.title,
    summary: entry.summary,
    author: entry.author,
    url: entry.url,
    publishedAt: entry.published_at,
    isRead: entry.is_read,
    isStarred: entry.is_starred,
    tagIds: entry.tag_ids,
    readerHtml: entry.reader_html,
    webPreview: entry.web_preview,
    relatedEntryIds: entry.related_entry_ids,
    note: entry.note,
    summaryText: entry.summary_text,
    translationHtml: entry.translation_html ?? undefined,
    translationStatus: entry.translation_status
  };
}
