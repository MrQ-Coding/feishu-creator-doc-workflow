# Feishu Creator Setup Recipes

## 1. Default Setup Goal

- Keep `MCP_MODE=auto`
- Use `stdio` for day-to-day MCP usage
- Only use `HTTP` temporarily for first-time `user` token / OAuth callback flow
- Do as much work automatically as possible before asking the user for missing credentials

## 2. Preflight

- Mandatory tools: `node`, `npm`
- Preferred tool: `git`
- Required Node version: `>= 20.17.0`
- If `node` was just installed, refresh the shell PATH or open a fresh shell before retrying
- If `git` is missing but the repo source is already present, bootstrap can still continue

## 3. Source And Repo Integrity

- Canonical repo page: `https://github.com/MrQ-Coding/feishu-creator`
- Canonical clone URL: `https://github.com/MrQ-Coding/feishu-creator.git`
- Canonical zip URL: `https://github.com/MrQ-Coding/feishu-creator/archive/refs/heads/main.zip`
- Do not start with GitHub / npm / pip keyword search when the canonical URLs above are available
- Prefer `git clone` when the repo is not present yet
- Fall back to a GitHub zip only when clone is unavailable or blocked
- Verify the repo root contains at least:
  1. `package.json`
  2. `.env.example`

## 4. Bootstrap Script

- Primary entry point: `scripts/setup_feishu_creator.py`
- Use it when the user asks to install, initialize, configure, bootstrap, enable, or wire `feishu-creator` or a Feishu helper (`飞书助手`) into an MCP client
- When bootstrapping from scratch, fetch the source from the canonical repo URL above before running the script
- Default behavior:
  1. Run preflight checks
  2. Run `npm install`
  3. Create `.env` from `.env.example` if missing
  4. Preserve or upsert provided env values
  5. Build with `npm run build`
  6. Write MCP client configs for detected targets

## 5. Config Targets

- Claude-compatible local config: `<repo>/.mcp.json`
- Cursor workspace config: `<repo>/.cursor/mcp.json`
- Gemini global config: `~/.gemini/antigravity/mcp_config.json`
- MarsCode global config: `~/.marscode/Studio.mcp.config.json`

Prefer workspace-local config over global config when the client supports it.

## 6. Remaining Manual Inputs

If the script finishes but the service still cannot authenticate, usually only these fields remain:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_AUTH_TYPE` (default `tenant`)
- `FEISHU_USER_ACCESS_TOKEN` or `FEISHU_USER_REFRESH_TOKEN` when the user intentionally needs `user` mode

Acquisition hints:

- `FEISHU_APP_ID`: log in to Feishu Open Platform, open the target custom app, then copy the App ID from the app credentials / basic info page
- `FEISHU_APP_SECRET`: copy the App Secret from the same app credentials page; do not commit it to a public repo
- `FEISHU_AUTH_TYPE`: keep `tenant` unless the user explicitly needs user OAuth or user-scoped APIs
- `FEISHU_USER_ACCESS_TOKEN` / `FEISHU_USER_REFRESH_TOKEN`: after MCP config is active, use `get_user_authorize_url` -> browser authorize -> `exchange_user_auth_code`

Do not frame that as a failed install when dependency install, build, and client wiring already succeeded.

## 7. Verification

After setup, verify:

1. `dist/index.js` exists
2. `.env` exists
3. Target MCP config files contain a `feishu-creator` server entry
4. If the user is explicitly validating install health, run `node dist/index.js --stdio` as a startup smoke test
5. If credentials exist, continue with `ping` -> `auth_status(fetchToken=true)` -> `get_feishu_document_info`
6. Tell the user to restart Codex or the target MCP client after config changes

## 8. Install Result Report

Use a fixed user-facing structure after setup:

1. `安装结果`
2. `环境`
3. `仓库位置`
4. `执行结果`
5. `生成或更新的文件`
6. `启动冒烟测试`
7. `仍需手动填写`
8. `下一步建议`

When `仍需手动填写` is non-empty, include acquisition steps for each missing field instead of listing bare env names.

## 9. Failure Classification

- Search/index delay after create is not evidence that install failed
- Permission or auth failures after setup are runtime/config issues, not dependency-install failures
- Report install/build/client-config success or failure separately from Feishu-side auth and indexing outcomes
