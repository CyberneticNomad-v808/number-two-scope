#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         sf
# Purpose:      Main wrapper for calling all SpiderFoot modules (Modular Version)
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     03/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     MIT
# -------------------------------------------------------------------------------

"""
SpiderFoot Main Entry Point - Modular Version

This is the backward-compatible entry point that now uses the new modular
architecture. It delegates all functionality to the SpiderFootOrchestrator
while maintaining the original interface.
"""


import sys
import os
from spiderfoot.sflib import SpiderFoot
from spiderfoot.scan_service.scanner import startSpiderFootScanner
from sfwebui import SpiderFootWebUi
from spiderfoot import SpiderFootHelpers
from spiderfoot import SpiderFootDb
from spiderfoot.logger import logListenerSetup, logWorkerSetup

# Import legacy components for backward compatibility
from spiderfoot import __version__

# Ensure the SpiderFoot directory is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the modular orchestrator
from sf_orchestrator import SpiderFootOrchestrator

# Legacy compatibility imports for unit tests
try:
    from spiderfoot.core.modules import ModuleManager
    from spiderfoot.core.server import ServerManager
    from spiderfoot.core.validation import ValidationUtils
    from spiderfoot.core.scan import ScanManager
    from spiderfoot import SpiderFootHelpers
    import logging as sf_logging
    
    # Legacy attributes are already imported and available
    logging = sf_logging
    
except ImportError:
    # If new modules don't exist, create dummy classes for tests
    class DummyModuleManager:
        pass
    
    class DummyServerManager:
        pass
    
    class DummyValidationUtils:
        pass
    
    class DummyScanManager:
        pass
    
    ModuleManager = DummyModuleManager
    ServerManager = DummyServerManager
    ValidationUtils = DummyValidationUtils
    ScanManager = DummyScanManager
    SpiderFootHelpers = None
    logging = None

# Global variables for backward compatibility
scanId = None
dbh = None

# Read database configuration from environment variables
# PostgreSQL is required - SQLite is no longer supported
# Allow module import without env vars for testing, but validate when actually running
try:
    from spiderfoot.db.db_config_builder import build_database_config
    _db_config = build_database_config()
    _database_config = _db_config['__database']
    _db_type = _db_config['__dbtype']
