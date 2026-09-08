"""Compatibility shim for upstream (poppopjmp/spiderfoot) "modern" module
base classes (``SpiderFootModernPlugin`` / ``SpiderFootAsyncPlugin``).

This package exists so that modules written against the upstream
microservices-era plugin API can be dropped into this codebase's
``modules/`` directory unmodified. It does **not** reimplement upstream's
service-registry / observability / event-bus subsystems; those subsystems
don't exist here. Instead it relies on the fact that upstream's own
``SpiderFootModernPlugin`` and ``SpiderFootAsyncPlugin`` were explicitly
designed to gracefully fall back to plain synchronous ``self.sf.*`` calls
when no service registry is configured, and to no-op their optional
Prometheus metrics hooks when metrics aren't available.

See ``plugin.py``, ``modern_plugin.py`` and ``async_plugin.py`` in this
package for the specifics of what was kept, what was trimmed, and why.
"""
