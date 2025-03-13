#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         sf
# Purpose:      Main wrapper for calling all SpiderFoot modules
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     03/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     MIT
# -------------------------------------------------------------------------------

import argparse
import cherrypy
import logging
import multiprocessing as mp
import os
import signal
import sys
from copy import deepcopy
from cherrypy.lib import auth_digest
from typing import Any, Dict, List, Optional, Union

from sflib import SpiderFoot
from sfscan import startSpiderFootScanner
from sfwebui import SpiderFootWebUi
from spiderfoot import (
    SpiderFootHelpers,
    SpiderFootDb,
    SpiderFootCorrelator,
    SpiderFootTarget,
)
from spiderfoot.logconfig import (
    configure_root_logger,
    get_module_logger,
    get_log_paths,
    setup_file_logging,
)
from spiderfoot.error_handling import (
    handle_exception,
    SpiderFootError,
    SpiderFootConfigError,
)
from spiderfoot import __version__

# Get main application logger
log = get_module_logger("sf")

# 'Global' configuration options
# These can be overriden on a per-module basis, and some will
# be overridden from saved configuration settings stored in the DB.
sfConfig = {
    "_debug": False,  # Debug
    "_maxthreads": 3,  # Number of modules to run concurrently
    "__logging": True,  # Logging in general
    "__outputfilter": None,  # Event types to filter from modules' output
    # User-Agent to use for HTTP requests
    "_useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0",
    "_dnsserver": "",  # Override the default resolver
    "_fetchtimeout": 5,  # number of seconds before giving up on a fetch
    "_internettlds": "https://publicsuffix.org/list/effective_tld_names.dat",
    "_internettlds_cache": 72,
    "_genericusers": ",".join(
        SpiderFootHelpers.usernamesFromWordlists(["generic-usernames"])
    ),
    "__database": f"{SpiderFootHelpers.dataPath()}/spiderfoot.db",
    "__modules__": None,  # List of modules. Will be set after start-up.
    # List of correlation rules. Will be set after start-up.
    "__correlationrules__": None,
    "_socks1type": "",
    "_socks2addr": "",
    "_socks3port": "",
    "_socks4user": "",
    "_socks5pwd": "",
}

sfOptdescs = {
    "_debug": "Enable debugging?",
    "_maxthreads": "Max number of modules to run concurrently",
    "_useragent": "User-Agent string to use for HTTP requests. Prefix with an '@' to randomly select the User Agent from a file containing user agent strings for each request, e.g. @C:\\useragents.txt or @/home/bob/useragents.txt. Or supply a URL to load the list from there.",
    "_dnsserver": "Override the default resolver with another DNS server. For example, 8.8.8.8 is Google's open DNS server.",
    "_fetchtimeout": "Number of seconds before giving up on a HTTP request.",
    "_internettlds": "List of Internet TLDs.",
    "_internettlds_cache": "Hours to cache the Internet TLD list. This can safely be quite a long time given that the list doesn't change too often.",
    "_genericusers": "List of usernames that if found as usernames or as part of e-mail addresses, should be treated differently to non-generics.",
    "_socks1type": "SOCKS Server Type. Can be '4', '5', 'HTTP' or 'TOR'",
    "_socks2addr": "SOCKS Server IP Address.",
    "_socks3port": "SOCKS Server TCP Port. Usually 1080 for 4/5, 8080 for HTTP and 9050 for TOR.",
    "_socks4user": "SOCKS Username. Valid only for SOCKS4 and SOCKS5 servers.",
    "_socks5pwd": "SOCKS Password. Valid only for SOCKS5 servers.",
    # This is a hack to get a description for an option not actually available.
    "_modulesenabled": "Modules enabled for the scan.",
}


