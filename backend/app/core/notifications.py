import httpx
from app.core.config import settings


async def send_notification(title: str, message: str) -> None:
    url = f"{settings.ntfy_url}/{settings.ntfy_topic}"
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            content=message.encode(),
            headers={"Title": title},
        )
