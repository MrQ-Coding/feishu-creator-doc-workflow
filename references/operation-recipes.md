# Feishu Creator Operation Recipes

## 1. Target

- Confirm an existing doc or wiki node: `get_feishu_document_info`
- Search by keyword: `search_feishu_documents`
- Browse spaces: `list_feishu_wiki_spaces`
- Traverse a wiki tree: `get_feishu_wiki_tree`
- Create a new page: `create_feishu_document`
- Fresh create or delete verification: prefer `get_feishu_document_info` or `get_feishu_wiki_tree`, not search.
- New wiki pages usually need `wikiContext.spaceId`; use `folderToken` only for Drive-folder compatibility.

## 2. Inspect

- Full block tree or parent context: `get_feishu_document_blocks`
- One heading range: `locate_section_range`
- Use before editing whenever heading position, parent block, block ID, or section boundary is unclear.

## 3. Write Or Replace

- New structured section: `generate_section_blocks`
- Mixed heading/text/list/code blocks: `generate_rich_text_blocks`
- Replace one section by heading: `replace_section_blocks`
- Replace one section with native ordered blocks: `replace_section_with_ordered_list`
- Insert before a heading: `insert_before_heading`
- Update known text blocks: `update_feishu_block_text`, `batch_update_feishu_blocks`
- Prefer section-level tools over low-level block editing.

## 4. Transfer Or Delete

- Preview complex transfers first: `preview_edit_plan`
- Copy or move a section: `copy_section`, `move_section`
- Delete a semantic section: `delete_by_heading`
- Delete a raw block range: `delete_feishu_document_blocks`
- Delete whole docs or wiki nodes: `delete_feishu_document`, `batch_delete_feishu_documents`
- Raw index deletion only when heading-based tools do not fit and the exact range is already known.
- Before `copy_section` or `move_section`, inspect the boundary if the heading is near the end of its parent.
- Trailing non-heading blocks, including images, still belong to that section until the next heading.
- If images are present, preview first; copied images get rebuilt with new file tokens and may run slower than text-only transfers.

## 5. Verification

After `replace`, `insert`, `delete`, `copy`, `move`, or large `generate` calls:

1. Re-read the affected area with `get_feishu_document_blocks`.
2. Confirm the heading order and parent block are still correct.
3. Confirm no duplicate section or stray list remains nearby.
4. For copy or move, confirm images and other non-text blocks landed in the intended order.
5. For whole-doc deletion, prefer `get_feishu_document_info` or `get_feishu_wiki_tree`.
6. Treat Feishu `code=1770003` or `resource deleted` as successful delete confirmation.
7. When validating fresh code changes, restart the MCP server first or call the local service directly.
