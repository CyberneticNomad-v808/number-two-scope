"""SpiderFoot HTTP request handler module.

This module provides a unified interface for making HTTP requests with
consistent error handling, logging, and proxy support.
"""

import json
import random
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
import urllib3

from spiderfoot.logconfig import get_module_logger
from spiderfoot.error_handling import SpiderFootError, error_handler

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RequestHandler:
    """Handler for making HTTP requests with consistent behavior."""

    def __init__(self, opts: Dict[str, Any] = None):
        """Initialize request handler.

        Args:
            opts (dict): Options for requests including:
                _useragent: User agent string or list of user agent strings
                _fetchtimeout: Timeout in seconds
                _socks1type: SOCKS proxy type
                _socks2addr: SOCKS proxy address
                _socks3port: SOCKS proxy port
                _socks4user: SOCKS proxy username
                _socks5pwd: SOCKS proxy password
        """
        self.log = get_module_logger("request_handler")
        self.opts = opts or {}
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create and configure a requests session.

        Returns:
            requests.Session: Configured session
        """
        session = requests.session()

        # Configure proxy if specified
        if (
            self.opts.get("_socks1type") and
            self.opts.get("_socks2addr") and
            self.opts.get("_socks3port")
        ):
            proxy_type = self.opts.get("_socks1type").lower()
            proxy_addr = self.opts.get("_socks2addr")
            proxy_port = self.opts.get("_socks3port")
            proxy_user = self.opts.get("_socks4user")
            proxy_pass = self.opts.get("_socks5pwd")

            proxy_url = f"{proxy_type}://"
            if proxy_user and proxy_pass:
                proxy_url += f"{proxy_user}:{proxy_pass}@"
            proxy_url += f"{proxy_addr}:{proxy_port}"

            self.log.debug(
                f"Using proxy: {self.sanitize_url_for_logging(proxy_url)}")
            session.proxies = {"http": proxy_url, "https": proxy_url}

        return session

    def get_user_agent(self) -> str:
        """Get a user agent string.

        Returns:
            str: User agent string
        """
        user_agent = self.opts.get(
            "_useragent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0",
        )

        if isinstance(user_agent, list):
            return random.SystemRandom().choice(user_agent)

        # Handle case where useragent is specified as a file or URL
        if isinstance(user_agent, str) and user_agent.startswith("@"):
            user_agents = self._load_user_agents_from_file_or_url(
                user_agent[1:])
            if user_agents:
                return random.SystemRandom().choice(user_agents)

        return user_agent

    def _load_user_agents_from_file_or_url(self, source: str) -> List[str]:
        """Load user agents from a file or URL.

        Args:
            source (str): File path or URL

        Returns:
            list: List of user agent strings
        """
        user_agents = []

        try:
            if source.startswith(("http://", "https://")):
                response = self.fetch_url(source, timeout=5)
                if response and response.get("content"):
                    user_agents = response["content"].decode(
                        "utf-8").splitlines()
            else:
                with open(source, "r") as f:
                    user_agents = [line.strip() for line in f]

            # Remove empty lines and comments
            user_agents = [
                ua for ua in user_agents if ua and not ua.startswith("#")]

            self.log.info(
                f"Loaded {len(user_agents)} user agents from {source}")
        except Exception as e:
            self.log.error(f"Failed to load user agents from {source}: {e}")

        return (
            user_agents
            if user_agents
            else [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0"
            ]
        )

    def sanitize_url_for_logging(self, url: str) -> str:
        """Remove potentially sensitive strings from a URL for logging.

        Args:
            url (str): URL

        Returns:
            str: Sanitized URL
        """
        if not url:
            return url

        try:
            parsed_url = urllib.parse.urlparse(url)

            # Hide password in netloc
            if "@" in parsed_url.netloc:
                netloc_parts = parsed_url.netloc.split("@")
                auth_parts = netloc_parts[0].split(":")
                if len(auth_parts) > 1:
                    # Replace password with asterisks but keep username
                    netloc = f"{auth_parts[0]}:****@{netloc_parts[1]}"
                    parsed_list = list(parsed_url)
                    parsed_list[1] = netloc
                    return urllib.parse.urlunparse(parsed_list)

            # For API keys in query parameters, hide values
            if parsed_url.query:
                sensitive_params = [
                    "api_key",
                    "apikey",
                    "key",
                    "password",
                    "token",
                    "auth",
                    "secret",
                ]
                query_dict = dict(urllib.parse.parse_qsl(parsed_url.query))

                for param in query_dict:
                    if any(
                        sensitive in param.lower() for sensitive in sensitive_params
                    ):
                        query_dict[param] = "****"

                new_query = urllib.parse.urlencode(query_dict)
                parsed_list = list(parsed_url)
                parsed_list[4] = new_query
                return urllib.parse.urlunparse(parsed_list)

        except Exception:
            pass

        return url

    @error_handler
    def fetch_url(
        self,
        url: str,
        cookies: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Any = None,
        method: str = "GET",
        use_session: bool = True,
        verify: bool = True,
        allow_redirects: bool = True,
        retry_times: int = 2,
        retry_pause: float = 1.0,
    ) -> Dict[str, Any]:
        """Fetch a URL and return the content and response headers.

        Args:
            url (str): URL to fetch
            cookies (dict, optional): Cookies
            timeout (int, optional): Timeout in seconds
            headers (dict, optional): Request headers
            data (Any, optional): Request body for POST requests
            method (str, optional): HTTP method (GET, POST, etc.)
            use_session (bool, optional): Whether to use the requests session
            verify (bool, optional): Whether to verify SSL certificates
            allow_redirects (bool, optional): Whether to follow redirects
            retry_times (int, optional): Number of times to retry on failure
            retry_pause (float, optional): Seconds to wait between retries

        Returns:
            dict: Dictionary containing:
                'content': The response content
                'code': The HTTP status code
                'headers': The response headers
                'time': The time taken to fetch the URL
        """
        start_time = time.time()

        if not url:
            return {"content": None, "code": None, "headers": None, "time": 0}

        if not timeout:
            timeout = int(self.opts.get("_fetchtimeout", 30))

        # Prepare headers
        if not headers:
            headers = {}

        if "User-Agent" not in headers:
            headers["User-Agent"] = self.get_user_agent()

        # Log the request (sanitize sensitive info)
        self.log.debug(
            f"Fetching {self.sanitize_url_for_logging(url)} with method {method}"
        )

        # Normalize method
        method = method.upper()

        # Prepare request arguments
        req_args = {
            "timeout": timeout,
            "headers": headers,
            "cookies": cookies,
            "verify": verify,
            "allow_redirects": allow_redirects,
        }

        if method in ["POST", "PUT", "PATCH"]:
            req_args["data"] = data

        # Attempt the request with retries
        response = None
        tries = 0
        exception = None

        while tries <= retry_times:
            try:
                if use_session:
                    request_function = getattr(self.session, method.lower())
                else:
                    request_function = getattr(requests, method.lower())

                response = request_function(url, **req_args)
                break
            except (
                requests.RequestException,
                urllib.error.URLError,
                ssl.SSLError,
            ) as e:
                exception = e
                tries += 1
                if tries <= retry_times:
                    self.log.debug(
                        f"Request to {self.sanitize_url_for_logging(url)} failed: {e}. Retrying ({tries}/{retry_times})..."
                    )
                    time.sleep(retry_pause)
                else:
                    self.log.error(
                        f"Request to {self.sanitize_url_for_logging(url)} failed after {retry_times} retries: {e}"
                    )

        # Calculate time taken
        time_taken = time.time() - start_time

        # Handle case when all requests failed
        if not response and exception:
            return {
                "content": None,
                "code": None,
                "headers": None,
                "time": time_taken,
                "error": str(exception),
            }

        # Process the response
        result = {
            "content": response.content,
            "code": response.status_code,
            "headers": dict(response.headers),
            "time": time_taken,
        }

        return result

    def download_file(self, url: str, local_path: str) -> bool:
        """Download a file from a URL to a local path.

        Args:
            url (str): URL to download
            local_path (str): Local path to save the file

        Returns:
            bool: Whether the download was successful
        """
        try:
            response = self.fetch_url(url, timeout=60)

            if not response or not response.get("content"):
                self.log.error(
                    f"Failed to download from {self.sanitize_url_for_logging(url)}: No content received"
                )
                return False

            if response.get("code") != 200:
                self.log.error(
                    f"Failed to download from {self.sanitize_url_for_logging(url)}: HTTP {response.get('code')}"
                )
                return False

            with open(local_path, "wb") as f:
                f.write(response["content"])

            self.log.debug(
                f"Downloaded {self.sanitize_url_for_logging(url)} to {local_path}"
            )
            return True

        except Exception as e:
            self.log.error(
                f"Failed to download from {self.sanitize_url_for_logging(url)}: {e}"
            )
            return False

    def check_url_exists(self, url: str) -> bool:
        """Check if a URL exists by making a HEAD request.

        Args:
            url (str): URL to check

        Returns:
            bool: Whether the URL exists and is accessible
        """
        try:
            response = self.fetch_url(url, method="HEAD")
            return response.get("code") in [200, 301, 302, 303, 307, 308]
        except Exception:
            return False