def main() -> None:
    """Main program entry point."""
    args = parse_args()

    try:
        # Configure logging based on debug flag
        configure_root_logger(debug=args.debug)

        # Set up file logging if needed
        log_paths = get_log_paths()
        setup_file_logging(log_paths["debug"], level=logging.DEBUG)

        # Initialize multiprocessing logging queue
        loggingQueue = mp.Queue()

        if args.debug:
            sfConfig["_debug"] = True
            log.info("Debug enabled")

        # Load modules
        if not load_modules(sfConfig):
            return

        # Start a scan
        if args.start:
            start_scan(sfConfig, args, loggingQueue)
            return

        # Start the web server
        if args.nowebserver:
            log.info("Web server disabled.")
            return

        # Prompt for input if we're not starting a scan
        if not args.start and not args.nowebserver:
            start_web_server(sfConfig, loggingQueue=loggingQueue)

    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    except SpiderFootError as e:
        handle_exception(e, "sf", fatal=True)
    except Exception as e:
        handle_exception(e, "sf", fatal=True)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SpiderFoot: Open Source Intelligence Automation."
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug output."
    )
    parser.add_argument("-l", help="Log directory.", metavar="DIR", type=str)
    parser.add_argument(
        "-m", "--modules", help="Comma-separated list of modules to enable.", type=str
    )
    parser.add_argument("-M", "--module-info",
                        help="Get module information.", type=str)
    parser.add_argument("-s", "--start", help="Target for the scan.", type=str)
    parser.add_argument(
        "-t", "--types", help="Types of scan to run.", type=str)
    parser.add_argument("-u", "--usecase", help="Use case to run.", type=str)
    parser.add_argument("-T", "--template",
                        help="Scan template to use.", type=str)
    parser.add_argument("-n", "--name", help="Name of the scan.", type=str)
    parser.add_argument("-o", "--output", help="Output format.", type=str)
    parser.add_argument(
        "-f", "--filter", help="Event types to filter out.", type=str)
    parser.add_argument(
        "-F",
        "--filtering",
        help="Build filter rules from previously run scans.",
        type=str,
    )
    parser.add_argument(
        "-x", "--noproxy", action="store_true", help="Disable proxy.", default=False
    )
    parser.add_argument(
        "-S", "--suppress", action="store_true", help="Silent output.", default=False
    )
    parser.add_argument(
        "-D", "--delete", action="store_true", help="Delete the scan.", default=False
    )
    parser.add_argument("-r", "--remote", help="Remote scan ID.", type=str)
    parser.add_argument(
        "-H",
        "--headers",
        action="store_true",
        help="Include headers in output.",
        default=False,
    )
    parser.add_argument("-v", "--version",
                        action="store_true", help="Display Version")
    parser.add_argument(
        "-nowebserver", action="store_true", help="Do not start the web server"
    )

    return parser.parse_args()


def load_modules(config: dict) -> bool:
    """Load SpiderFoot modules.

    Args:
        config: SpiderFoot configuration options

    Returns:
        bool: Success or failure
    """
    try:
        # Import here to avoid circular imports
        from spiderfoot import SpiderFootHelpers

        modDir = os.path.dirname(os.path.abspath(__file__)) + "/modules/"

        if not os.path.isdir(modDir):
            log.error(f"Modules directory does not exist: {modDir}")
            return False

        modules = SpiderFootHelpers.loadModulesAsDict(modDir)
        if not modules:
            log.error("No modules found in modules directory.")
            return False

        log.info(f"Found {len(modules)} modules")
        config["__modules__"] = modules

        # Load correlation rules
        corr_dir = os.path.dirname(
            os.path.abspath(__file__)) + "/correlations/"
        if os.path.isdir(corr_dir):
            rules = SpiderFootHelpers.loadCorrelationRulesRaw(corr_dir)
            config["__correlationrules__"] = rules
            log.info(f"Loaded {len(rules)} correlation rules")

        return True

    except Exception as e:
        log.error(f"Failed to load modules: {e}")
        return False


