#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         sf
# Purpose:      Main SpiderFoot driver
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     03/04/2012
# Copyright:   (c) Steve Micallef 2012
# License:     MIT
# -----------------------------------------------------------------

import os
import sys
import argparse
from collections import OrderedDict
import cherrypy
import logging

# To support both command-line access and web interface
from sflib import SpiderFoot
from sfscan import startSpiderFootScanner
from sfwebui import SpiderFootWebUi
from spiderfoot import SpiderFootDb, SpiderFootHelpers
from spiderfoot import __version__
from spiderfoot.logger import logListenerSetup, logWorkerSetup

# Now imports for the FastAPI interface
import importlib.util
import multiprocessing as mp

# Check if FastAPI and dependencies are available
fastapi_available = True
try:
    import fastapi
    import uvicorn
    from fastapi.staticfiles import StaticFiles
except ImportError:
    fastapi_available = False


def main():
    # Parse command line options
    parser = argparse.ArgumentParser(
        description=f'SpiderFoot {__version__}: Open Source Intelligence Automation.')
    parser.add_argument(
        '-d', '--debug', help='Enable debug output.', action='store_true')
    parser.add_argument('-l', metavar='IP:port',
                        help='IP and port to listen on.')
    parser.add_argument('-m', metavar='mod1,mod2,...',
                        type=str, help='Modules to enable.')
    parser.add_argument('-M', '--modules',
                        help='List available modules.', action='store_true')
    parser.add_argument('-s', metavar='TARGET', help='Target for the scan.')
    parser.add_argument('-t', metavar='type1,type2,...',
                        type=str, help='Event types to collect.')
    parser.add_argument(
        '-T', '--types', help='List available event types.', action='store_true')
    parser.add_argument('-o', metavar='tab|csv|json',
                        type=str, help='Output format.')
    parser.add_argument('-n', metavar='Name', help='Name for the scan.')
    parser.add_argument('-r', help='Data directory', type=str)
    parser.add_argument(
        '-c', '--correlate', help='Run correlation rules against scan results.', action='store_true')
    parser.add_argument('-f', help='Disable DNS cache.', action='store_true')
    parser.add_argument(
        '-F', '--fastapi', help='Use FastAPI web interface instead of CherryPy.', action='store_true')
    options = parser.parse_args()

    # Load the default configuration from the config file
    sf = SpiderFoot(opts)
    sfConfig = sf.defaultConfig()
    sfConfig['_debug'] = options.debug

    if options.r:
        if not os.path.isdir(options.r):
            print(f"Could not find data directory: {options.r}")
            sys.exit(-1)
        sfConfig['__database'] = os.path.join(options.r, "spiderfoot.db")

    # Are we looping through a set of modules and just listing them?
    if options.modules:
        log_level = logging.DEBUG if options.debug else logging.INFO
        mp.set_start_method("spawn", force=True)
        loggingQueue = mp.Queue()
        logListenerSetup(loggingQueue, sfConfig)
        logWorkerSetup(loggingQueue)

        sf = SpiderFoot(sfConfig)
        modlist = sf.modulesProducing("")
        modules = dict()
        for mod in modlist:
            module_info = sf.loadModuleInfo(mod)
            modules[mod] = module_info

        print("")
        print("Modules available:")
        for mod in sorted(modules.keys()):
            if mod.startswith("sfp__"):
                print(f"  {mod} - {modules[mod]['descr']}")
        print("")
        sys.exit(0)

    # Are we looping through a set of output types and just listing them?
    if options.types:
        dbh = SpiderFootDb(sfConfig)
        types = dbh.eventTypes()
        print("")
        print("Types available:")
        for r in types:
            print(f"  {r[1]} - {r[0]}")
        print("")
        sys.exit(0)

    # Convert a target to a normalized form
    target_type = None
    if options.s:
        target_type = SpiderFootHelpers.targetTypeFromString(options.s)
        if target_type is None:
            print("Unable to determine target type. Please specify a valid target.")
            sys.exit(-1)

    # If using the web interface, start the web server
    if options.l and not options.s:
        if ":" not in options.l:
            print("Invalid ip:port format.")
            sys.exit(-1)

        try:
            (host, port) = options.l.split(":")
            port = int(port)
        except Exception as e:
            print(f"Invalid ip:port format: {e}")
            sys.exit(-1)

        # Start the web server
        web_config = {
            'host': host,
            'port': port,
            'root': '/'
        }

        # Use FastAPI if available and requested
        if options.fastapi or fastapi_available:
            try:
                from sfwebui_fastapi_main import main as fastapi_main
                # Override sys.argv to pass the web server configuration
                orig_argv = sys.argv
                sys.argv = [sys.argv[0],
                            '--listen', host,
                            '--port', str(port)]
                if options.debug:
                    sys.argv.append('--debug')
                if options.r:
                    sys.argv.extend(
                        ['--config', os.path.join(options.r, "spiderfoot.conf")])

                print(f"Starting FastAPI web server at http://{host}:{port}/")
                fastapi_main()
                sys.argv = orig_argv  # Restore original argv
                return
            except Exception as e:
                print(f"Failed to start FastAPI web server: {e}")
                if not options.fastapi:
                    print("Falling back to CherryPy web server")
                else:
                    sys.exit(-1)

        # Fall back to CherryPy
        sfWebUiConfig = {
            'host': host,
            'port': port,
            'root': '/',
            'cors': ['http://127.0.0.1:3000', 'http://localhost:3000']
        }

        cherrypy.config.update({
            'server.socket_host': host,
            'server.socket_port': port,
            'log.screen': options.debug,
            'request.show_tracebacks': options.debug
        })

        mp.set_start_method("spawn", force=True)
        loggingQueue = mp.Queue()
        logListenerSetup(loggingQueue, sfConfig)

        if not options.debug:
            cherrypy.log.screen = False

        print(f"Starting web server at http://{host}:{port}/")

        # Initialize the web server
        webapp = SpiderFootWebUi(sfWebUiConfig, sfConfig, loggingQueue)

        # Configure and start the web server
        cherrypy.quickstart(webapp, script_name=web_config['root'])
        return

    # We're not starting the web server, so run the command-line scanner
    if not options.s:
        print("You need to specify a target with -s.")
        sys.exit(-1)

    if not options.m and not options.t:
        print("You need to specify scan modules with -m or event types with -t.")
        sys.exit(-1)

    if not options.n:
        print("No name specified, will use the current timestamp.")
        options.n = SpiderFootHelpers.genScanInstanceId()

    # Define the scan ID
    scan_id = SpiderFootHelpers.genScanInstanceId()

    # Initialize logging
    mp.set_start_method("spawn", force=True)
    loggingQueue = mp.Queue()
    logListenerSetup(loggingQueue, sfConfig)
    logWorkerSetup(loggingQueue)

    # Start a scan
    options.m = options.m.split(",") if options.m else []
    options.t = options.t.split(",") if options.t else []

    mods = options.m
    if len(options.t) > 0:
        # If scan modules specified, they take precedence
        sf = SpiderFoot(sfConfig)
        mods = sf.modulesProducing(options.t)

    # Add mandatory modules, they take precedence
    if "sfp__stor_db" not in mods:
        mods.append("sfp__stor_db")

    if options.f:
        sfConfig['_dnsresolver'] = False

    # Start the scan
    p = mp.Process(
        target=startSpiderFootScanner,
        args=(loggingQueue, options.n, scan_id,
              options.s, target_type, mods, sfConfig)
    )
    p.daemon = True
    p.start()
    p.join()

    # Wait for the scan to complete
    print(f"Scan {scan_id} completed. Use the -l option to review results.")

    # Correlate the results if requested
    if options.correlate:
        print("Running correlation...")
        dbh = SpiderFootDb(sfConfig)
        dbh.scanInstanceCorrelations(scan_id)

    # Output scan results if output format specified
    if options.o:
        dbh = SpiderFootDb(sfConfig)
        data = dbh.scanResultEvent(scan_id)
        if options.o == "csv":
            import csv
            with open(f"{options.n}.csv", "w", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Type", "Module", "Source", "Data"])
                for row in data:
                    writer.writerow([row[4], row[3], row[2], row[1]])
            print(f"CSV output written to {options.n}.csv")
        elif options.o == "json":
            import json
            scan_data = []
            for row in data:
                scan_data.append({
                    "type": row[4],
                    "module": row[3],
                    "source": row[2],
                    "data": row[1]
                })
            with open(f"{options.n}.json", "w") as f:
                json.dump(scan_data, f, indent=4)
            print(f"JSON output written to {options.n}.json")
        elif options.o == "tab":
            with open(f"{options.n}.tsv", "w") as f:
                for row in data:
                    f.write(f"{row[4]}\t{row[3]}\t{row[2]}\t{row[1]}\n")
            print(f"Tab-separated output written to {options.n}.tsv")
        else:
            print(f"Unknown output format: {options.o}")


if __name__ == "__main__":
    main()
