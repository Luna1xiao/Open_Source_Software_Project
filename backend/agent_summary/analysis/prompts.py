"""Prompt 模板"""

PROMPT_VERSION = "v1"

SUMMARY_PROMPTS = {
    "direct": "请用 2-3 句话总结以下内容：\n\n{content}",
    "key_points": "请从以下新闻中提取 3-5 个关键点：\n\n{content}",
    "hierarchical": "请总结以下段落的要点：\n\n{content}",
    "merge": "请将以下各段摘要合并为一篇连贯的总结：\n\n{chunk_summaries}",
    "context_enhanced": "基于以下背景信息，总结文章内容：\n\n背景：{context}\n\n文章：{content}",
}
