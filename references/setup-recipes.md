# Feishu Creator Setup Recipes

## 1. Default Setup Goal

- Keep `MCP_MODE=auto`
- Use `stdio` for day-to-day MCP usage
- Only use `HTTP` temporarily for first-time `user` token / OAuth callback flow
- Do as much work automatically as possible before asking the user for missing credentials

## 2. Bootstrap Script

- Primary entry point: `scripts/setup_feishu_creator.py`
- Use it when the user asks to install, initialize, configure, bootstrap, enable, or wire `feishu-creator` into an MCP client
- Default behavior:
  1. Verify repo root
  2. Run `npm install`
  3. Create `.env` from `.env.example` if missing
  4. Preserve or upsert provided env values
  5. Build with `npm run build`
  6. Write MCP client configs for detected targets

## 3. Config Targets

- Claude-compatible local config: `<repo>/.mcp.json`
- Cursor workspace config: `<repo>/.cursor/mcp.json`
- Gemini global config: `~/.gemini/antigravity/mcp_config.json`
- MarsCode global config: `~/.marscode/Studio.mcp.config.json`

Prefer workspace-local config over global config when the client supports it.

## 4. Remaining Manual Inputs

If the script finishes but the service still cannot authenticate, usually only these fields remain:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_AUTH_TYPE`
- `FEISHU_USER_ACCESS_TOKEN` or `FEISHU_USER_REFRESH_TOKEN` when the user intentionally needs `user` mode

Do not frame that as a failed install when dependency install, build, and client wiring already succeeded.

## 5. Verification

After setup, verify:

1. `dist/index.js` exists
2. `.env` exists
3. Target MCP config files contain a `feishu-creator` server entry
4. If credentials exist, the user can continue with `ping` -> `auth_status` -> `get_feishu_document_info`
