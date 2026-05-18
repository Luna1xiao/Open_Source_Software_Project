import type { DigestTemplate, Entry, Tag } from "./types";

export function composeDigest(entries: Entry[], tags: Tag[], template: DigestTemplate): string {
  const tagById = new Map(tags.map((tag) => [tag.id, tag.name]));
  return entries
    .map((entry) => {
      const parts = [`# ${entry.title}`, entry.url, "", entry.summary];
      if (template.includeSummary && entry.summaryText) {
        parts.push("", "## Summary", entry.summaryText);
      }
      if (template.includeNotes && entry.note) {
        parts.push("", "## Note", entry.note);
      }
      if (template.includeTags && entry.tagIds.length > 0) {
        parts.push("", `Tags: ${entry.tagIds.map((id) => tagById.get(id) ?? id).join(", ")}`);
      }
      return parts.join("\n");
    })
    .join("\n\n---\n\n");
}
