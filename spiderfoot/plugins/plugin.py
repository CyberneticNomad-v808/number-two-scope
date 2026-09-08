"""Re-export of this codebase's real ``SpiderFootPlugin``.

Upstream's own ``spiderfoot/plugins/modern_plugin.py`` does
``from .plugin import SpiderFootPlugin`` to get its base class. This
codebase's actual classic plugin base class lives at the top-level
``spiderfoot.plugin`` module (``spiderfoot/plugin.py``), not under a
``plugins/`` subpackage — this file just points upstream's expected import
path at it, so ``SpiderFootModernPlugin`` ends up subclassing the exact
same ``SpiderFootPlugin`` every native module here already uses. No
reimplementation, no behavioral difference — it's the identical class
object.
"""

from spiderfoot import SpiderFootPlugin

__all__ = ["SpiderFootPlugin"]
