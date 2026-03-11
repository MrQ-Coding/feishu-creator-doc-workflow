#!/usr/bin/env python3
"""Bootstrap feishu-creator locally and wire it into common MCP clients."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_SERVER_NAME = "feishu-creator"
AUTO_MODE = "auto"
CLIENTS = ("claude", "cursor", "gemini", "marscode")
MIN_NODE_VERSION = (20, 17, 0)


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


def parse_node_version(text: str) -> tuple[int, int, int]:
    raw = text.strip().lstrip("v")
    parts = raw.split(".")
    if len(parts) < 3:
        raise SystemExit(f"Unexpected Node.js version output: {text!r}")
    return tuple(int(part) for part in parts[:3])  # type: ignore[return-value]


def preflight(repo_root: Path, dry_run: bool) -> None:
    node_path = require_tool("node", required=True)
    npm_path = require_tool("npm", required=True)
    git_path = require_tool("git", required=False)

    print("Preflight summary")
    print(f"- node: {node_path}")
    print(f"- npm: {npm_path}")
    print(f"- git: {git_path or 'not found (ok if repo source already exists)'}")

    if dry_run:
        return

    version_output = subprocess.check_output(["node", "--version"], cwd=str(repo_root), text=True)
    node_version = parse_node_version(version_output)
    print(f"- node version: {version_output.strip()}")
    if node_version < MIN_NODE_VERSION:
        required = ".".join(str(part) for part in MIN_NODE_VERSION)
        raise SystemExit(
            f"Node.js >= {required} is required, but found {version_output.strip()}. "
            "Install a newer Node.js and reopen the shell before retrying.",
        )


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


def ensure_env(repo_root: Path, args: argparse.Namespace) -> tuple[Path, list[str]]:
    env_path = repo_root / ".env"
    env_example = repo_root / ".env.example"
    warnings: list[str] = []

    if not env_path.exists():
        print(f"+ create {env_path} from {env_example}")
        if not args.dry_run:
            shutil.copy2(env_example, env_path)

    if args.skip_env:
        return env_path, warnings

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

    content = read_text(env_path)
    if "FEISHU_APP_ID=cli_xxx" in content or "FEISHU_APP_ID=" in content and "FEISHU_APP_ID=\n" in content:
        warnings.append("FEISHU_APP_ID is still missing or left as the example placeholder.")
    if "FEISHU_APP_SECRET=xxx" in content or "FEISHU_APP_SECRET=" in content and "FEISHU_APP_SECRET=\n" in content:
        warnings.append("FEISHU_APP_SECRET is still missing or left as the example placeholder.")
    return env_path, warnings


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


def configure_clients(repo_root: Path, args: argparse.Namespace, dist_entry: Path) -> list[Path]:
    if args.skip_config:
        return []

    home = Path.home()
    clients = detect_clients(args, home, repo_root)
    touched: list[Path] = []
    server_config = {
        "command": "node",
        "args": [str(dist_entry), "--stdio"],
        "env": {},
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
    preflight(repo_root, args.dry_run)

    if not args.skip_install:
        run(["npm", "install"], repo_root, args.dry_run)

    env_path, warnings = ensure_env(repo_root, args)

    if not args.skip_build:
        run(["npm", "run", "build"], repo_root, args.dry_run)

    touched = configure_clients(repo_root, args, dist_entry)

    print("")
    print("Setup summary")
    print(f"- package: {package_json}")
    print(f"- env: {env_path}")
    print(f"- dist: {dist_entry}")
    if touched:
        print("- configured MCP files:")
        for path in touched:
            print(f"  - {path}")
    else:
        print("- configured MCP files: none")

    if warnings:
        print("- remaining manual inputs:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("- remaining manual inputs: none detected")

    return 0


if __name__ == "__main__":
    sys.exit(main())
