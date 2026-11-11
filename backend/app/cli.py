import argparse
import os
import secrets
import sys

import uvicorn
from pydantic import ValidationError

from app.core.config import Settings


def main(argv=()) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable-settings", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        settings = Settings()
    except ValidationError:
        print(
            "Invalid NOMI configuration; check variable names and documented constraints.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    from app.main import create_app

    admin = None
    if arguments.enable_settings or os.name == "nt":
        from app.settings.manager import LocalSettings
        from app.settings.vault import VaultError, platform_vault

        code = secrets.token_urlsafe(24) if arguments.enable_settings else None
        try:
            admin = LocalSettings(settings, platform_vault(), code)
        except VaultError:
            print("Protected credential storage unavailable; startup aborted.", file=sys.stderr)
            raise SystemExit(2) from None
        if code:
            print(
                "Local settings pairing code (single use, 5 minutes; do not share):",
                code,
                flush=True,
            )
    uvicorn.run(
        create_app(settings, local_admin=admin),
        host=settings.host,
        port=settings.port,
        access_log=False,
        workers=1,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
