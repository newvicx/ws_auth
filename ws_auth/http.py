import asyncio
import logging
import ssl
import weakref
from typing import Union

import h11
from websockets.datastructures import Headers
from websockets.legacy.client import WebSocketClientProtocol
from websockets.uri import WebSocketURI

from .types import Request, Response


logger = logging.getLogger(__name__)


class HTTPInterface:

    """
    An HTTP 1.1 interface that wraps the transport and reader from
    an instance of the WebsocketClientProtocol. It provides a higher
    level HTTP interface for handling the opening handshake over
    multiple request-response cycles
    """

    def __init__(
        self,
        protocol: WebSocketClientProtocol
    ) -> None:

        self.transport_wr: asyncio.Transport = weakref.ref(protocol.transport)
        self.reader_wr: asyncio.StreamReader = weakref.ref(protocol.reader)
        self.state = h11.Connection(our_role=h11.CLIENT)
        self.stream_consumed = False

    @property
    def transport(self) -> asyncio.Transport:
        if self.transport_wr is not None:
            return self.transport_wr()
        return None

    @property
    def reader(self) -> asyncio.StreamReader:
        if self.reader_wr is not None:
            return self.reader_wr()
        return None

    @property
    def cycle_state(self) -> dict:
        return self.state.states

    async def handle_async_request(self, request: Request) -> Response:
        """Send request and receive header portion of response"""
        
        wsuri: WebSocketURI = request[0]
        headers: Headers = request[1]
        target = wsuri.resource_name
        raw_request = self.prep_request(target, headers)
        
        # send request receive headers
        await self.send_request(raw_request)
        event = await self.receive_headers()

        # check HTTP version returned from server, must be 1.1
        if event.http_version != b"1.1":
            msg = f"Invalid HTTP protocol: HTTP {event.http_version.decode()}"
            raise h11.RemoteProtocolError(msg)
        
        status_code = event.status_code
        raw_header = event.headers
        
        # decode and construct response headers
        response_headers = Headers()
        for pair in raw_header:
            header = pair[0].decode()
            val = pair[1].decode()
            response_headers[header] = val
        
        # get ssl socket if this is TLS connection. Can be helpful in some auth flows
        transport = self.transport
        if transport is not None:
            ssl_socket: Union[ssl.SSLSocket, None] = transport.get_extra_info("ssl_object")

        return status_code, response_headers, request, ssl_socket
        

    def prep_request(self, target: str, headers: Headers) -> bytes:
        """Update state and prep request to be sent over wire"""
        logger.debug("Starting req-resp - %s", self.cycle_state)
        event = h11.Request(
            method="GET",
            target=target,
            headers=[(header, val) for header, val in headers.raw_items()]
        )
        return self.state.send(event)

    async def send_request(self, raw_request: bytes) -> None:
        """Write request to transport"""
        transport = self.transport
        if transport is not None:
            transport.write(raw_request)
            self.state.send(h11.EndOfMessage())
            logger.debug("Request sent - %s", self.cycle_state)
            self.stream_consumed = False

    async def receive_headers(self) -> h11.Response:
        """Read only response headers and leave body buffered"""
        while True:
            event = await self.receive_event()
            if isinstance(event, (h11.Response, h11.InformationalResponse)):
                logger.debug("Received headers - %s", self.cycle_state)
                return event
    
    async def receive_body(self) -> bytes:
        """
        Receive the response body. This will be called if we
        are going to do another request-response cycle or the
        response body is required by the auth flow.
        """
        content = b''
        while True:
            event = await self.receive_event()
            if isinstance(event, h11.Data):
                content += bytes(event.data)
            elif isinstance(event, (h11.EndOfMessage, h11.PAUSED)):
                logger.debug("Received body - %s", self.cycle_state)
                self.stream_consumed = True
                return content

    async def receive_event(self) -> bytes:
        """Receives chunk of data from reader"""
        reader = self.reader
        if reader is not None:
            while True:
                event = self.state.next_event()
                if event is h11.NEED_DATA:
                    try:
                        data = await self.reader.readline()
                    except ValueError as err:
                        raise err
                    if data == b"" and self.state.their_state == h11.SEND_RESPONSE:
                        msg = "Server disconnected without sending a response."
                        raise h11.RemoteProtocolError(msg)
                    self.state.receive_data(data)
                else:
                    return event

    async def start_next_cycle(self) -> None:
        """Reset internal state. Consume response body if cycle not complete"""
        if (self.state.our_state is h11.DONE and self.state.their_state is h11.DONE):
            self.state.start_next_cycle()
        elif not self.stream_consumed:
            # if the body wasnt consumed already then we dont need it
            await self.receive_body()
            await self.start_next_cycle()
        else:
            msg = f"Incorrect state - {self.cycle_state})"
            raise h11.LocalProtocolError(msg)
    
    def teardown(self) -> None:
        """Release all references to protocol and remove state"""
        self.transport_wr = None
        self.reader_wr = None
        self.state = None
        self.stream_consumed = False
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        self.teardown()

    

    