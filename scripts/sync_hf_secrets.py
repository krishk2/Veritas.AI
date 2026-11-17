#!/usr/bin/env python3
"""
Bulk sync secrets from a local .env file to a Hugging Face Space.
Usage:
    python scripts/sync_hf_secrets.py --space Krishnakkp/veritas-ai-api --env .env
"""

import os
import sys
import argparse
from pathlib import Path
from huggingface_hub import HfApi

def parse_env_file(env_path: Path):
    secrets = {}
    if not env_path.exists():
        print(f"Error: {env_path} does not exist.")
        sys.exit(1)

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            # Only upload non-empty keys and values
            if key and val:
                secrets[key] = val
    return secrets

def main():
    parser = argparse.ArgumentParser(description="Bulk upload secrets to a Hugging Face Space.")
    parser.add_argument("--space", default="Krishnakkp/veritas-ai-api", help="Hugging Face Space repo ID (e.g. username/space-name)")
    parser.add_argument("--env", default=".env", help="Path to local .env file")
    parser.add_argument("--token", default=None, help="Hugging Face Write Token (optional if already logged in)")

    args = parser.parse_args()

    token = args.token or os.environ.get("HF_TOKEN")
    if not token:
        token_file = Path.home() / ".cache" / "huggingface" / "token"
        if token_file.exists():
            token = token_file.read_text().strip()

    api = HfApi(token=token)
    env_path = Path(args.env)
    secrets = parse_env_file(env_path)

    print(f"\n🚀 Syncing {len(secrets)} secrets from '{env_path}' to Hugging Face Space: '{args.space}'...\n")

    # Filter out local development paths or internal flags that shouldn't be cloud secrets
    SKIP_KEYS = {"PORT", "HOST", "VIRTUAL_ENV", "PATH", "PYTHONPATH"}

    success_count = 0
    for key, value in secrets.items():
        if key in SKIP_KEYS:
            continue
        try:
            api.add_space_secret(repo_id=args.space, key=key, value=value)
            print(f"  ✓ Added secret: {key}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed to add {key}: {e}")

    print(f"\n✨ Done! Successfully set {success_count} secrets on '{args.space}'.")

if __name__ == "__main__":
    main()
