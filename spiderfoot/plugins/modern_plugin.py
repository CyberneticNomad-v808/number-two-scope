#!/usr/bin/env python3
# -------------------------------------------------------------------------------
# Name:         modern_plugin
# Purpose:      Compatibility port of upstream (poppopjmp/spiderfoot)
#               SpiderFootModernPlugin, adapted to run on this codebase.
#
#               Upstream's version integrates an extracted service layer
#               (HttpService, DnsService, CacheService, DataService,
#               EventBus, Prometheus metrics) that doesn't exist here. This
#               port keeps upstream's full public API (so ported modules'
#               code doesn't need to change) but relies entirely on
#               upstream's own documented fallback behavior: every
#               service accessor already returns None and every metrics
#               hook already no-ops when its backing subsystem isn't
#               present. Existing modules continue to work unchanged via
#               self.sf, exactly as upstream's own docstring promises.
#
#               Two upstream imports were dropped rather than reimplemented,
#               because nothing in the modules this shim targets needs them:
#                 - spiderfoot.config.constants.DEFAULT_TTL_ONE_HOUR
#                   -> inlined as a local constant (same value, 3600s).
#                 - spiderfoot.scan.scan_state_map.DB_STATUS_FINISHED
#                   -> inlined as a local constant matching this codebase's
#                      own queue sentinel (spiderfoot/plugin.py uses the
#                      literal string 'FINISHED'). Only reachable if a
#                      subclass re-enables _enable_metrics (see below).
#
#               Metrics are off by default here (_enable_metrics = False)
#               since spiderfoot.observability.metrics doesn't exist in
#               this codebase. With metrics disabled, threadWorker() falls
#               straight through to the real SpiderFootPlugin.threadWorker()
#               inherited from this codebase's own engine — ported modules
#               run on the exact same scan loop as native ones.
#
# Original Author: Van1sh (upstream, poppopjmp/spiderfoot)
# Ported:          2026-09-08
# Licence:         MIT (matches upstream)
# -------------------------------------------------------------------------------

