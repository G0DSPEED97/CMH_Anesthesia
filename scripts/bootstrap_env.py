from __future__ import annotations

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def main() -> int:
    if ENV_FILE.exists():
        return 0
    admin = secrets.token_urlsafe(14)
    staff = secrets.token_urlsafe(14)
    database = secrets.token_hex(24)
    ENV_FILE.write_text(
        "\n".join(
            [
                f"CMH_ANESTHESIA_POSTGRES_PASSWORD={database}",
                f"CMH_ANESTHESIA_DATABASE_URL=postgresql+psycopg://cmh_anesthesia:{database}@127.0.0.1:5432/cmh_anesthesia",
                f"CMH_ANESTHESIA_ADMIN_PASSWORD={admin}",
                f"CMH_ANESTHESIA_SEED_USER_PASSWORD={staff}",
                "CMH_ANESTHESIA_COOKIE_SECURE=false",
                "CMH_ANESTHESIA_TOKEN_PRINTER_NAME=",
                "",
            ]
        ),
        encoding="utf-8",
    )
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass
    print("Created .env with initial credentials:")
    print(f"  admin: {admin}")
    print(f"  reception / doctor / ot_control / display: {staff}")
    print("Store these passwords securely. Every account must change its password at first login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
