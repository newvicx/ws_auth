from ssl import SSLSocket
from typing import Optional, Tuple, Union

from websockets.datastructures import Headers
from websockets.uri import WebSocketURI


StatusCode = int
Body = bytes
RequestHeaders = Headers
Request = Tuple[WebSocketURI, RequestHeaders]
ResponseHeaders = Headers
Response = Tuple[StatusCode, ResponseHeaders, Request, Union[SSLSocket, None], Optional[Body]]