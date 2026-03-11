---
name: feishu-creator-doc-workflow
description: Use the feishu-creator MCP to create, inspect, update, replace, and verify Feishu documents and wiki notes with stable heading- and section-level workflows. Use when Codex needs to choose the right feishu-creator operation, locate headings or blocks, replace stale content in place, avoid duplicate sections, or confirm that an edit landed in the intended position.
---

# Feishu Creator Document Workflow

Use this skill when the hard part is operating `feishu-creator` safely rather than writing the content itself. Prefer heading- and section-level tools over guessed indices, and verify every structural edit after it lands.

## Workflow

1. Resolve the target first.
- Existing page: start with `get_feishu_document_info`.
- Unknown page: use `search_feishu_documents`, `list_feishu_wiki_spaces`, or `get_feishu_wiki_tree`.
- New page: use `create_feishu_document`.
- In this repo's wiki-first setup, new pages normally need `wikiContext.spaceId`; use `folderToken` only for Drive-folder compatibility.
- Do not use immediate search misses as proof that a fresh create or delete failed.

2. Inspect before mutating.
- If parent block, heading position, or section boundary is unclear, call `get_feishu_document_blocks`.
- For heading-scoped work, prefer `locate_section_range` or heading-based tools over guessed indices.
- Use `headingPath` or `sectionOccurrence` when headings may collide.
- Preview complex `copy_section` / `move_section` changes first, especially across documents or when images may be present.

3. Choose the highest-level edit primitive that fits.
- New structured content: `generate_section_blocks` or `generate_rich_text_blocks`.
- Replace an existing section: `replace_section_blocks` or `replace_section_with_ordered_list`.
- Insert before a heading: `insert_before_heading`.
- Update known text blocks directly only when block IDs are already known.
- Delete by semantic target before considering raw index deletion.

4. Default to in-place edits.
- Replace stale content instead of appending a second version nearby.
- Append only when the user wants additive content.
- Treat trailing non-heading blocks under the same parent as part of the current section until the next heading.

5. Verify after structural edits.
- Re-read the affected area with `get_feishu_document_blocks`.
- Confirm the new content landed under the intended parent block or heading.
- Check for duplicate sections, stray list blocks, or misplaced content.
- For whole-doc deletion, prefer `get_feishu_document_info` or `get_feishu_wiki_tree`.
- Treat Feishu `code=1770003` / `resource deleted` as delete confirmation.
- If service code changed in the same task, restart the MCP server or validate through the local service layer before trusting the result.

6. Handle whiteboards conservatively.
- Recreate the whiteboard at the same position instead of patching the old block in place.
- If a safe whiteboard workflow is unavailable, stop and tell the user.

## References

- Read [references/operation-recipes.md](references/operation-recipes.md) for a concise tool-by-task mapping.
- Read [references/whiteboard-mermaid-patterns.md](references/whiteboard-mermaid-patterns.md) only when the task explicitly involves whiteboard diagrams.
