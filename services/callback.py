import httpx
from core.config import settings
from .create_signature import create_service_headers
import asyncio
import logging



logger = logging.getLogger(__name__)


class DjangoClient:

    def __init__(self):

        self.client = httpx.AsyncClient(
            base_url=settings.DJANGO_API_URL,
            timeout=10,
        )

    async def _request(
        self,
        method,
        url,
        max_retries=3,
        **kwargs,
    ):

        last_exception = None

        for attempt in range(1, max_retries + 1):

            try:

                request = self.client.build_request(
                    method,
                    url,
                    **kwargs,
                )

                body = request.content.decode("utf-8")

                request.headers.update(
                    create_service_headers(
                        method=method,
                        path=request.url.raw_path.decode(),
                        body=body,
                    )
                )

                response = await self.client.send(request)

                response.raise_for_status()

                return response.json()

            except httpx.RequestError as exc:

                last_exception = exc

                logger.warning(
                    "Django request failed. "
                    "method=%s url=%s attempt=%s/%s error=%s",
                    method,
                    url,
                    attempt,
                    max_retries,
                    exc,
                )

            except httpx.HTTPStatusError as exc:

                status_code = exc.response.status_code

                if status_code not in {500, 502, 503, 504}:
                    raise

                last_exception = exc

                logger.warning(
                    "Django temporary error. "
                    "method=%s url=%s status=%s attempt=%s/%s",
                    method,
                    url,
                    status_code,
                    attempt,
                    max_retries,
                )

            if attempt < max_retries:
                await asyncio.sleep(3)

        raise last_exception

    async def post(self, url, **kwargs):
        return await self._request(
            method="POST",
            url=url,
            **kwargs,
        )
