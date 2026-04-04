#!/usr/bin/env python3
"""VaultHelper — Convenience CLI for Vault operations.

Usage:
    python3 vault_helper.py read local/threatrecall/patton/test
    python3 vault_helper.py write local/threatrecall/patton/test "secret-value"
    python3 vault_helper.py delete local/threatrecall/patton/test
    python3 vault_helper.py list local/threatrecall/patton
    python3 vault_helper.py auth-check
"""

import argparse
import json
import sys
from pathlib import Path

import hvac


def load_credentials(agent: str = "patton") -> dict:
    creds_file = Path.home() / ".openclaw" / "vault-credentials" / f"{agent}.json"
    if not creds_file.exists():
        raise FileNotFoundError(f"Credentials not found: {creds_file}")
    with open(creds_file) as f:
        return json.load(f)


def get_client(agent: str = "patton") -> hvac.Client:
    creds = load_credentials(agent)
    client = hvac.Client(url=creds["vault_addr"])
    client.auth.approle.login(
        role_id=creds["role_id"],
        secret_id=creds["secret_id"],
    )
    return client


def cmd_read(path: str, agent: str = "patton") -> str:
    client = get_client(agent)
    result = client.secrets.kv.v2.read_secret_version(path=path, mount_point="secret")
    return result["data"]["data"]["value"]


def cmd_write(path: str, value: str, agent: str = "patton") -> None:
    client = get_client(agent)
    client.secrets.kv.v2.create_or_update_secret(
        path=path,
        secret={"value": value},
        mount_point="secret",
    )
    print(f"Written to secret/data/{path}")


def cmd_delete(path: str, agent: str = "patton") -> None:
    client = get_client(agent)
    client.secrets.kv.v2.delete_metadata_and_all_versions(path=path, mount_point="secret")
    print(f"Deleted secret/data/{path}")


def cmd_list(path: str, agent: str = "patton") -> None:
    client = get_client(agent)
    result = client.secrets.kv.v2.list_secrets(path=path, mount_point="secret")
    keys = result.get("data", {}).get("keys", [])
    for key in keys:
        print(key)


def cmd_auth_check(agent: str = "patton") -> None:
    try:
        client = get_client(agent)
        print(f"Authenticated as {agent}: OK")
        print(f"  Vault addr: {client.url}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="VaultHelper CLI")
    parser.add_argument("command", choices=["read", "write", "delete", "list", "auth-check"])
    parser.add_argument("path", nargs="?")
    parser.add_argument("value", nargs="?")
    parser.add_argument("--agent", default="patton")
    args = parser.parse_args()

    try:
        match args.command:
            case "read":
                if not args.path:
                    print("Error: path required for read")
                    sys.exit(1)
                print(cmd_read(args.path, args.agent))
            case "write":
                if not args.path or not args.value:
                    print("Error: path and value required for write")
                    sys.exit(1)
                cmd_write(args.path, args.value, args.agent)
            case "delete":
                if not args.path:
                    print("Error: path required for delete")
                    sys.exit(1)
                cmd_delete(args.path, args.agent)
            case "list":
                cmd_list(args.path or "", args.agent)
            case "auth-check":
                cmd_auth_check(args.agent)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