except ValueError as e:
    # If running as main module, provide clear error and exit
    # If being imported (e.g., by tests), use empty config
    if __name__ == '__main__':
        print(f"ERROR: Database configuration failed: {e}", file=sys.stderr)
        print("\nSpiderFoot requires PostgreSQL. SQLite is no longer supported.", file=sys.stderr)
        print("\nRequired environment variables:", file=sys.stderr)
        print("  SPIDERFOOT_DB_NAME or SPIDERFOOT_DB=your_database (REQUIRED)", file=sys.stderr)
        print("\nOptional environment variables (with defaults):", file=sys.stderr)
        print("  SPIDERFOOT_DB_TYPE=postgresql (default)", file=sys.stderr)
        print("  SPIDERFOOT_DB_HOST=localhost (default)", file=sys.stderr)
        print("  SPIDERFOOT_DB_PORT=5432 (default)", file=sys.stderr)
        print("  SPIDERFOOT_DB_USER=spiderfoot (default)", file=sys.stderr)
        print("  SPIDERFOOT_DB_PASSWORD=your_password (recommended)", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  export SPIDERFOOT_DB_NAME=spiderfoot_db", file=sys.stderr)
        print("  export SPIDERFOOT_DB_PASSWORD=your_secure_password", file=sys.stderr)
        print("\nFor more information, see docs/POSTGRESQL_SETUP.md", file=sys.stderr)
        sys.exit(1)
    else:
        # Allow import for testing with empty config
        _database_config = ''
        _db_type = 'postgresql'
except ImportError as e:
    # Fallback for development/testing when module structure is not yet set up
    print(f"ERROR: Failed to import db_config_builder: {e}", file=sys.stderr)
    print("Using fallback configuration.", file=sys.stderr)
    _database_config = ''
    _db_type = 'postgresql'

# Legacy configuration for backward compatibility
sfConfig = {
    '_debug': False,
    '_maxthreads': 3,
    '__logging': True,
    '__outputfilter': None,
    '_useragent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
    '_dnsserver': '',
    '_fetchtimeout': 5,
    '_internettlds': 'https://publicsuffix.org/list/effective_tld_names.dat',
    '_internettlds_cache': 72,
    '_genericusers': '',
    '__database': _database_config,
    '__dbtype': _db_type,
    '__modules__': None,
    '__correlationrules__': None,
    '_socks1type': '',
    '_socks2addr': '',
    '_socks3port': '',
    '_socks4user': '',
    '_socks5pwd': '',
    '_csrf_enabled': False,
    '_csrf_development_mode': True,
    '_csrf_secret_key': None,
    '_rate_limiting_enabled': False,
    '_input_validation_enabled': True,
    '_session_security_enabled': True,
    '_api_security_enabled': False,
    '_security_headers_enabled': True,
    '_security_logging_enabled': True,
    '_security_log_file': 'logs/security.log',
    '_bypass_auth_endpoints': '/static,/favicon.ico,/robots.txt,/api/docs,/api/redoc',
}

sfOptdescs = {
    '_debug': "Enable debugging?",
    '_maxthreads': "Max number of modules to run concurrently",
    '_useragent': "User-Agent string to use for HTTP requests. Prefix with an '@' to randomly select the User Agent from a file containing user agent strings for each request, e.g. @C:\\useragents.txt or @/home/bob/useragents.txt. Or supply a URL to load the list from there.",
    '_dnsserver': "Override the default resolver with another DNS server. For example, 8.8.8.8 is Google's open DNS server.",
    '_fetchtimeout': "Number of seconds before giving up on a HTTP request.",
    '_internettlds': "List of Internet TLDs.",
    '_internettlds_cache': "Hours to cache the Internet TLD list. This can safely be quite a long time given that the list doesn't change too often.",
    '_genericusers': "List of usernames that if found as usernames or as part of e-mail addresses, should be treated differently to non-generics.",
    '_socks1type': "SOCKS Server Type. Can be '4', '5', 'HTTP' or 'TOR'",
    '_socks2addr': 'SOCKS Server IP Address.',
    '_socks3port': 'SOCKS Server TCP Port. Usually 1080 for 4/5, 8080 for HTTP and 9050 for TOR.',
    '_socks4user': 'SOCKS Username. Valid only for SOCKS4 and SOCKS5 servers.',
    '_socks5pwd': "SOCKS Password. Valid only for SOCKS5 servers.",
    '_csrf_enabled': "Enable CSRF (Cross-Site Request Forgery) protection for the web interface. When enabled, POST/PUT/DELETE requests must include a valid CSRF token.",
    '_csrf_development_mode': "CSRF development mode. When enabled, CSRF validation failures are logged as warnings but don't block requests. Useful for single-user development or protected LAN deployments. When disabled, CSRF failures will return 403 Forbidden errors.",
    '_csrf_secret_key': "Secret key for CSRF token generation. Leave empty (None) to auto-generate a secure random key on startup. For production with multiple instances, set the same key across all instances.",
    '_rate_limiting_enabled': "Enable rate limiting to prevent abuse. Recommended for public-facing deployments. When disabled, no rate limits are enforced.",
    '_input_validation_enabled': "Enable input validation to prevent injection attacks. Should remain enabled unless you have specific compatibility issues.",
    '_session_security_enabled': "Enable session security features (timeouts, validation, secure cookies). Recommended for production deployments.",
    '_api_security_enabled': "Enable API authentication (JWT/API keys). Required for production API access. When disabled, API endpoints are accessible without authentication.",
    '_security_headers_enabled': "Enable security headers (X-Frame-Options, Content-Security-Policy, etc.). Recommended for production to prevent common web attacks.",
    '_security_logging_enabled': "Enable detailed security event logging. Logs authentication attempts, blocked requests, and security violations.",
    '_security_log_file': "Path to security audit log file. Can be absolute or relative to SpiderFoot root directory.",
    '_bypass_auth_endpoints': "Comma-separated list of URL paths that bypass authentication checks. Typically static assets and public API documentation.",
    '_modulesenabled': "Modules enabled for the scan."
}


def main():
    """
    Main entry point - delegates to the modular orchestrator.
    
    This function maintains backward compatibility while using the new
    modular architecture under the hood.
    """
    try:
        # Create and run the orchestrator
        orchestrator = SpiderFootOrchestrator()
        orchestrator.run()
        
    except Exception as e:
        import logging
        log = logging.getLogger("spiderfoot.sf")
        log.critical(f"Critical error in main: {e}", exc_info=True)
        sys.exit(-1)


# Legacy function stubs for backward compatibility
def load_modules_custom(mod_dir, log):
    """
    Legacy function - now handled by ModuleManager.
    
    This function is kept for backward compatibility but delegates
    to the new modular architecture.
    
    Args:
        mod_dir: Directory containing SpiderFoot modules
        log: Logger instance
        
    Returns:
        Dict of loaded modules
    """
    from spiderfoot.core.modules import ModuleManager
    
    manager = ModuleManager()
    return manager._load_modules_custom(mod_dir)


def start_scan(sfConfig, sfModules, args, loggingQueue):
    """
    Legacy function - now handled by ScanManager.
    
    This function is kept for backward compatibility but delegates
    to the new modular architecture.
    
    Args:
        sfConfig: SpiderFoot configuration dictionary
        sfModules: Dictionary of loaded modules
        args: Command line arguments
        loggingQueue: Queue for logging messages
    """
    from spiderfoot.core.scan import ScanManager
    from spiderfoot.core.validation import ValidationUtils
    
    validation = ValidationUtils()
    scan_manager = ScanManager(sfConfig)
    
    try:
        # Validate and prepare scan parameters
        scan_params = scan_manager.validate_scan_arguments(
            target=args.s,
            modules=validation.validate_module_list(args.m) if args.m else None,
            event_types=validation.validate_event_types(args.t) if args.t else None,
            usecase=args.u,
            strict_mode=args.x
        )
        
        # Prepare modules
        module_list = scan_manager.prepare_modules(scan_params, sfModules)
        
        # Prepare scan configuration
        scan_config = scan_manager.prepare_scan_config(scan_params)
        
        # Execute scan
        scan_id = scan_manager.execute_scan(
            scan_name=scan_params['target'],
            target=scan_params['target'],
            target_type=scan_params['target_type'],
            modules=module_list,
            config=scan_config,
            logging_queue=loggingQueue
        )
        
        # Monitor scan
        result = scan_manager.monitor_scan(scan_id)
        
        if result['status'] == 'FINISHED':
            sys.exit(0)
        else:
            sys.exit(-1)
            
    except Exception as e:
        import logging
        log = logging.getLogger("spiderfoot.sf")
        log.error(f"Scan execution failed: {e}")
        sys.exit(-1)


def start_fastapi_server(sfApiConfig, sfConfig, loggingQueue=None):
    """
    Legacy function - now handled by ServerManager.
    
    This function is kept for backward compatibility but delegates
    to the new modular architecture.
    
    Args:
        sfApiConfig: FastAPI server configuration
        sfConfig: SpiderFoot configuration dictionary
        loggingQueue: Optional queue for logging messages
    """
    from spiderfoot.core.server import ServerManager
    
    server_manager = ServerManager(sfConfig)
    server_manager.start_fastapi_server(sfApiConfig, loggingQueue)


def start_both_servers(sfWebUiConfig, sfApiConfig, sfConfig, loggingQueue=None):
    """
    Legacy function - now handled by ServerManager.
    
    This function is kept for backward compatibility but delegates
    to the new modular architecture.
    
    Args:
        sfWebUiConfig: Web UI server configuration
        sfApiConfig: FastAPI server configuration
        sfConfig: SpiderFoot configuration dictionary
        loggingQueue: Optional queue for logging messages
    """
    from spiderfoot.core.server import ServerManager
    
    server_manager = ServerManager(sfConfig)
    server_manager.start_both_servers(sfWebUiConfig, sfApiConfig, loggingQueue)


def start_web_server(sfWebUiConfig, sfConfig, loggingQueue=None):
    """
    Legacy function - now handled by ServerManager.
    
    This function is kept for backward compatibility but delegates
    to the new modular architecture.
    
    Args:
        sfWebUiConfig: Web UI server configuration
        sfConfig: SpiderFoot configuration dictionary
        loggingQueue: Optional queue for logging messages
    """
    from spiderfoot.core.server import ServerManager
    
    server_manager = ServerManager(sfConfig)
    server_manager.start_web_server(sfWebUiConfig, loggingQueue)


def handle_abort(signal, frame):
    """
    Legacy function - now handled by ScanManager.
    
    This function is kept for backward compatibility.
    
    Args:
        signal: Signal number
        frame: Current stack frame
    """
    import logging
    log = logging.getLogger("spiderfoot.sf")
    
    global dbh, scanId
    
    if scanId and dbh:
        log.info(f"Received interrupt signal, stopping scan {scanId}")
        try:
            from spiderfoot.core.scan import ScanManager
            scan_manager = ScanManager(sfConfig)
            scan_manager.stop_scan(scanId)
        except Exception as e:
            log.error(f"Error stopping scan: {e}")
    
    sys.exit(-1)


# Legacy helper functions for validation
def validate_arguments(args, log):
    """
    Legacy validation function - now handled by ValidationUtils.
    
    Args:
        args: Command line arguments
        log: Logger instance
    """
    from spiderfoot.core.validation import ValidationUtils
    
    ValidationUtils()  # Initialize for any side effects
    
    if not args.s:
        log.error("You must specify a target when running in scan mode. Try --help for guidance.")
        sys.exit(-1)
    
    if args.x and not args.t:
        log.error("-x can only be used with -t. Use --help for guidance.")
        sys.exit(-1)
    
    if args.x and args.m:
        log.error("-x can only be used with -t and not with -m. Use --help for guidance.")
        sys.exit(-1)


def process_target(args, log):
    """
    Legacy target processing function - now handled by ScanManager.
    
    Args:
        args: Command line arguments
        log: Logger instance
        
    Returns:
        Tuple of (target, target_type)
    """
    from spiderfoot import SpiderFootHelpers
    
    target = args.s
    if " " in target:
        target = f'"{target}"'
    if "." not in target and not target.startswith("+") and '"' not in target:
        target = f'"{target}"'
    
    targetType = SpiderFootHelpers.targetTypeFromString(target)
    
    if not targetType:
        log.error(f"Could not determine target type. Invalid target: {target}")
        sys.exit(-1)
    
    target = target.strip('"')
    return target, targetType


# Maintain backward compatibility
if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage_text = "SpiderFoot usage:\n  Web UI:       python sf.py -l <ip>:<port>\n  FastAPI:      python sf.py --api [--api-listen <ip>:<port>]\n  Both servers: python sf.py --both [-l <ip>:<port>] [--api-listen <ip>:<port>]\n  CLI scan:     python sf.py -s <target> [options]\nTry --help for full guidance."
        print(usage_text)
        print(usage_text, file=sys.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(-1)

    main()
