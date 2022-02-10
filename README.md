# WS_Auth
Custom protocol for python websockets client that supports HTTPX style auth flows
## Background
ws_auth is a simple package that extends the WebSocketClientProtocol class from [websockets](https://github.com/aaugustin/websockets) to support [HTTPX](https://www.python-httpx.org/advanced/#customizing-authentication)  style auth flows. ws_auth requires no setup other than an import statement, you can use the base websockets package as is with the additional option of adding auth flows
## Installation
You can install ws_auth via pip

    pip install ws-auth
## Usage
### Basic
Using ws_auth with websockets is as simple as importing it

    import websockets
    import ws_auth
	
	async def main():
		async with websockets.connect("wss://example.com") as client:
			data = await client.recv()
			print(type(client))
ws_auth does not require you to pass the `create_protocol` argument to `connect()` to use the `WebsocketAuthProtocol`, it is used automatically. Of course you can still pass the `create_protocol` method if you want to extend the `WebsocketAuthProtocol`
### Auth Flows
By default, the base `Auth` class is used in the `WebsocketAuthProtocol` instance. This is equivalent to no authentication. However, you can implement your own auth flows by inheriting from Auth and overwriting the auth_flow method.

    import websockets
    import ws_auth
    from ws_auth import Auth
	
	class ExampleAuth(Auth):
		requires_response_body = False
		"""
		To implement a custom authentication scheme, subclass `Auth` and override
		the `.auth_flow()` method. If the authentication scheme does I/O such as disk access
		or network calls, or uses synchronization primitives such as locks, you should override
		`.async_auth_flow()` instead of `.auth_flow()` to provide specialized implementations that
		will be used by `WebsocketAuthProtocol`.
		
		Additional Notes
		- A dispatched request must have the signature Tuple[WebSocketURI, Headers]
		- Responses sent back to the flow generator have the signature 
		Tuple[StatusCode, ResponseHeaders, Request, Union[SSLSocket, None], Optional[Body]]
		
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
			response = yield request
			status_code = response[0]
			wsuri = request[0]
			if status_code != 101:
				print(f"auth_flow failed with status code {status_code} for uri {wsuri}")
			else:
				print(f"auth_flow succeeded with status code {status_code} for uri {wsuri}")
			return
	
	# use the auth flow
	async def main():
		auth = ExampleAuth()
		async with websockets.connect("wss://example.com", auth=auth) as client:
			data = await client.recv()
## Additional Notes

 - The authentication is handled during the opening handshake step of the websocket connection
 - websockets natively supports redirects, auth flows are always restarted if a redirect occurs and the Authorization header is stripped from the request
## Supports
 - python >=3.7
 - websockets==10.1

		

