"""SpiderFoot: Open Source Intelligence Automation."""

# Import base components that don't have dependencies on other modules
from .db import SpiderFootDb
from .event import SpiderFootEvent
from .helpers import SpiderFootHelpers
from .threadpool import SpiderFootThreadPool
# Now we can safely import the plugin module
from .plugin import SpiderFootPlugin
from .logger import logListenerSetup, logWorkerSetup
from spiderfoot.__version__ import __version__  # noqa

# Expose these classes/functions at the package level
# but import them in functions where needed
SpiderFootCorrelator = None
SpiderFootTarget = None
MispIntegration = None


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
    return SpiderFootHelpers


def get_misp_integration(dbh):
    """Initialize and return a MISP integration object.

    This avoids circular imports by importing the module only when needed.

    Args:
        dbh (SpiderFootDb): database handle

    Returns:
        MispIntegration: MISP integration object
    """
    global MispIntegration
    if MispIntegration is None:
        from spiderfoot.misp_integration import MispIntegration as MIIntegration

        MispIntegration = MIIntegration
    return MispIntegration(dbh)


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
    "MispIntegration"
]