"""
SpiderFoot Modern Plugin Base (ported)

Extends this codebase's ``SpiderFootPlugin`` with the same optional
service-accessor / metrics-hook surface upstream modules expect, all of
which gracefully degrade to legacy ``self.sf`` behavior here.

Usage (new-style module, unchanged from upstream)::

    from spiderfoot.plugins.modern_plugin import SpiderFootModernPlugin

    class sfp_example(SpiderFootModernPlugin):
        meta = { ... }

        def setup(self, sfc, userOpts=dict()):
            super().setup(sfc, userOpts)

        def handleEvent(self, event):
            result = self.fetch_url("https://api.example.com/lookup")
            # falls back to self.sf.fetchUrl() here — no HttpService exists
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .plugin import SpiderFootPlugin

# Inlined in place of spiderfoot.config.constants.DEFAULT_TTL_ONE_HOUR
DEFAULT_TTL_ONE_HOUR = 3600

# Inlined in place of spiderfoot.scan.scan_state_map.DB_STATUS_FINISHED.
# Matches this codebase's own queue sentinel (see spiderfoot/plugin.py).
DB_STATUS_FINISHED = "FINISHED"


log = logging.getLogger("spiderfoot.modern_plugin")


class SpiderFootModernPlugin(SpiderFootPlugin):
    """
    Enhanced SpiderFootPlugin with first-class service integration.

    Provides:
        - self.http → HttpService (extracted HTTP client) — always None here
        - self.dns  → DnsService (extracted DNS resolver) — always None here
        - self.cache → CacheService (extracted cache layer) — always None here
        - self.data  → DataService (extracted DB layer) — always None here
        - self.event_bus → EventBus (publish/subscribe) — always None here
        - self.emit_metric() → Prometheus metrics — no-op here

    Every accessor above resolves to None (no service registry exists in
    this codebase) and every convenience method (fetch_url, resolve_host,
    cache_get, ...) falls back to the equivalent self.sf.* call, exactly
    as upstream's own fallback logic already does.
    """

    # Off by default: spiderfoot.observability.metrics doesn't exist here.
    _enable_metrics = False

    def __init__(self) -> None:
        """Initialize the SpiderFootModernPlugin."""
        super().__init__()
        self._registry = None
        self._http_service = None
        self._dns_service = None
        self._cache_service = None
        self._data_service = None
        self._event_bus = None
        self._log = None

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    @property
    def log(self) -> logging.Logger:
        """Module-specific logger."""
        if self._log is None:
            name = getattr(self, "__name__", None) or self.__class__.__name__
            self._log = logging.getLogger(f"spiderfoot.module.{name}")
        return self._log

    # ------------------------------------------------------------------
    # Setup (called by scan engine)
    # ------------------------------------------------------------------

    def setup(self, sfc: Any, userOpts: dict | None = None) -> None:
        """Initialize the module with SpiderFoot facade and user options.

        Extends the legacy setup to also try to resolve services from a
        registry, if one is ever added later. Today, spiderfoot.service_registry
        doesn't exist in this codebase, so this always resolves to
        self._registry = None and every service accessor below returns None.
        """
        if userOpts is None:
            userOpts = {}

        # Set self.sf and merge user opts (legacy parent setup is a no-op)
        self.sf = sfc
        for opt in list(userOpts.keys()):
            self.opts[opt] = userOpts[opt]

        # Try to attach to a service registry, if one ever exists.
        try:
            from spiderfoot.service_registry import get_registry
            self._registry = get_registry()
        except ImportError:
            self._registry = None

    # ------------------------------------------------------------------
    # Binary preflight check (Item 7 of the correlation/module refactor)
    # ------------------------------------------------------------------

    def check_binary(self, opt_name: str, required: bool = True) -> bool:
        """Verify a configured tool-path option points at a real,
        executable file, and set self.errorState immediately if not.

        Ported tool-wrapper modules (sfp_httpx, sfp_tool_dnsx, etc.) used
        to only discover a missing binary lazily, on the first matching
        handleEvent() call -- logging an error there and setting
        errorState, which silently makes the module inert for the rest of
        the scan with no upfront signal. Call this from setup() instead so
        a bad path fails immediately and visibly, before the scan starts
        depending on the module.

        Args:
            opt_name: the self.opts key holding the configured path
                (e.g. 'httpx_path').
            required: if True (default) and the path is missing/not
                executable, sets self.errorState = True and logs an
                error. If False, only logs a debug note (for genuinely
                optional tools) and returns the check result without
                marking the module as errored.

        Returns:
            True if the path exists and is executable, False otherwise.
        """
        import os
        import shutil

        path = (self.opts.get(opt_name, '') or '').strip()
        if not path:
            # No explicit path configured -- try resolving the option's
            # implied binary name on $PATH as a last resort (matches how
            # each module's own lazy _find_* helper already behaves).
            guessed_name = opt_name.rsplit('_path', 1)[0]
            resolved = shutil.which(guessed_name)
            if resolved:
                return True
            msg = f"No {opt_name} configured and '{guessed_name}' not found on PATH"
        elif not (os.path.isfile(path) and os.access(path, os.X_OK)):
            msg = f"{opt_name} is set to '{path}' but that file doesn't exist or isn't executable"
        else:
            return True

        if required:
            self.log.error(f"[{self.__class__.__name__}] {msg}; module will not run this scan.")
            self.errorState = True
        else:
            self.log.debug(f"[{self.__class__.__name__}] {msg} (optional, continuing).")
        return False

    # ------------------------------------------------------------------
    # Service accessors (lazy resolution — always None in this codebase)
    # ------------------------------------------------------------------

    @property
    def http(self) -> Any | None:
        """Access the HttpService."""
        if self._http_service is None:
            self._http_service = self._get_service("http")
        return self._http_service

    @property
    def dns(self) -> Any | None:
        """Access the DnsService."""
        if self._dns_service is None:
            self._dns_service = self._get_service("dns")
        return self._dns_service

    @property
    def cache(self) -> Any | None:
        """Access the CacheService."""
        if self._cache_service is None:
            self._cache_service = self._get_service("cache")
        return self._cache_service

    @cache.setter
    def cache(self, value: Any) -> None:
        """Set a custom cache implementation."""
        self._cache_service = value

    @property
    def data(self) -> Any | None:
        """Access the DataService."""
        if self._data_service is None:
            self._data_service = self._get_service("data")
        return self._data_service

    @property
    def event_bus(self) -> Any | None:
        """Access the EventBus."""
        if self._event_bus is None:
            self._event_bus = self._get_service("event_bus")
        return self._event_bus

    def _get_service(self, name: str):
        """Resolve a service from the registry, returning None if unavailable."""
        if self._registry is None:
            return None
        try:
            from spiderfoot.service_registry import (
                SERVICE_HTTP, SERVICE_DNS, SERVICE_CACHE,
                SERVICE_DATA, SERVICE_EVENT_BUS,
            )
            mapping = {
                "http": SERVICE_HTTP,
                "dns": SERVICE_DNS,
                "cache": SERVICE_CACHE,
                "data": SERVICE_DATA,
                "event_bus": SERVICE_EVENT_BUS,
            }
            svc_name = mapping.get(name)
            if svc_name and self._registry.has(svc_name):
                return self._registry.get(svc_name)
        except (KeyError, AttributeError):
            pass
        return None

    # ------------------------------------------------------------------
    # Modern convenience methods (delegate to services or fallback)
    # ------------------------------------------------------------------

    def fetch_url(self, url: str, method: str = "GET",
                  headers: dict | None = None,
                  data: Any | None = None,
                  timeout: int = 30,
                  use_cache: bool = True,
                  cache_ttl: int = DEFAULT_TTL_ONE_HOUR,
                  **kwargs) -> dict | None:
        """Fetch a URL using HttpService (or fallback to self.sf.fetchUrl).

        Accepts all legacy fetchUrl kwargs (useragent, postData, etc.)
        and passes them through automatically.

        Returns a dict with keys: content, code, headers, realurl, status
        """
        t0 = time.monotonic()
        try:
            if self.http is not None:
                svc_kwargs: dict[str, Any] = dict(kwargs)
                svc_kwargs["headers"] = headers
                svc_kwargs["timeout"] = timeout
                if data is not None:
                    svc_kwargs["post_data"] = data
                if method and method.upper() == "HEAD":
                    svc_kwargs["head_only"] = True
                if "postData" in svc_kwargs:
                    svc_kwargs.setdefault("post_data", svc_kwargs.pop("postData"))
                if "headOnly" in svc_kwargs:
                    svc_kwargs.setdefault("head_only", svc_kwargs.pop("headOnly"))
                if "sizeLimit" in svc_kwargs:
                    svc_kwargs.setdefault("size_limit", svc_kwargs.pop("sizeLimit"))
                if "disableContentEncoding" in svc_kwargs:
                    svc_kwargs.setdefault("disable_content_encoding",
                                          svc_kwargs.pop("disableContentEncoding"))
                for _drop in ("method", "data", "use_cache", "cache_ttl",
                              "noLog", "dontMaskPassword", "fatal",
                              "useragent_for_page"):
                    svc_kwargs.pop(_drop, None)
                result = self.http.fetch_url(url, **svc_kwargs)
                self._record_http_metric(method, result.get("code", 0), t0)
                return result

            # Fallback (always taken here) — translate modern kwargs to legacy API
            if hasattr(self, "sf") and self.sf:
                legacy_kwargs = dict(kwargs)
                legacy_kwargs["timeout"] = timeout
                if data is not None:
                    legacy_kwargs["postData"] = data
                if method == "HEAD":
                    legacy_kwargs["headOnly"] = True
                result = self.sf.fetchUrl(url, **legacy_kwargs)
                self._record_http_metric(method, 200, t0)
                return result

        except Exception as e:
            self.log.error("fetch_url error: %s", e)
            self._record_http_metric(method, 0, t0)

        return None

    def resolve_host(self, hostname: str) -> list[str]:
        """Resolve a hostname to IPv4 addresses."""
        try:
            if self.dns is not None:
                return self.dns.resolve_host(hostname)

            if hasattr(self, "sf") and self.sf:
                return self.sf.resolveHost(hostname) or []

        except Exception as e:
            self.log.error("resolve_host error: %s", e)

        return []

    def resolve_host6(self, hostname: str) -> list[str]:
        """Resolve a hostname to IPv6 addresses."""
        try:
            if self.dns is not None:
                return self.dns.resolve_host6(hostname)

            if hasattr(self, "sf") and self.sf:
                return self.sf.resolveHost6(hostname) or []

        except Exception as e:
            self.log.error("resolve_host6 error: %s", e)

        return []

    def reverse_resolve(self, ip_address: str) -> list[str]:
        """Reverse-resolve an IP address."""
        try:
            if self.dns is not None:
                return self.dns.reverse_resolve(ip_address)

            if hasattr(self, "sf") and self.sf:
                return self.sf.resolveIP(ip_address) or []

        except Exception as e:
            self.log.error("reverse_resolve error: %s", e)

        return []

    def cache_get(self, key: str, ttl: int = 0) -> Any | None:
        """Get a value from the cache.

        Args:
            key: Cache key to look up.
            ttl: Cache TTL in hours (used by legacy cacheGet; ignored by dict cache).
        """
        try:
            if self.cache is not None:
                return self.cache.get(key)

            if hasattr(self, "sf") and self.sf:
                return self.sf.cacheGet(key, ttl or 24)

        except (KeyError, OSError) as e:
            self.log.debug("cache_get error for %s: %s", key, e)

        return None

    def cache_put(self, key: str, value: Any, ttl: int = DEFAULT_TTL_ONE_HOUR) -> bool:
        """Put a value into the cache."""
        try:
            if self.cache is not None:
                self.cache.put(key, value, ttl=ttl)
                return True

            if hasattr(self, "sf") and self.sf:
                self.sf.cachePut(key, value)
                return True

        except (TypeError, ValueError, OSError) as e:
            self.log.debug("cache_put error for %s: %s", key, e)

        return False

    def store_event(self, event: Any) -> None:
        """Store an event to the data service. No-op here (data service
        never exists) — the scan engine already handles storage the
        legacy way, matching upstream's own documented legacy path."""
        try:
            if self.data is not None:
                self.data.event_store({
                    "scan_id": self.getScanId(),
                    "event_type": event.eventType,
                    "data": event.data,
                    "module": self.__name__,
                    "source_event": getattr(event, "sourceEventHash", ""),
                })
                return
            # Legacy: scan engine handles storage
        except Exception as e:
            self.log.error("store_event error: %s", e)

    def publish_event(self, topic: str, data: Any) -> None:
        """Publish an event to the event bus. No-op here (no event bus)."""
        try:
            if self.event_bus is not None:
                self.event_bus.publish(topic, data)
        except (AttributeError, RuntimeError) as e:
            self.log.debug("publish_event error for %s: %s", topic, e)

    # ------------------------------------------------------------------
    # Enhanced event dispatch with metrics (no-op unless _enable_metrics)
    # ------------------------------------------------------------------

    def notifyListeners(self, sfEvent: Any) -> None:
        """Override to add metrics instrumentation, then delegate."""
        self._record_event_produced(sfEvent.eventType)
        super().notifyListeners(sfEvent)

    # NOTE: upstream also overrides sendEvent() here. This codebase's own
    # SpiderFootPlugin doesn't define sendEvent() at all (confirmed: no
    # module in this port set calls it either), so that override was
    # dropped rather than crashing on a super() call to a nonexistent
    # method. Ported modules use notifyListeners(), which does exist.

    # ------------------------------------------------------------------
    # Metrics helpers — all no-ops: spiderfoot.observability doesn't exist
    # ------------------------------------------------------------------

    def _record_http_metric(self, method: str, status_code: int,
                            start_time: float) -> None:
        if not self._enable_metrics:
            return
        try:
            from spiderfoot.observability.metrics import HTTP_REQUESTS, HTTP_DURATION
            HTTP_REQUESTS.labels(
                method=method, status_code=str(status_code)
            ).inc()
            HTTP_DURATION.observe(time.monotonic() - start_time)
        except ImportError:
            pass

    def _record_event_produced(self, event_type: str) -> None:
        if not self._enable_metrics:
            return
        try:
            from spiderfoot.observability.metrics import EVENTS_PRODUCED
            EVENTS_PRODUCED.labels(event_type=event_type).inc()
        except ImportError:
            pass

    def _record_module_duration(self, duration: float) -> None:
        if not self._enable_metrics:
            return
        try:
            from spiderfoot.observability.metrics import MODULE_DURATION, EVENTS_PROCESSED
            MODULE_DURATION.observe(duration)
            EVENTS_PROCESSED.labels(module=self.__name__).inc()
        except ImportError:
            pass

    def _record_module_error(self, error_type: str) -> None:
        if not self._enable_metrics:
            return
        try:
            from spiderfoot.observability.metrics import MODULE_ERRORS
            MODULE_ERRORS.labels(
                module=self.__name__, error_type=error_type
            ).inc()
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # threadWorker: with metrics disabled (the default here), this falls
    # straight through to SpiderFootPlugin.threadWorker() — the real scan
    # engine's own loop. Ported modules run on the exact same thread loop
    # as native modules. The instrumented loop below only activates if a
    # subclass sets _enable_metrics = True *and* wires up
    # spiderfoot.observability.metrics itself.
    # ------------------------------------------------------------------

    def threadWorker(self) -> None:
        """Instrumented handleEvent loop — inactive unless _enable_metrics
        is explicitly re-enabled by a subclass with a real metrics backend."""
        if not self._enable_metrics:
            super().threadWorker()
            return

        import queue

        while True:
            if self.checkForStop():
                break

            try:
                sfEvent = self.incomingEventQueue.get(timeout=1)
            except queue.Empty:
                continue

            if sfEvent is None:
                break

            if sfEvent == DB_STATUS_FINISHED:
                self.log.debug(
                    "%s.threadWorker() got FINISHED from incomingEventQueue.",
                    self.__name__,
                )
                try:
                    self.finish()
                except Exception as e:
                    self.log.error("Module %s finish() failed: %s", self.__name__, e)
                self.incomingEventQueue.task_done()
                continue

            self._currentEvent = sfEvent

            try:
                t0 = time.monotonic()
                self.handleEvent(sfEvent)
                self._record_module_duration(time.monotonic() - t0)
            except Exception as e:
                self.log.error("Module %s failed: %s", self.__name__, e)
                self._record_module_error(type(e).__name__)
                self.errorState = True

            self.incomingEventQueue.task_done()

    # ------------------------------------------------------------------
    # Module info
    # ------------------------------------------------------------------

    def asdict(self) -> dict:
        """Enhanced module serialization with service status."""
        d = super().asdict()
        d["modern_plugin"] = True
        d["services"] = {
            "http": self.http is not None,
            "dns": self.dns is not None,
            "cache": self.cache is not None,
            "data": self.data is not None,
            "event_bus": self.event_bus is not None,
        }
        return d
