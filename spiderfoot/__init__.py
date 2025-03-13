"""SpiderFoot: Open Source Intelligence Automation."""

# Break circular imports by exposing specific parts at top level
# without importing the full modules
from .threadpool import SpiderFootThreadPool
from .plugin import SpiderFootPlugin
from .logger import logListenerSetup, logWorkerSetup
from spiderfoot.version import __version__  # noqa

# Expose these classes/functions at the package level
# but import them in functions where needed
SpiderFootDb = None
SpiderFootHelpers = None
SpiderFootCorrelator = None
SpiderFootTarget = None


def set_target(target_value, target_type):
    """Initialize and return a target object.

    This avoids circular imports by importing the module only when needed.

    Args:
        target_value (str): target value
        target_type (str): target type

    Returns:
        SpiderFootTarget: target object
    """
    global SpiderFootTarget
    if SpiderFootTarget is None:
        from spiderfoot.target import SpiderFootTarget as SFTarget

        SpiderFootTarget = SFTarget
    return SpiderFootTarget(target_value, target_type)


def get_db(opts):
    """Initialize and return a database object.

    This avoids circular imports by importing the module only when needed.

    Args:
        opts (dict): options

    Returns:
        SpiderFootDb: database object
    """
    global SpiderFootDb
    if SpiderFootDb is None:
        from spiderfoot.db import SpiderFootDb as SFDb

        SpiderFootDb = SFDb
    return SpiderFootDb(opts)


def get_correlator(dbh, rules, scan_id):
    """Initialize and return a correlator object.

    This avoids circular imports by importing the module only when needed.

    Args:
        dbh (SpiderFootDb): database handle
        rules (list): correlation rules
        scan_id (str): scan ID

    Returns:
        SpiderFootCorrelator: correlator object
    """
    global SpiderFootCorrelator
    if SpiderFootCorrelator is None:
        from spiderfoot.correlation import SpiderFootCorrelator as SFCorrelator

        SpiderFootCorrelator = SFCorrelator
    return SpiderFootCorrelator(dbh, rules, scan_id)


def get_helpers():
    """Get helpers module.

    This avoids circular imports by importing the module only when needed.

    Returns:
        SpiderFootHelpers: helpers object
    """
    global SpiderFootHelpers
    if SpiderFootHelpers is None:
        from spiderfoot.helpers import SpiderFootHelpers as SFHelpers

        SpiderFootHelpers = SFHelpers
    return SpiderFootHelpers


class SpiderFootStaticJS:
    """
    SpiderFoot static JavaScript class to handle JS dependencies
    """

    def __init__(self):
        self.js_resources = {}

    def add_resource(self, name, content):
        """
        Add a JavaScript resource
        """
        self.js_resources[name] = content

    def get_resource(self, name):
        """
        Get a JavaScript resource by name
        """
        if name in self.js_resources:
            return self.js_resources[name]
        return None


__all__ = [
    "SpiderFootDb",
    "SpiderFootEvent",
    "SpiderFootHelpers",
    "SpiderFootPlugin",
    "SpiderFootTarget",
    "logListenerSetup",
    "logWorkerSetup",
    "SpiderFootThreadPool",
    "SpiderFootCorrelator",
]
