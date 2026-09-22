import httpx


class CallbackClientError(Exception):
    pass


class CallbackClient:

    async def post(
        self,
        url: str,
        data: dict,
    ):
        print(f"url is : {url}")
        print(f"data is : {data}")

        try:

            async with httpx.AsyncClient(
                timeout=30.0,
            ) as client:

                response = await client.post(
                    url,
                    json=data,
                )

                print(f"response is : {response}")
        except httpx.RequestError as exc:

            raise CallbackClientError(
                f"Callback request failed: {exc}"
            ) from exc

        if response.status_code >= 400:

            raise CallbackClientError(
                f"Callback request failed: "
                f"{response.status_code} - "
                f"{response.text}"
            )

        return response.json()