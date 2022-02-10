"""
A near carbon copy of httpx.Auth adapted to work in the
framework of websockets.legacy.WebsocketClientProtocol

HTTPX Auth Source (Credit encode)
https://github.com/encode/httpx/blob/master/httpx/_auth.py
"""
from typing import AsyncGenerator, Generator

from .types import Request, Response

class Auth:
    """
    Base class for all authentication schemes.
    To implement a custom authentication scheme, subclass `Auth` and override
    the `.auth_flow()` method.
    If the authentication scheme does I/O such as disk access or network calls, or uses
    synchronization primitives such as locks, you should override `.async_auth_flow()`
    instead of `.auth_flow()` to provide specialized implementations that will be
    used by `AuthFlowWebsocketProtocol`.

    Additional Notes
        - A dispatched request must have the signature Tuple[WebSocketURI, Headers]
        - Responses sent back to the flow generator have the signature
        Tuple[StatusCode, ResponseHeaders, Request, Union[SSLSocket, None], Optional[Body]]
    """

    requires_response_body = False

    def auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        """
        Execute the authentication flow.
        To dispatch a request, `yield` it:
        ```
        yield request
        ```
        The client will `.send()` the response back into the flow generator. You can
        access it like so:
        ```
        response = yield request
        ```
        A `return` (or reaching the end of the generator) will result in the
        client returning the last response obtained from the server.
        You can dispatch as many requests as is necessary.
        """
        yield request

    async def async_auth_flow(self, request: Request) -> AsyncGenerator[Request, Response]:
        """
        Execute the authentication flow asynchronously.
        By default, this defers to `.auth_flow()`. You should override this method
        when the authentication scheme does I/O and/or uses concurrency primitives.
        """

        flow = self.auth_flow(request)
        request = next(flow)

        while True:
            response = yield request
            try:
                request = flow.send(response)
            except StopIteration:
                break