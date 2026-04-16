import uvicorn

from .config import Settings


def main():
    settings = Settings()
    uvicorn.run(
        "ohent_scheduler.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