def start_scan(config: dict, args, loggingQueue: mp.Queue) -> None:
    """Start a scan based on the provided configuration and command-line arguments.

    Args:
        config: SpiderFoot config options
        args: command line args
        loggingQueue: main SpiderFoot logging queue
    """
    try:
        # Validate arguments
        if not validate_scan_arguments(args):
            return

        target = process_target(args.start)
        if not target:
            log.error("Invalid target specified.")
            return

        # Initialize database
        dbh = SpiderFootDb(config)

        # Create a new scan
        scanName = args.name if args.name else target
        scanId = SpiderFootHelpers.genScanInstanceId()
        targetType = SpiderFootHelpers.targetTypeFromString(target)

        log.info(
            f"Starting scan '{scanName}' (ID: {scanId}) for target '{target}'")

        # Set up modules
        modlist = prepare_modules(args, dbh, config, targetType)
        if not modlist:
            log.error("No modules selected for scan.")
            return

        # Prepare output configuration
        prepare_scan_output(args)

        # Execute the scan
        startSpiderFootScanner(
            loggingQueue, scanName, scanId, target, targetType, modlist, config
        )

    except Exception as e:
        handle_exception(e, "start_scan")


def validate_scan_arguments(args) -> bool:
    """Validate scan arguments.

    Args:
        args: Command line arguments

    Returns:
        bool: True if arguments are valid
    """
    if not args.start:
        log.error("No target specified.")
        return False

    if args.x and not args.t:
        log.error("You cannot use -x without -t. Use -h for help.")
        return False

    if args.x and args.m:
        log.error("You cannot use -x with -m. Use -h for help.")
        return False

    if args.r and (args.o and args.o not in ["tab", "csv"]):
        log.error(
            "Remote fetching is only compatible with tab and csv output formats.")
        return False

    if args.H and (args.o and args.o not in ["tab", "csv"]):
        log.error("Headers are only compatible with tab and csv output formats.")
        return False

    if args.D and args.o != "csv":
        log.error("-D can only be used when the output format is CSV (-o csv).")
        return False

    return True


def process_target(target: str) -> str:
    """Process and validate the scan target.

    Args:
        target: Target string

    Returns:
        str: Processed target
    """
    # Usernames and names - quoted on the commandline - won't have quotes,
    # so add them.
    if " " in target:
        target = f'"{target}"'

    if "." not in target and not target.startswith("+") and '"' not in target:
        target = f'"{target}"'

    targetType = SpiderFootHelpers.targetTypeFromString(target)
    if not targetType:
        log.error(
            f"Invalid target '{target}'. Could not determine target type.")
        return ""

    target = target.strip('"')
    return target


def prepare_modules(args, dbh, config: dict, targetType: str) -> List[str]:
    """Prepare module list for scanning.

    Args:
        args: Command line arguments
        dbh: Database handle
        config: SpiderFoot config
        targetType: Target type

    Returns:
        list: List of modules to use
    """
    modlist: List[str] = []

    # If no modules or types specified, use all
    if not args.t and not args.m and not args.u:
        log.info("No modules or types specified, using all modules.")
        for module in sorted(config["__modules__"]):
            if module.startswith("sfp__"):
                modlist.append(module)

        return modlist

    # Register signal handler for CTRL-C
    signal.signal(signal.SIGINT, handle_abort)

    # If the user is scanning by type..
    if args.t:
        types = args.t.split(",")
        for module in sorted(config["__modules__"]):
            if module.startswith("sfp_"):
                for mtype in config["__modules__"][module]["provides"]:
                    if mtype.lower() in [t.lower() for t in types]:
                        modlist.append(module)
                        break

    # If the user is scanning by module..
    if args.m:
        modules = args.m.split(",")
        for module in sorted(config["__modules__"]):
            if module.startswith("sfp_") and module in modules:
                modlist.append(module)

    # If the user is scanning by use case
    if args.u:
        usecase = args.u.lower()
        for module in sorted(config["__modules__"]):
            if not module.startswith("sfp_"):
                continue

            if usecase == "all":
                modlist.append(module)
                continue

            if (
                usecase == "passive" and
                "passive" in config["__modules__"][module]["flags"]
            ):
                modlist.append(module)
                continue

            if (
                usecase == "investigate" and
                "investigate" in config["__modules__"][module]["flags"]
            ):
                modlist.append(module)
                continue

            if (
                usecase == "footprint" and
                "footprint" in config["__modules__"][module]["flags"]
            ):
                modlist.append(module)
                continue

    # Add sfp__stor_stdout to the module list
    typedata = dbh.eventTypes()
    types = dict()
    for r in typedata:
        types[r[1]] = r[0]

    sfp__stor_stdout_opts = config["__modules__"]["sfp__stor_stdout"]["opts"]
    sfp__stor_stdout_opts["_eventtypes"] = types

    # Configure stdout module based on arguments
    if args.f:
        sfp__stor_stdout_opts["_modulefilter"] = args.f

    if args.F:
        sfp__stor_stdout_opts["_modulefilters"] = args.F

    if args.o:
        sfp__stor_stdout_opts["_format"] = args.o

    if args.t:
        sfp__stor_stdout_opts["_typefilter"] = args.t

    if args.n:
        sfp__stor_stdout_opts["_requested"] = args.n

    if args.r:
        sfp__stor_stdout_opts["_requested"] = args.r

    if args.S:
        sfp__stor_stdout_opts["_showsource"] = args.S

    if args.D:
        sfp__stor_stdout_opts["_deleteafter"] = args.D

    if args.x:
        sfp__stor_stdout_opts["_stripnumpy"] = True

    modlist.append("sfp__stor_stdout")

    return list(set(modlist))  # Ensure list contains no duplicates


