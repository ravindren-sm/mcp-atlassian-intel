"""SSL and proxy utility functions for MCP Atlassian."""

import logging
import os
import ssl
from typing import Any
from urllib.parse import urlparse

from requests import PreparedRequest, Response
from requests.adapters import HTTPAdapter
from requests.sessions import Session
from requests.utils import should_bypass_proxies
from urllib3.poolmanager import PoolManager

logger = logging.getLogger("mcp-atlassian")


class NoProxyAdapter(HTTPAdapter):
    """HTTP adapter that respects NO_PROXY environment variable.

    A custom transport adapter that ensures NO_PROXY is honored even when
    proxies are explicitly configured on the session. By default, the requests
    library only checks NO_PROXY during auto-detection from environment variables,
    not when proxies are explicitly set on session.proxies.
    """

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float, float] | None = None,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
        proxies: dict[str, str] | None = None,
    ) -> Response:
        """Send a request, respecting NO_PROXY environment variable."""
        no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
        if request.url and proxies and no_proxy and should_bypass_proxies(request.url, no_proxy):
            logger.debug(
                f"Bypassing proxy for {request.url} due to NO_PROXY setting: {no_proxy}"
            )
            proxies = None

        return super().send(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )


class SSLIgnoreAdapter(NoProxyAdapter):
    """HTTP adapter that ignores SSL verification and respects NO_PROXY.

    A custom transport adapter that:
    1. Disables SSL certificate verification for specific domains
    2. Respects NO_PROXY environment variable even when proxies are explicitly set

    This implementation ensures that both verify_mode is set to CERT_NONE and check_hostname
    is disabled, which is required for properly ignoring SSL certificates.

    Note that this reduces security and should only be used when absolutely necessary.
    """

    def init_poolmanager(
        self, connections: int, maxsize: int, block: bool = False, **pool_kwargs: Any
    ) -> None:
        """Initialize the connection pool manager with SSL verification disabled."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=context,
            **pool_kwargs,
        )

    def cert_verify(self, conn: Any, url: str, verify: bool, cert: Any | None) -> None:
        """Override cert verification to disable SSL verification."""
        super().cert_verify(conn, url, verify=False, cert=cert)

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float, float] | None = None,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
        proxies: dict[str, str] | None = None,
    ) -> Response:
        """Send a request with SSL verification disabled."""
        # Let parent class handle NO_PROXY, but always disable SSL verification
        return super().send(
            request,
            stream=stream,
            timeout=timeout,
            verify=False,
            cert=cert,
            proxies=proxies,
        )


def configure_proxy_bypass(
    service_name: str,
    url: str,
    session: Session,
) -> None:
    """Configure the session to respect NO_PROXY environment variable."""
    no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
    if no_proxy:
        logger.debug(
            f"{service_name}: Configuring proxy bypass adapter for NO_PROXY={no_proxy}"
        )
        domain = urlparse(url).netloc
        adapter = NoProxyAdapter()
        session.mount(f"https://{domain}", adapter)
        session.mount(f"http://{domain}", adapter)


def configure_ssl_verification(
    service_name: str,
    url: str,
    session: Session,
    ssl_verify: bool,
    client_cert: str | None = None,
    client_key: str | None = None,
    client_key_password: str | None = None,
) -> None:
    """Configure SSL verification and client certificates for a specific service."""
    if isinstance(client_cert, str) and isinstance(client_key, str):
        if isinstance(client_key_password, str) and client_key_password:
            raise ValueError(
                f"{service_name} client certificate authentication with encrypted "
                "private keys is not supported. Please decrypt your private key first "
                "(e.g., using 'openssl rsa -in encrypted.key -out decrypted.key')."
            )
        session.cert = (client_cert, client_key)
        logger.info(
            f"{service_name} client certificate authentication configured "
            f"with cert: {client_cert}"
        )

    domain = urlparse(url).netloc

    if not ssl_verify:
        logger.warning(
            f"{service_name} SSL verification disabled. This is insecure and should only be used in testing environments."
        )
        # SSLIgnoreAdapter also handles NO_PROXY via its NoProxyAdapter parent
        adapter = SSLIgnoreAdapter()
        session.mount(f"https://{domain}", adapter)
        session.mount(f"http://{domain}", adapter)
    else:
        # Even with SSL verification enabled, ensure NO_PROXY is respected
        no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
        if no_proxy:
            logger.debug(
                f"{service_name}: Mounting proxy bypass adapter for NO_PROXY={no_proxy}"
            )
            adapter = NoProxyAdapter()
            session.mount(f"https://{domain}", adapter)
            session.mount(f"http://{domain}", adapter)
