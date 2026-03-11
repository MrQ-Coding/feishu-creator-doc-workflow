#!/usr/bin/env python3
"""Bootstrap feishu-creator locally and wire it into common MCP clients."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_SERVER_NAME = "feishu-creator"
AUTO_MODE = "auto"
CLIENTS = ("claude", "cursor", "gemini", "marscode")
MIN_NODE_VERSION = (20, 17, 0)
NETWORK_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "NODE_USE_ENV_PROXY",
    "NODE_EXTRA_CA_CERTS",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
)
PROXY_VALUE_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)
LOCAL_NO_PROXY_VALUES = ("localhost", "127.0.0.1", "::1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install/build feishu-creator and configure common MCP clients.",
    )
    parser.add_argument("--repo-root", help="Path to the feishu-creator repo. Defaults to cwd or nearest parent.")
    parser.add_argument(
        "--clients",
        default="auto",
        help="Comma-separated list of clients to configure: auto, all, claude,cursor,gemini,marscode",
    )
    parser.add_argument("--server-name", default=DEFAULT_SERVER_NAME)
    parser.add_argument("--mode", choices=["auto", "stdio", "http"], default=None)
    parser.add_argument("--auth-type", choices=["tenant", "user"], default=None)
    parser.add_argument("--app-id", default=None)
    parser.add_argument("--app-secret", default=None)
    parser.add_argument("--user-access-token", default=None)
    parser.add_argument("--user-refresh-token", default=None)
    parser.add_argument("--http-auth-token", default=None)
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-env", action="store_true")
    parser.add_argument("--skip-config", action="store_true")
    parser.add_argument("--startup-smoke-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        package_json = candidate / "package.json"
        env_example = candidate / ".env.example"
        if package_json.exists() and env_example.exists():
            try:
                data = json.loads(package_json.read_text())
            except json.JSONDecodeError:
                continue
            if data.get("name") == "feishu-creator":
                return candidate
    raise SystemExit("Could not locate the feishu-creator repo root from the current directory.")


def run(cmd: list[str], cwd: Path, dry_run: bool) -> None:
    print(f"+ {' '.join(cmd)}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd), check=True)


def require_tool(name: str, required: bool = True) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    if required:
        raise SystemExit(
            f"{name} is required. Install Node.js >= 20.17.0 (which provides node/npm) "
            "and reopen the shell so PATH is refreshed before retrying.",
        )
    return None


def get_tool_version(name: str) -> str | None:
    resolved = shutil.which(name)
    if not resolved:
        return None
    try:
        output = subprocess.check_output([resolved, "--version"], text=True, stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    for line in output.splitlines():
        line = line.strip()
        if line:
            return line
    return None


def parse_node_version(text: str) -> tuple[int, int, int]:
    raw = text.strip().lstrip("v")
    parts = raw.split(".")
    if len(parts) < 3:
        raise SystemExit(f"Unexpected Node.js version output: {text!r}")
    return tuple(int(part) for part in parts[:3])  # type: ignore[return-value]


def preflight(repo_root: Path, dry_run: bool) -> dict[str, str | None]:
    node_path = require_tool("node", required=True)
    npm_path = require_tool("npm", required=True)
    git_path = require_tool("git", required=False)
    summary: dict[str, str | None] = {
        "node_path": node_path,
        "npm_path": npm_path,
        "git_path": git_path,
        "node_version": None,
        "npm_version": None,
        "git_version": None,
    }

    print("Preflight summary")
    print(f"- node: {node_path}")
    print(f"- npm: {npm_path}")
    print(f"- git: {git_path or 'not found (ok if repo source already exists)'}")

    version_output = subprocess.check_output([node_path, "--version"], cwd=str(repo_root), text=True)
    node_version = parse_node_version(version_output)
    summary["node_version"] = version_output.strip()
    summary["npm_version"] = get_tool_version("npm")
    summary["git_version"] = get_tool_version("git")
    print(f"- node version: {version_output.strip()}")
    if dry_run:
        return summary
    if node_version < MIN_NODE_VERSION:
        required = ".".join(str(part) for part in MIN_NODE_VERSION)
        raise SystemExit(
            f"Node.js >= {required} is required, but found {version_output.strip()}. "
            "Install a newer Node.js and reopen the shell before retrying.",
        )
    return summary


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def backup_if_exists(path: Path, dry_run: bool) -> None:
    if not path.exists():
        return
    backup = path.with_name(path.name + ".bak")
    if dry_run:
        print(f"+ backup {path} -> {backup}")
        return
    shutil.copy2(path, backup)


def ensure_parent(path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"+ mkdir -p {path.parent}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)


def parse_env_lines(text: str) -> tuple[list[str], dict[str, int]]:
    lines = text.splitlines()
    index: dict[str, int] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        index[key] = i
    return lines, index


def parse_env_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def upsert_env(path: Path, updates: dict[str, str], only_if_missing: set[str], dry_run: bool) -> dict[str, str]:
    original = read_text(path)
    lines, index = parse_env_lines(original)
    changed: dict[str, str] = {}
    for key, value in updates.items():
        if value is None:
            continue
        if key in index:
            if key in only_if_missing:
                continue
            current = lines[index[key]].split("=", 1)[1]
            if current == value:
                continue
            lines[index[key]] = f"{key}={value}"
            changed[key] = value
            continue
        lines.append(f"{key}={value}")
        changed[key] = value
    new_text = "\n".join(lines) + "\n"
    if new_text != original:
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
    return changed


def ensure_env(repo_root: Path, args: argparse.Namespace) -> Path:
    env_path = repo_root / ".env"
    env_example = repo_root / ".env.example"
    if not env_path.exists():
        print(f"+ create {env_path} from {env_example}")
        if not args.dry_run:
            shutil.copy2(env_example, env_path)

    if args.skip_env:
        return env_path

    updates: dict[str, str] = {}
    only_if_missing: set[str] = set()

    requested_mode = args.mode or AUTO_MODE
    updates["MCP_MODE"] = requested_mode
    if not env_path.exists():
        only_if_missing.add("MCP_MODE")

    requested_auth_type = args.auth_type or os.environ.get("FEISHU_AUTH_TYPE")
    if requested_auth_type:
        updates["FEISHU_AUTH_TYPE"] = requested_auth_type
    elif "FEISHU_AUTH_TYPE" not in parse_env_lines(read_text(env_path))[1]:
        updates["FEISHU_AUTH_TYPE"] = "tenant"

    mapping = {
        "FEISHU_APP_ID": args.app_id or os.environ.get("FEISHU_APP_ID"),
        "FEISHU_APP_SECRET": args.app_secret or os.environ.get("FEISHU_APP_SECRET"),
        "FEISHU_USER_ACCESS_TOKEN": args.user_access_token or os.environ.get("FEISHU_USER_ACCESS_TOKEN"),
        "FEISHU_USER_REFRESH_TOKEN": args.user_refresh_token or os.environ.get("FEISHU_USER_REFRESH_TOKEN"),
        "MCP_HTTP_AUTH_TOKEN": args.http_auth_token or os.environ.get("MCP_HTTP_AUTH_TOKEN"),
    }
    updates.update({k: v for k, v in mapping.items() if v})
    upsert_env(env_path, updates, only_if_missing, args.dry_run)
    return env_path


def collect_current_network_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key in NETWORK_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def has_proxy_values(env: dict[str, str]) -> bool:
    return any(env.get(key) for key in PROXY_VALUE_KEYS)


def ensure_node_uses_env_proxy(env: dict[str, str]) -> dict[str, str]:
    if has_proxy_values(env) and "NODE_USE_ENV_PROXY" not in env:
        env["NODE_USE_ENV_PROXY"] = "1"
    return env


def normalize_proxy_url(value: str, default_scheme: str = "http") -> str:
    normalized = value.strip().strip('"').strip("'")
    if not normalized:
        return ""
    if "://" in normalized:
        return normalized
    return f"{default_scheme}://{normalized}"


def normalize_no_proxy(value: str) -> str:
    tokens: list[str] = []
    for raw in value.replace(";", ",").split(","):
        token = raw.strip()
        if not token or token == "(none)":
            continue
        if token.lower() == "<local>":
            for local_value in LOCAL_NO_PROXY_VALUES:
                if local_value not in tokens:
                    tokens.append(local_value)
            continue
        if token not in tokens:
            tokens.append(token)
    return ",".join(tokens)


def parse_windows_proxy_server(value: str) -> dict[str, str]:
    raw = value.strip().strip('"').strip("'")
    if not raw:
        return {}

    env: dict[str, str] = {}
    if "=" not in raw:
        proxy_url = normalize_proxy_url(raw, default_scheme="http")
        if proxy_url:
            env["HTTP_PROXY"] = proxy_url
            env["HTTPS_PROXY"] = proxy_url
        return env

    for part in raw.split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        key, proxy_value = item.split("=", 1)
        proxy_key = key.strip().lower()
        normalized_value = proxy_value.strip()
        if not normalized_value:
            continue
        if proxy_key == "http":
            env["HTTP_PROXY"] = normalize_proxy_url(normalized_value, default_scheme="http")
        elif proxy_key == "https":
            env["HTTPS_PROXY"] = normalize_proxy_url(normalized_value, default_scheme="http")
        elif proxy_key in {"socks", "socks4"}:
            env["ALL_PROXY"] = normalize_proxy_url(normalized_value, default_scheme="socks")
        elif proxy_key == "socks5":
            env["ALL_PROXY"] = normalize_proxy_url(normalized_value, default_scheme="socks5")

    if env.get("HTTP_PROXY") and "HTTPS_PROXY" not in env:
        env["HTTPS_PROXY"] = env["HTTP_PROXY"]
    if env.get("HTTPS_PROXY") and "HTTP_PROXY" not in env:
        env["HTTP_PROXY"] = env["HTTPS_PROXY"]
    return env


def merge_missing_env(base: dict[str, str], updates: dict[str, str]) -> dict[str, str]:
    merged = dict(base)
    for key, value in updates.items():
        if value and not merged.get(key):
            merged[key] = value
    return merged


def detect_windows_internet_settings_proxy() -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": "",
        "env": {},
        "notes": [],
        "pac_only": False,
    }
    if os.name != "nt":
        return result

    try:
        import winreg
    except ImportError:
        return result

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            try:
                proxy_enable = int(winreg.QueryValueEx(key, "ProxyEnable")[0])
            except OSError:
                proxy_enable = 0
            try:
                proxy_server = str(winreg.QueryValueEx(key, "ProxyServer")[0]).strip()
            except OSError:
                proxy_server = ""
            try:
                proxy_override = str(winreg.QueryValueEx(key, "ProxyOverride")[0]).strip()
            except OSError:
                proxy_override = ""
            try:
                auto_config_url = str(winreg.QueryValueEx(key, "AutoConfigURL")[0]).strip()
            except OSError:
                auto_config_url = ""
    except OSError:
        return result

    if proxy_enable and proxy_server:
        env = parse_windows_proxy_server(proxy_server)
        no_proxy = normalize_no_proxy(proxy_override)
        if no_proxy:
            env["NO_PROXY"] = no_proxy
        if has_proxy_values(env):
            result["source"] = "Windows Internet Settings"
            result["env"] = ensure_node_uses_env_proxy(env)

    if auto_config_url:
        if result["env"]:
            result["notes"].append(
                f"另外检测到 Windows 自动代理脚本 (PAC): {auto_config_url}。",
            )
        else:
            result["pac_only"] = True
            result["notes"].append(
                "检测到 Windows 自动代理脚本 (PAC)，但它不会自动转换成 HTTP_PROXY/HTTPS_PROXY；"
                "如需 MCP 子进程走代理，请补充具体代理地址。",
            )
    return result


def detect_windows_winhttp_proxy() -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": "",
        "env": {},
        "notes": [],
        "pac_only": False,
    }
    if os.name != "nt":
        return result

    try:
        completed = subprocess.run(
            ["netsh", "winhttp", "show", "proxy"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return result

    output = (completed.stdout or "").strip()
    if not output:
        return result

    lowered = output.lower()
    if (
        ("direct access" in lowered and "proxy" in lowered)
        or "直接访问" in output
        or "no proxy server" in lowered
    ):
        return result

    values: list[str] = []
    for line in output.splitlines():
        if ":" not in line:
            continue
        _, raw_value = line.split(":", 1)
        value = raw_value.strip()
        if not value:
            continue
        values.append(value)

    proxy_server = ""
    bypass_list = ""
    for value in values:
        lowered_value = value.lower()
        if lowered_value in {"(none)", "none"}:
            if not bypass_list:
                bypass_list = value
            continue
        if "direct access" in lowered_value or "直接访问" in value:
            return result
        if not proxy_server:
            proxy_server = value
            continue
        if not bypass_list:
            bypass_list = value

    env = parse_windows_proxy_server(proxy_server)
    no_proxy = normalize_no_proxy(bypass_list)
    if no_proxy:
        env["NO_PROXY"] = no_proxy
    if has_proxy_values(env):
        result["source"] = "Windows WinHTTP"
        result["env"] = ensure_node_uses_env_proxy(env)
    return result


def collect_child_process_env_info() -> dict[str, Any]:
    env = ensure_node_uses_env_proxy(collect_current_network_env())
    if has_proxy_values(env):
        return {
            "env": env,
            "status": "proxy_configured",
            "source": "current shell env",
            "notes": [],
        }

    notes: list[str] = []
    if os.name == "nt":
        internet_settings = detect_windows_internet_settings_proxy()
        notes.extend(internet_settings["notes"])
        if internet_settings["env"]:
            return {
                "env": merge_missing_env(env, internet_settings["env"]),
                "status": "proxy_configured",
                "source": internet_settings["source"],
                "notes": notes,
            }

        winhttp = detect_windows_winhttp_proxy()
        notes.extend(winhttp["notes"])
        if winhttp["env"]:
            return {
                "env": merge_missing_env(env, winhttp["env"]),
                "status": "proxy_configured",
                "source": winhttp["source"],
                "notes": notes,
            }

        if internet_settings["pac_only"] or winhttp["pac_only"]:
            return {
                "env": env,
                "status": "pac_only",
                "source": "",
                "notes": notes,
            }

    return {
        "env": env,
        "status": "none",
        "source": "",
        "notes": notes,
    }
def is_missing_env_value(value: str | None, placeholders: set[str]) -> bool:
    if value is None:
        return True
    normalized = value.strip()
    return not normalized or normalized in placeholders


def build_manual_input_items(env_path: Path) -> list[dict[str, Any]]:
    env_values = parse_env_values(read_text(env_path))
    items: list[dict[str, Any]] = []

    if is_missing_env_value(env_values.get("FEISHU_APP_ID"), {"cli_xxx"}):
        items.append(
            {
                "field": "FEISHU_APP_ID",
                "reason": "当前仍为空，或还是示例占位值。",
                "steps": [
                    "登录飞书开放平台，进入你准备接入的企业自建应用。",
                    "打开应用的凭证或基础信息页面。",
                    "复制 App ID，填入 .env 里的 FEISHU_APP_ID。",
                ],
            },
        )

    if is_missing_env_value(env_values.get("FEISHU_APP_SECRET"), {"xxx"}):
        items.append(
            {
                "field": "FEISHU_APP_SECRET",
                "reason": "当前仍为空，或还是示例占位值。",
                "steps": [
                    "登录飞书开放平台，进入同一个企业自建应用。",
                    "在凭证页面找到 App Secret。",
                    "复制后填入 .env 里的 FEISHU_APP_SECRET，不要提交到公开仓库。",
                ],
            },
        )

    auth_type = env_values.get("FEISHU_AUTH_TYPE", "tenant").strip() or "tenant"
    if auth_type == "user":
        access_token = env_values.get("FEISHU_USER_ACCESS_TOKEN", "").strip()
        refresh_token = env_values.get("FEISHU_USER_REFRESH_TOKEN", "").strip()
        if not access_token and not refresh_token:
            items.append(
                {
                    "field": "FEISHU_USER_ACCESS_TOKEN / FEISHU_USER_REFRESH_TOKEN",
                    "reason": "当前是 user 模式，但还没有用户 token。",
                    "steps": [
                        "先保留 FEISHU_AUTH_TYPE=user，并重启 Codex 或目标 MCP 客户端。",
                        "通过 get_user_authorize_url 打开授权页面，使用飞书账号完成授权。",
                        "从回调地址中取出 code，再调用 exchange_user_auth_code 换取用户 token。",
                        "把换到的 access token / refresh token 写回 .env，或直接切回 tenant 模式。",
                    ],
                },
            )

    return items


def run_startup_smoke_test(repo_root: Path, dist_entry: Path, node_path: str, dry_run: bool) -> dict[str, str]:
    if dry_run:
        return {"status": "未执行", "detail": "dry-run 模式下跳过启动冒烟测试。"}
    if not dist_entry.exists():
        return {"status": "失败", "detail": "dist/index.js 不存在，无法执行启动冒烟测试。"}

    cmd = [node_path, str(dist_entry), "--stdio"]
    print(f"+ {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = ""
    try:
        time.sleep(2)
        if process.poll() is None:
            process.terminate()
            try:
                output, _ = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                output, _ = process.communicate(timeout=3)
            detail = "Starting feishu-creator in stdio mode (进程可正常拉起并保持运行)。"
            if output.strip():
                detail = f"{detail} 日志摘录: {output.strip().splitlines()[0]}"
            return {"status": "通过", "detail": detail}

        output, _ = process.communicate(timeout=1)
        detail = f"进程提前退出，exit code {process.returncode}。"
        if output.strip():
            detail = f"{detail} 日志摘录: {output.strip().splitlines()[0]}"
        return {"status": "失败", "detail": detail}
    except Exception as exc:
        if process.poll() is None:
            process.kill()
        return {"status": "失败", "detail": f"启动冒烟测试异常: {exc}"}


def print_install_report(
    repo_root: Path,
    env_path: Path,
    dist_entry: Path,
    tool_summary: dict[str, str | None],
    touched: list[Path],
    child_env_info: dict[str, Any],
    manual_inputs: list[dict[str, Any]],
    smoke_result: dict[str, str] | None,
    args: argparse.Namespace,
) -> None:
    child_env = child_env_info["env"]
    generated_files = [env_path, *touched, dist_entry]
    unique_files: list[Path] = []
    seen: set[Path] = set()
    for path in generated_files:
        if path in seen:
            continue
        seen.add(path)
        unique_files.append(path)

    completed_steps: list[str] = []
    if args.dry_run:
        completed_steps.append("本次为 dry-run，仅做流程预演，没有实际写入文件。")
    else:
        if not args.skip_install:
            completed_steps.append("已完成 npm install。")
        if not args.skip_build:
            completed_steps.append("已完成 npm run build。")
        if not args.skip_env:
            completed_steps.append("已检查并准备 .env。")
        if not args.skip_config:
            completed_steps.append("已写入或更新 MCP 客户端配置。")

    if child_env_info["status"] == "proxy_configured":
        completed_steps.append(
            ("已检测到代理并写入 MCP 子进程 env" if not args.dry_run else "已检测到代理；正式执行时将写入 MCP 子进程 env")
            + (f"（来源: {child_env_info['source']}）" if child_env_info["source"] else "")
            + ": "
            + ", ".join(sorted(child_env.keys()))
            + "。",
        )
    elif child_env_info["status"] == "pac_only":
        completed_steps.append(
            "检测到系统自动代理脚本 (PAC)，但未自动写入 HTTP_PROXY/HTTPS_PROXY。",
        )
    elif child_env:
        completed_steps.append(
            "未检测到具体代理地址，但已保留其他网络相关环境变量: "
            + ", ".join(sorted(child_env.keys()))
            + "。",
        )
    else:
        completed_steps.append("未检测到具体代理地址，因此 MCP 配置未额外写入代理 env。")
    for note in child_env_info["notes"]:
        completed_steps.append(note)

    next_steps: list[str] = []
    if args.dry_run:
        next_steps.append("去掉 --dry-run 重新执行一次实际安装，让文件真正写入磁盘。")
        if manual_inputs:
            next_steps.append("实际安装完成后，再按上面的获取方法补齐 .env。")
        else:
            next_steps.append("实际安装完成后，再重启 Codex 或目标 MCP 客户端加载 MCP 配置。")
    else:
        if manual_inputs:
            next_steps.append("先把上面仍需手动填写的字段补进 .env。")
        if touched:
            next_steps.append("重启 Codex 或目标 MCP 客户端，让新配置生效。")
        if child_env_info["status"] == "pac_only":
            next_steps.append(
                "如果当前网络依赖系统自动代理脚本 (PAC)，请手动确认具体代理地址，再写入 shell 环境或 .mcp.json 后重试 auth_status(fetchToken=true)。",
            )
        if not manual_inputs:
            next_steps.append("继续做连通性验证：ping -> auth_status(fetchToken=true) -> get_feishu_document_info。")
        elif smoke_result is None:
            next_steps.append("补齐凭证后，可以再执行一次 node dist/index.js --stdio 做启动验证。")

    print("")
    print("安装结果")
    if args.dry_run:
        print("- 已完成安装流程预演，当前未实际落盘。")
    else:
        print("- 飞书助手基础安装流程已完成。")

    print("")
    print("环境")
    print(f"- Node.js: {tool_summary.get('node_version') or '已检测到 node，但未记录版本'}")
    print(f"- npm: {tool_summary.get('npm_version') or '已检测到 npm'}")
    print(f"- Git: {tool_summary.get('git_version') or '未检测到或未记录'}")

    print("")
    print("仓库位置")
    print(f"- {repo_root}")

    print("")
    print("执行结果")
    for step in completed_steps:
        print(f"- {step}")

    print("")
    print("计划生成或更新的文件" if args.dry_run else "生成或更新的文件")
    for path in unique_files:
        print(f"- {path}")

    print("")
    print("启动冒烟测试")
    if smoke_result is None:
        print("- 未执行；需要时可运行 node dist/index.js --stdio 进行验证。")
    else:
        print(f"- {smoke_result['status']}: {smoke_result['detail']}")

    print("")
    print("仍需手动填写")
    if not manual_inputs:
        print("- 当前未发现必须补填的字段。")
    else:
        for item in manual_inputs:
            print(f"- {item['field']}: {item['reason']}")
            print("  获取方法:")
            for index, step in enumerate(item["steps"], start=1):
                print(f"  {index}. {step}")

    print("")
    print("下一步建议")
    for index, step in enumerate(next_steps, start=1):
        print(f"{index}. {step}")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)


def write_json(path: Path, data: dict[str, Any], dry_run: bool) -> None:
    ensure_parent(path, dry_run)
    existing = read_text(path).strip()
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if existing == rendered.strip():
        return
    if path.exists():
        backup_if_exists(path, dry_run)
    print(f"+ write {path}")
    if not dry_run:
        path.write_text(rendered, encoding="utf-8")


def upsert_server_config(path: Path, server_name: str, server_config: dict[str, Any], dry_run: bool) -> None:
    data = load_json(path)
    if not isinstance(data, dict):
        data = {}
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers
    servers[server_name] = server_config
    write_json(path, data, dry_run)


def detect_clients(args: argparse.Namespace, home: Path, repo_root: Path) -> list[str]:
    if args.clients == "all":
        return list(CLIENTS)
    if args.clients != "auto":
        return [item.strip() for item in args.clients.split(",") if item.strip()]

    detected = ["claude"]
    if (home / ".config" / "Cursor").exists() or (home / ".cursor").exists():
        detected.append("cursor")
    if (home / ".gemini" / "antigravity").exists():
        detected.append("gemini")
    if (home / ".marscode").exists():
        detected.append("marscode")
    if (repo_root / ".cursor").exists() and "cursor" not in detected:
        detected.append("cursor")
    return detected


def configure_clients(
    repo_root: Path,
    args: argparse.Namespace,
    dist_entry: Path,
    child_env: dict[str, str],
) -> list[Path]:
    if args.skip_config:
        return []

    home = Path.home()
    clients = detect_clients(args, home, repo_root)
    touched: list[Path] = []
    server_config = {
        "command": "node",
        "args": [str(dist_entry), "--stdio"],
        "env": child_env,
    }

    for client in clients:
        if client == "claude":
            path = repo_root / ".mcp.json"
        elif client == "cursor":
            path = repo_root / ".cursor" / "mcp.json"
        elif client == "gemini":
            path = home / ".gemini" / "antigravity" / "mcp_config.json"
        elif client == "marscode":
            path = home / ".marscode" / "Studio.mcp.config.json"
        else:
            continue
        upsert_server_config(path, args.server_name, server_config, args.dry_run)
        touched.append(path)
    return touched


def main() -> int:
    args = parse_args()
    start = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    repo_root = find_repo_root(start)
    package_json = repo_root / "package.json"
    dist_entry = repo_root / "dist" / "index.js"

    print(f"repo_root={repo_root}")
    tool_summary = preflight(repo_root, args.dry_run)

    if not args.skip_install:
        run([str(tool_summary["npm_path"]), "install"], repo_root, args.dry_run)

    env_path = ensure_env(repo_root, args)

    if not args.skip_build:
        run([str(tool_summary["npm_path"]), "run", "build"], repo_root, args.dry_run)

    child_env_info = collect_child_process_env_info()
    touched = configure_clients(repo_root, args, dist_entry, child_env_info["env"])
    manual_inputs = build_manual_input_items(env_path)
    smoke_result = None
    if args.startup_smoke_test:
        smoke_result = run_startup_smoke_test(repo_root, dist_entry, str(tool_summary["node_path"]), args.dry_run)
    print_install_report(
        repo_root,
        env_path,
        dist_entry,
        tool_summary,
        touched,
        child_env_info,
        manual_inputs,
        smoke_result,
        args,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
