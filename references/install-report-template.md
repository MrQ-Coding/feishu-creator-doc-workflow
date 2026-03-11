# Feishu Creator Install Report Template

Use this template after install, bootstrap, repair, or verification work for `feishu-creator`.

## Required Section Order

1. `安装结果`
2. `环境`
3. `仓库位置`
4. `执行结果`
5. `生成或更新的文件`
6. `启动冒烟测试`
7. `仍需手动填写`
8. `下一步建议`

## Template

```text
安装结果
- 飞书助手基础安装流程已完成。

环境
- Node.js: <version>
- npm: <version>
- Git: <version or not found>

仓库位置
- <repo_root>

执行结果
- 已完成 npm install。
- 已完成 npm run build。
- 已检查并准备 .env。
- 已写入或更新 MCP 客户端配置。

生成或更新的文件
- <repo_root>/.env
- <repo_root>/.mcp.json
- <repo_root>/.cursor/mcp.json
- <repo_root>/dist/index.js

启动冒烟测试
- 通过: Starting feishu-creator in stdio mode (进程可正常拉起并保持运行)。

仍需手动填写
- FEISHU_APP_ID: 当前仍为空，或还是示例占位值。
  获取方法:
  1. 登录飞书开放平台，进入目标企业自建应用。
  2. 打开应用的凭证或基础信息页面。
  3. 复制 App ID，写入 .env。
- FEISHU_APP_SECRET: 当前仍为空，或还是示例占位值。
  获取方法:
  1. 在同一个应用的凭证页面找到 App Secret。
  2. 复制后写入 .env。
  3. 不要把它提交到公开仓库。

下一步建议
1. 先把上面仍需手动填写的字段补进 .env。
2. 重启 Codex 或目标 MCP 客户端，让新配置生效。
3. 再做连通性验证：ping -> auth_status(fetchToken=true) -> get_feishu_document_info。
4. 如果你在 Windows 上要验证中文写入，优先用 `node scripts/callTool.mjs --tool <name> --args-file <utf8-json>`，不要把带中文的内联 JSON 直接管道给 `node`。
```

## Notes

- If no manual env fields are missing, explicitly say `当前未发现必须补填的字段`
- If startup smoke test was not run, say so directly and tell the user how to run `node dist/index.js --stdio`
- Do not collapse install/build/client-config success into Feishu-side auth success; report them separately
- For Windows local verification with Chinese payloads, prefer `node scripts/callTool.mjs --tool <name> --args-file <utf8-json>` so the JSON stays UTF-8 end-to-end
- In `生成或更新的文件`, keep absolute paths instead of shortening them to repo-relative names; otherwise the UI may not open them correctly
