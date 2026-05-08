import uvicorn

from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "admin.main:app",
        host=settings.app_host,
        port=settings.admin_port,
        reload=True,
    )
