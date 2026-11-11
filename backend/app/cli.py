import sys

import uvicorn
from pydantic import ValidationError

from app.core.config import Settings


def main() -> None:
    try:
        settings = Settings()
    except ValidationError:
        print(
            "Invalid NOMI configuration; check variable names and documented constraints.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    from app.main import create_app

    uvicorn.run(
        create_app(settings), host=settings.host, port=settings.port, access_log=False, workers=1
    )


if __name__ == "__main__":
    main()
