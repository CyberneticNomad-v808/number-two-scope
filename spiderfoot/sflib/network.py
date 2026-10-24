# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         Modular SpiderFoot SFLib Module
# Purpose:      Common functions for working with the database back-end.
#
# Author:      Agostino Panico @poppopjmp
#
# Created:     30/06/2025
# Copyright:   (c) Agostino Panico 2025
# Licence:     MIT
# -------------------------------------------------------------------------------
# Network, DNS, IP, socket, proxy, fetch, etc. utilities
import socket
import ssl
import requests
import OpenSSL
import cryptography
import urllib.parse
import random
from cryptography.hazmat.backends.openssl import backend
from .helpers import validIP, validIP6
from datetime import datetime, timezone


def resolveHost(host: str) -> list:
    """Return a normalised IPv4 resolution of a hostname.

    Note: .onion addresses are NOT resolved here - they must be resolved
    by the Tor network via SOCKS5 proxy. Attempting local DNS resolution
    of .onion addresses will fail and leak privacy.
    """
    import socket
    from .helpers import normalizeDNS
    if not host:
        return []

    # CRITICAL: Never attempt to resolve .onion addresses via regular DNS
    # They can only be resolved through Tor's SOCKS5 proxy
    if host.lower().endswith('.onion'):
        return []

    try:
        # Use gethostbyname_ex for patching/mocking compatibility in tests
        addrs = normalizeDNS(socket.gethostbyname_ex(host))
    except Exception:
        return []
    if not addrs:
        return []
    return list(set(addrs))


def resolveIP(ipaddr: str) -> list:
    """Return a normalised resolution of an IPv4 or IPv6 address as a flat list (not a tuple)."""
    import socket
    from .helpers import normalizeDNS, validIP, validIP6
    if not validIP(ipaddr) and not validIP6(ipaddr):
        return []
    try:
        addrs = normalizeDNS(socket.gethostbyaddr(ipaddr))
    except Exception:
        return []
    if not addrs:
        return []
    return list(set(addrs))


def resolveHost6(hostname: str) -> list:
    """Return IPv6 addresses for a hostname.

    Note: .onion addresses are NOT resolved here - they must be resolved
    by the Tor network via SOCKS5 proxy.
    """
    if not hostname:
        return []

    # CRITICAL: Never attempt to resolve .onion addresses via regular DNS
    if hostname.lower().endswith('.onion'):
        return []

    addrs = []
    try:
        for r in socket.getaddrinfo(hostname, None, socket.AF_INET6):
            addrs.append(r[4][0])
    except Exception:
        return []
    if not addrs:
        return []
    return list(set(addrs))


def validateIP(host: str, ip: str) -> bool:
    if not host:
        return False
    addrs = []
    if validIP(ip):
        addrs = resolveHost(host)
    elif validIP6(ip):
        addrs = resolveHost6(host)
    else:
        return False
    if not addrs:
        return False
    return any(str(addr) == ip for addr in addrs)


def safeSocket(host: str, port: int, timeout: int) -> 'ssl.SSLSocket':
    sock = socket.create_connection((host, int(port)), int(timeout))
    sock.settimeout(int(timeout))
    return sock


def safeSSLSocket(host: str, port: int, timeout: int) -> 'ssl.SSLSocket':
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    s = socket.socket()
    s.settimeout(int(timeout))
    s.connect((host, int(port)))
    sock = context.wrap_socket(s, server_hostname=host)
    sock.do_handshake()
    return sock


def parseCert(rawcert: str, fqdn: str = None, expiringdays: int = 30) -> dict:
    if not rawcert:
        return {}
    ret = {}
    if '\r' in rawcert:
        rawcert = rawcert.replace('\r', '')
    if isinstance(rawcert, str):
        rawcert = rawcert.encode('utf-8')
    cert = cryptography.x509.load_pem_x509_certificate(rawcert, backend)
    sslcert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, rawcert)
    sslcert_dump = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_TEXT, sslcert)
    ret['text'] = sslcert_dump.decode('utf-8', errors='replace')
    ret['issuer'] = str(cert.issuer)
    ret['altnames'] = []
    ret['expired'] = False
    ret['expiring'] = False
    ret['mismatch'] = False
    ret['certerror'] = False
    ret['issued'] = str(cert.subject)
    # Expiry info
    try:
        not_after = cert.not_valid_after
        now = datetime.now(timezone.utc)
        if not_after < now:
            ret['expired'] = True
        elif (not_after - now).days < expiringdays:
            ret['expiring'] = True
    except Exception:
        pass
    # SANs
    try:
        ext = cert.extensions.get_extension_for_class(cryptography.x509.SubjectAlternativeName)
        ret['altnames'] = ext.value.get_values_for_type(cryptography.x509.DNSName)
    except Exception:
        pass
    certhosts = []
    try:
        certhosts.append(cert.subject.get_attributes_for_oid(cryptography.x509.NameOID.COMMON_NAME)[0].value)
        certhosts.extend(ret['altnames'])
    except Exception:
        pass
    # Check for mismatch
    if fqdn and ret['issued']:
        if fqdn not in certhosts:
            ret['mismatch'] = True
    return ret


