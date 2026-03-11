---
name: feishu-creator-doc-workflow
description: Install, initialize, configure, and operate the feishu-creator MCP end-to-end. Use when the user asks to install `feishu-creator`, install or configure a Feishu helper (`飞书助手`), bootstrap feishu-creator in a local workspace, prepare .env/build/client config, or safely create, inspect, update, replace, and verify Feishu documents and wiki notes with stable heading- and section-level workflows.
---

# Feishu Creator Workflow

Use this skill when the task touches the `feishu-creator` lifecycle end-to-end: local bootstrap, MCP client wiring, or safe Feishu document operations. Default to doing as much setup work automatically as possible before asking the user for help.

## Workflow

1. Route by intent first.
- If the user wants to install `feishu-creator`, install or configure a Feishu helper (`飞书助手`), initialize, bootstrap, enable, or wire `feishu-creator` into an MCP client, start with the setup flow below.
- If the user wants to create, inspect, update, replace, move, copy, or verify Feishu docs after setup, use the document-operation flow below.
- If the user asks for both, finish setup first, then continue into document operations without waiting for a second prompt.

2. Setup and bootstrap flow.
- Resolve the repo root by finding `package.json` for `feishu-creator` plus `.env.example`. If the current workspace is already the repo, use it directly.
- Use the canonical project source directly when the repo is missing:
  - Repo page: `https://github.com/MrQ-Coding/feishu-creator`
  - Git clone: `https://github.com/MrQ-Coding/feishu-creator.git`
  - Zip fallback: `https://github.com/MrQ-Coding/feishu-creator/archive/refs/heads/main.zip`
- Do not start by searching GitHub, npm, or pip by keyword when these canonical URLs are available. Only search if the user explicitly wants an alternate fork/source, or the canonical source is unreachable.
- Start with a preflight check: confirm `node` and `npm` are available, prefer `git` for source retrieval and updates, and require Node `>= 20.17.0`.
- If `node` was just installed, refresh the shell PATH before retrying `node` or `npm`.
- If the repo is not present yet, prefer `git clone`; only fall back to a GitHub zip when clone is unavailable or blocked.
- Default to `MCP_MODE=auto` and `stdio`. Do not switch the long-term default to `http` unless the user explicitly wants that.
- Run [scripts/setup_feishu_creator.py](scripts/setup_feishu_creator.py) for local bootstrap.
- Let the script do the heavy lifting: install dependencies, prepare `.env` if missing, preserve existing values, build `dist/`, and write MCP config for detected clients.
- Prefer local or workspace-scoped client config when possible. In the current implementation:
  - Claude-compatible local config: `.mcp.json`
  - Cursor workspace config: `.cursor/mcp.json`
  - Gemini global config: `~/.gemini/antigravity/mcp_config.json`
  - MarsCode global config: `~/.marscode/Studio.mcp.config.json`
- Minimum expected env fields are `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, and `FEISHU_AUTH_TYPE`. Default `FEISHU_AUTH_TYPE=tenant` unless the user explicitly needs `user` mode.
- Do not stop just because Feishu credentials are missing. Finish the install/build/client-config work first, then report exactly which env fields still need user input.
- Return install/setup results in a fixed report shape: `安装结果` -> `环境` -> `仓库位置` -> `执行结果` -> `生成或更新的文件` -> `启动冒烟测试` -> `仍需手动填写` -> `下一步建议`.
- When `仍需手动填写` is not empty, include a short acquisition method for each missing field instead of only naming the field.
- After bootstrap, confirm `dist/index.js` exists and summarize which files were created or updated.
- When the user is explicitly validating install health or the setup path was flaky, run a startup smoke test with `node dist/index.js --stdio` before declaring the install healthy.
- If credentials exist, continue with `ping` -> `auth_status(fetchToken=true)` -> `get_feishu_document_info`.
- After writing MCP client config, remind the user to restart Codex or the target MCP client so the new server entry is reloaded.
- Treat search delay or permission errors as post-install runtime issues. Do not report dependency install, build, or client wiring as failed unless those steps themselves failed.
- If the user explicitly asks to configure a specific client, pass a targeted client list to the script instead of touching every detected client.

3. Resolve the Feishu target before content edits.
- Existing page: start with `get_feishu_document_info`.
- Unknown page: use `search_feishu_documents`, `list_feishu_wiki_spaces`, or `get_feishu_wiki_tree`.
- New page: use `create_feishu_document`.
- In this repo's wiki-first setup, new pages normally need `wikiContext.spaceId`; use `folderToken` only for Drive-folder compatibility.
- Do not use immediate search misses as proof that a fresh create or delete failed.

4. Inspect before mutating.
- If parent block, heading position, or section boundary is unclear, call `get_feishu_document_blocks`.
- For heading-scoped work, prefer `locate_section_range` or heading-based tools over guessed indices.
- Use `headingPath` or `sectionOccurrence` when headings may collide.
- Preview complex `copy_section` / `move_section` changes first, especially across documents or when images may be present.

5. Choose the highest-level edit primitive that fits.
- New structured content: `generate_section_blocks` or `generate_rich_text_blocks`.
- Replace an existing section: `replace_section_blocks` or `replace_section_with_ordered_list`.
- Insert before a heading: `insert_before_heading`.
- Update known text blocks directly only when block IDs are already known.
- Delete by semantic target before considering raw index deletion.

6. Default to in-place edits.
- Replace stale content instead of appending a second version nearby.
- Append only when the user wants additive content.
- Treat trailing non-heading blocks under the same parent as part of the current section until the next heading.

7. Verify after structural edits.
- Re-read the affected area with `get_feishu_document_blocks`.
- Confirm the new content landed under the intended parent block or heading.
- Check for duplicate sections, stray list blocks, or misplaced content.
- For whole-doc deletion, prefer `get_feishu_document_info` or `get_feishu_wiki_tree`.
- Treat Feishu `code=1770003` / `resource deleted` as delete confirmation.
- If service code changed in the same task, restart the MCP server or validate through the local service layer before trusting the result.

8. Handle whiteboards conservatively.
- Recreate the whiteboard at the same position instead of patching the old block in place.
- If a safe whiteboard workflow is unavailable, stop and tell the user.

## References

- Read [references/setup-recipes.md](references/setup-recipes.md) when the user asks to install, initialize, configure, or verify `feishu-creator` MCP locally.
- Read [references/install-report-template.md](references/install-report-template.md) when you need to present setup/install results in a stable, user-facing format.
- Read [references/operation-recipes.md](references/operation-recipes.md) for a concise tool-by-task mapping.
- Read [references/whiteboard-mermaid-patterns.md](references/whiteboard-mermaid-patterns.md) only when the task explicitly involves whiteboard diagrams.
