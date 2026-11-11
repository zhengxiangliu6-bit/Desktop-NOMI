"""Direct TLS to approved hosts, resolving and pinning public addresses at connect time."""

import ipaddress
import socket
import ssl
from urllib.parse import urlsplit
from urllib.request import getproxies

import anyio
import httpcore
import httpx

from app.core.errors import AppError
from app.settings.models import BAILIAN_ROOTS

ALLOWED_HOSTS = {urlsplit(url).hostname for url in BAILIAN_ROOTS}


class PublicNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, resolver=None, backend=None):
        self.resolver = resolver or anyio.getaddrinfo
        self.backend = backend or httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):  # noqa: ASYNC109
        host = host.decode() if isinstance(host, bytes) else host
        if host not in ALLOWED_HOSTS or port != 443:
            raise httpcore.ConnectError("Destination rejected")
        addresses = await self.resolver(host, port, type=socket.SOCK_STREAM)
        ips = list(dict.fromkeys(item[4][0] for item in addresses))
        if not ips or any(
            not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast
            for ip in ips
        ):
            raise httpcore.ConnectError("Non-public destination rejected")
        # Connect by numeric IP; httpcore retains the original hostname for TLS SNI/cert checks.
        return await self.backend.connect_tcp(
            ips[0],
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(self, *args, **kwargs):
        raise httpcore.ConnectError("Unix destinations rejected")

    async def sleep(self, seconds):
        await anyio.sleep(seconds)


class CoreStream(httpx.AsyncByteStream):
    def __init__(self, stream):
        self.stream = stream

    async def __aiter__(self):
        try:
            async for chunk in self.stream:
                yield chunk
        except httpcore.TimeoutException:
            raise httpx.ReadTimeout("Provider read timeout") from None
        except Exception:
            raise httpx.ReadError("Provider read failed") from None

    async def aclose(self):
        await self.stream.aclose()


class PublicTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(),
            network_backend=PublicNetworkBackend(),
            retries=0,
        )

    async def handle_async_request(self, request):
        if (
            request.url.scheme != "https"
            or request.url.host not in ALLOWED_HOSTS
            or request.url.port not in {None, 443}
            or request.url.path != "/compatible-mode/v1/chat/completions"
        ):
            raise httpx.ConnectError("Destination rejected")
        try:
            response = await self.pool.handle_async_request(
                httpcore.Request(
                    method=request.method,
                    url=httpcore.URL(
                        scheme=request.url.raw_scheme,
                        host=request.url.raw_host,
                        port=request.url.port,
                        target=request.url.raw_path,
                    ),
                    headers=request.headers.raw,
                    content=request.stream,
                    extensions=request.extensions,
                )
            )
        except httpcore.TimeoutException:
            raise httpx.ConnectTimeout("Provider timeout") from None
        except Exception:
            raise httpx.ConnectError("Provider connection rejected") from None
        return httpx.Response(
            response.status,
            headers=response.headers,
            stream=CoreStream(response.stream),
            extensions=response.extensions,
        )

    async def aclose(self):
        await self.pool.aclose()


def secure_client(timeout: float) -> httpx.AsyncClient:
    # Never silently bypass a managed/corporate proxy. Such environments remain env-configured.
    if any(getproxies().get(key) for key in ("http", "https", "all")):
        raise AppError(
            503,
            "SECURE_TRANSPORT_UNAVAILABLE",
            "当前代理环境无法验证配置中心的连接地址，已阻止请求。",
        )
    return httpx.AsyncClient(
        transport=PublicTransport(), timeout=timeout, follow_redirects=False, trust_env=False
    )