def getSession() -> 'requests.sessions.Session':
    """Return requests session object.

    Note: Proxy configuration is handled per-request in fetchUrl() via the
    proxies parameter, not at the session level. This allows proper per-URL
    proxy routing based on useProxyForUrl() logic.

    Returns:
        requests.sessions.Session: requests session
    """
    session = requests.session()
    return session


def _default_url_fqdn(u):
    return u


def _default_is_local(ip):
    return False


def useProxyForUrl(url: str, opts=None, urlFQDN=None, isValidLocalOrLoopbackIp=None) -> bool:
    if opts is None:
        return False
    if urlFQDN is None:
        urlFQDN = _default_url_fqdn
    if isValidLocalOrLoopbackIp is None:
        isValidLocalOrLoopbackIp = _default_is_local
    fqdn = urlFQDN(url)
    host = fqdn.lower() if fqdn is not None else ''
    if not opts.get('_socks1type'):
        return False
    proxy_host = opts.get('_socks2addr')
    if not proxy_host:
        return False
    proxy_port = opts.get('_socks3port')
    if not proxy_port:
        return False
    if host == proxy_host.lower():
        return False
    # Localhost and private IPs should not use proxy
    if host in ("localhost", "127.0.0.1", "::1"):
        return False
    if isValidLocalOrLoopbackIp(host):
        return False
    if validIP(host):
        # If it's a valid IP, check if it's local/private
        if isValidLocalOrLoopbackIp(host):
            return False
    return True


def fetchUrl(url: str, cookies: str = None, timeout: int = 30, useragent: str = "SpiderFoot", headers: dict = None, noLog: bool = False, postData: str = None, disableContentEncoding: bool = False, sizeLimit: int = None, headOnly: bool = False, verify: bool = True, proxies: dict = None) -> dict:
    """Fetch URL content with proxy support.

    Args:
        proxies: Dict with 'http' and 'https' keys for proxy configuration.
                 Set to None to use no proxy, or set values to None to explicitly disable proxies.

    Note on DNS Resolution and .onion addresses:
        When using SOCKS5 proxy with the requests library (which uses PySocks under the hood),
        DNS resolution is automatically performed REMOTELY by the SOCKS5 proxy server, NOT locally.
        This is critical for:
          1. .onion addresses - which can ONLY be resolved by Tor's DNS
          2. Privacy - prevents DNS leaks that could expose your queries
          3. Anonymity - keeps all network activity within the Tor network

        The requests library will pass the hostname directly to the SOCKS5 proxy,
        and Tor will resolve it using its internal DNS resolver (DNSPort 8853 in our config).
        We ensure local DNS is never attempted by blocking .onion in resolveHost/resolveHost6.
    """
    if not isinstance(url, str):
        return None
    if not url or not url.strip():
        return None
    url = url.strip()
    try:
        parsed_url = urllib.parse.urlparse(url)
    except Exception:
        return None
    if parsed_url.scheme not in ['http', 'https']:
        return None
    result = {
        'code': None,
        'status': None,
        'content': None,
        'headers': None,
        'realurl': url
    }
    url = url.strip()
    try:
        parsed_url = urllib.parse.urlparse(url)
    except Exception:
        return result
    if parsed_url.scheme not in ['http', 'https']:
        return result
    session = getSession()
    try:
        if headOnly:
            resp = session.head(url, timeout=timeout, headers=headers, verify=verify, proxies=proxies)
        elif postData:
            resp = session.post(url, data=postData, timeout=timeout, headers=headers, verify=verify, proxies=proxies)
        else:
            resp = session.get(url, timeout=timeout, headers=headers, verify=verify, proxies=proxies)
        result['code'] = str(resp.status_code)
        result['status'] = resp.reason
        result['content'] = resp.content.decode('utf-8', errors='replace')
        result['headers'] = {**resp.headers}
        result['realurl'] = resp.url
    except Exception:
        pass
    return result


def checkDnsWildcard(target: str) -> bool:
    if not target:
        return False
    randpool = 'bcdfghjklmnpqrstvwxyz3456789'
    randhost = ''.join([random.SystemRandom().choice(randpool) for _ in range(10)])
    if not resolveHost(randhost + "." + target):
        return False
    return True