def prepare_scan_output(args):
    """Prepare scan output based on arguments.

    Args:
        args: Command line arguments
    """
    if args.o == "json":
        print("[", end="")
    elif not args.H:
        # Print header if CSV or TSV output and headers are enabled
        if args.o == "tab":
            print("Source\tType\tData\tModule")
        elif args.o == "csv":
            print("Source,Type,Data,Module")


def execute_scan(
    loggingQueue: mp.Queue,
    target: str,
    targetType: str,
    modlist: List[str],
    config: Dict[str, Any],
):
    """Execute a scan with the provided parameters.

    Args:
        loggingQueue: Logging queue
        target: Target to scan
        targetType: Type of target
        modlist: List of modules to use
        config: SpiderFoot configuration
    """
    scanName = target
    scanId = SpiderFootHelpers.genScanInstanceId()

    try:
        # Start the scan
        startSpiderFootScanner(
            loggingQueue, scanName, scanId, target, targetType, modlist, config
        )
    except Exception as e:
        handle_exception(e, "execute_scan")


def start_web_server(config: dict, loggingQueue=None) -> None:
    """Start SpiderFoot web server.

    Args:
        config: SpiderFoot configuration
        loggingQueue: Logging queue for multiprocessing
    """
    log.info("Starting web server")

    web_host = "127.0.0.1"
    web_port = 5001
    web_root = "/"

    # Override defaults from config
    if config.get("__webserver_host"):
        web_host = config["__webserver_host"]
    if config.get("__webserver_port"):
        web_port = config["__webserver_port"]
    if config.get("__webserver_root"):
        web_root = config["__webserver_root"]

    # Initialize the web server
    cherrypy.config.update(
        {"server.socket_host": web_host, "server.socket_port": int(web_port)}
    )

    log.info(f"Starting web server at http://{web_host}:{web_port}{web_root}")

    # Initialize the web interface
    webapp = SpiderFootWebUi(config)

    # Configure the web server
    cherrypy_conf = {
        "global": {"server.socket_host": web_host, "server.socket_port": int(web_port)},
        "/": {
            "tools.sessions.on": True,
            "tools.sessions.timeout": 60 * 60 * 24,
            "tools.staticdir.root": os.path.dirname(os.path.abspath(__file__)),
            "tools.staticdir.dir": "static",
        },
        "/static": {"tools.staticdir.on": True, "tools.staticdir.dir": "static"},
    }

    # Start the web server
    cherrypy.quickstart(webapp, script_name=web_root, config=cherrypy_conf)


def handle_abort(signal, frame) -> None:
    """Handle abortion of a running scan (CTRL+C).

    Args:
        signal: Signal received
        frame: Current stack frame
    """
    log.info("Aborting...")
    sys.exit(0)


if __name__ == "__main__":
    main()
