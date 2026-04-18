"""One-off OAuth 2.0 authorization helper.

Run this locally before starting the backend:

    cd backend
    python scripts/setup_oauth.py

It opens a browser for the Google consent screen and writes the resulting
token to the path in `$TOKEN_FILE` (default: `token.json`).
"""

from __future__ import annotations

import os
import sys

# Allow running as `python scripts/setup_oauth.py` from the `backend/` dir.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from app.collectors.youtube_analytics import OAUTH_SCOPES  # noqa: E402
from config.settings import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    client_secrets = settings.CLIENT_SECRETS_FILE
    token_path = settings.TOKEN_FILE

    if not os.path.exists(client_secrets):
        raise SystemExit(
            f"client_secrets.json が見つかりません: {client_secrets}\n"
            "Google Cloud Console で OAuth クライアントを発行し、"
            "ダウンロードしたファイルのパスを CLIENT_SECRETS_FILE に設定してください。"
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets, OAUTH_SCOPES
    )
    creds = flow.run_local_server(port=0)

    with open(token_path, "w", encoding="utf-8") as fp:
        fp.write(creds.to_json())

    print(f"OAuth token を保存しました: {token_path}")


if __name__ == "__main__":
    main()
