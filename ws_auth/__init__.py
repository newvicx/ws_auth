import functools
from typing import Any, Callable, Optional, Sequence

from websockets.datastructures import HeadersLike
from websockets.extensions import ClientExtensionFactory
from websockets.legacy.client import Connect
from websockets.typing import LoggerLike, Origin, Subprotocol

from .auth import Auth
from .protocol import WebsocketAuthProtocol

# Monkey patch Connect class to add 'auth' parameter and modify protcol factory
orig_Connect__init__ = Connect.__init__

def new_Connect__init__(
    self,
    uri: str,
    *,
    create_protocol: Optional[Callable[[Any], WebsocketAuthProtocol]] = None,
    auth: Optional[Auth] = None,
    logger: Optional[LoggerLike] = None,
    compression: Optional[str] = "deflate",
    origin: Optional[Origin] = None,
    extensions: Optional[Sequence[ClientExtensionFactory]] = None,
    subprotocols: Optional[Sequence[Subprotocol]] = None,
    extra_headers: Optional[HeadersLike] = None,
    open_timeout: Optional[float] = 10,
    ping_interval: Optional[float] = 20,
    ping_timeout: Optional[float] = 20,
    close_timeout: Optional[float] = None,
    max_size: Optional[int] = 2 ** 20,
    max_queue: Optional[int] = 2 ** 5,
    read_limit: int = 2 ** 16,
    write_limit: int = 2 ** 16,
    **kwargs: Any,
):
    create_protocol = create_protocol or WebsocketAuthProtocol
    orig_Connect__init__(
        self,
        uri,
        create_protocol=create_protocol,
        logger=logger,
        compression=compression,
        origin=origin,
        extensions=extensions,
        subprotocols=subprotocols,
        extra_headers=extra_headers,
        open_timeout=open_timeout,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
        close_timeout=close_timeout,
        max_size=max_size,
        max_queue=max_queue,
        read_limit=read_limit,
        write_limit=write_limit,
        **kwargs
    )
    # Modify factory to add auth param
    factory = self._create_connection.args[0]
    factory = functools.partial(
        factory.func,
        *factory.args,
        **dict(factory.keywords, auth=auth)
    )
    create_args = self._create_connection.args[1:]
    self._create_connection = functools.partial(
        self._create_connection.func,
        *(factory, *create_args),
        **self._create_connection.keywords
    )

Connect.__init__ = new_Connect__init__
