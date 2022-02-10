from typing import Any, Optional, Sequence

from websockets.datastructures import Headers, HeadersLike
from websockets.exceptions import (
    InvalidHeader,
    InvalidStatusCode,
    NegotiationError,
    RedirectHandshake,
)
from websockets.extensions import ClientExtensionFactory
from websockets.headers import (
    build_authorization_basic,
    build_extension,
    build_host,
    build_subprotocol,
)
from websockets.http import USER_AGENT
from websockets.legacy.client import WebSocketClientProtocol
from websockets.legacy.handshake import build_request, check_response
from websockets.typing import LoggerLike, Origin, Subprotocol
from websockets.uri import WebSocketURI

from .auth import Auth
from .http import HTTPInterface
from .types import Request, Response


class WebsocketAuthProtocol(WebSocketClientProtocol):
    """
    Adds support for HTTPX style auth flows
    """

    def __init__(
        self,
        *,
        auth: Auth = None,
        follow_redirects: bool = False,
        max_redirects: int = None,
        logger: Optional[LoggerLike] = None,
        origin: Optional[Origin] = None,
        extensions: Optional[Sequence[ClientExtensionFactory]] = None,
        subprotocols: Optional[Sequence[Subprotocol]] = None,
        extra_headers: Optional[HeadersLike] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            logger=logger,
            origin=origin,
            extensions=extensions,
            subprotocols=subprotocols,
            extra_headers=extra_headers,
            **kwargs
        )
        self.auth = auth or Auth()
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects or 5

    async def handshake(
        self,
        wsuri: WebSocketURI,
        origin: Optional[Origin] = None,
        available_extensions: Optional[Sequence[ClientExtensionFactory]] = None,
        available_subprotocols: Optional[Sequence[Subprotocol]] = None,
        extra_headers: Optional[HeadersLike] = None,
    ) -> None:
        """
        Unchanged from base client protocol except HTTP req-resp handled by
        auth flow
        """
        request_headers = Headers()

        request_headers["Host"] = build_host(wsuri.host, wsuri.port, wsuri.secure)

        if wsuri.user_info:
            request_headers["Authorization"] = build_authorization_basic(
                *wsuri.user_info
            )
            self.auth = Auth()

        if origin is not None:
            request_headers["Origin"] = origin

        key = build_request(request_headers)

        if available_extensions is not None:
            extensions_header = build_extension(
                [
                    (extension_factory.name, extension_factory.get_request_params())
                    for extension_factory in available_extensions
                ]
            )
            request_headers["Sec-WebSocket-Extensions"] = extensions_header

        if available_subprotocols is not None:
            protocol_header = build_subprotocol(available_subprotocols)
            request_headers["Sec-WebSocket-Protocol"] = protocol_header

        extra_headers = extra_headers or self.extra_headers
        if extra_headers is not None:
            request_headers.update(extra_headers)

        request_headers.setdefault("User-Agent", USER_AGENT)
        request = (wsuri, request_headers)
        try:
            status_code, response_headers = await self.http_handling_auth(request)
        except BaseException as err:
            raise NegotiationError("Auth flow failed") from err

        if status_code in (301, 302, 303, 307, 308):
            if "Location" not in response_headers:
                raise InvalidHeader("Location")
            raise RedirectHandshake(response_headers["Location"])
        elif status_code != 101:
            raise InvalidStatusCode(status_code, response_headers)

        check_response(response_headers, key)

        self.extensions = self.process_extensions(
            response_headers, available_extensions
        )

        self.subprotocol = self.process_subprotocol(
            response_headers, available_subprotocols
        )
        self.logger.debug("Handshake succeeded")
        self.connection_open()

    # Handling is functionally equivalent to httpx.AsyncClient auth handling
    # though the semantics have changed to fit within websockets framework
    # https://github.com/encode/httpx/blob/master/httpx/_client.py
    async def http_handling_auth(
        self,
        request: Request
    ) -> Response:
        
        """Create auth flow generator and execute HTTP requests"""
        
        requires_response_body = self.auth.requires_response_body
        auth_flow = self.auth.async_auth_flow(request)
        interface = HTTPInterface(self)
        
        try:
            request = await auth_flow.__anext__()
            while True:
                response = await interface.handle_async_request(request)
                # We dont want the auth flow to continue in the event of
                # a redirect
                status_code = response[0]
                if status_code in (301, 302, 303, 307, 308):
                    return response[:2]
                if requires_response_body:
                    content = await interface.receive_body()
                    response = (*response, content)
                try:
                    try:
                        next_request = await auth_flow.asend(response)
                    except StopAsyncIteration:
                        return response[:2]
                    request = next_request
                except Exception as err:
                    raise err
                await interface.start_next_cycle()
        finally:
            interface.teardown()
            await auth_flow.aclose()
