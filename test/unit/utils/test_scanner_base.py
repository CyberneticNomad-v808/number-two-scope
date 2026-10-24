#!/usr/bin/env python3
"""Enhanced Test Base for SpiderFoot Scanner Tests.

Provides automatic resource management, thread cleanup, and leak detection
for all SpiderFoot scanner tests.
"""

import os
import unittest
import threading
import time
from contextlib import suppress
from typing import Any


def _build_test_dsn() -> str:
    """Build a PostgreSQL DSN from environment variables.

    Mirrors the logic in test/conftest.py default_options fixture so that
    every test base class provides a DSN that passes DbCore.__init__
    validation.
    The actual connection is intercepted by the mock_db_connection fixture
    in test/unit/conftest.py -- this string only needs to be syntactically
    valid.

    Returns:
        str: A PostgreSQL DSN string.
    """
    user = os.environ.get('SPIDERFOOT_DB_USER', 'spiderfoot_test')
    password = os.environ.get('SPIDERFOOT_DB_PASSWORD', 'test_password')
    host = os.environ.get('SPIDERFOOT_DB_HOST', 'localhost')
    port = os.environ.get('SPIDERFOOT_DB_PORT', '5432')
    name = os.environ.get('SPIDERFOOT_DB_NAME', 'spiderfoot_test')
    return 'postgresql://' + user + ':' + password + '@' + host + ':' + port + '/' + name


try:
    # Relative imports (when called from package)
    from .resource_manager import get_test_resource_manager
    from .thread_registry import get_test_thread_registry, cleanup_test_threads
    from .shared_pool_cleanup import cleanup_shared_pools
except ImportError:
    # Absolute imports (when called directly)
    from test.unit.utils.resource_manager import get_test_resource_manager
    from test.unit.utils.thread_registry import get_test_thread_registry, cleanup_test_threads
    from test.unit.utils.shared_pool_cleanup import cleanup_shared_pools


class TestScannerBase(unittest.TestCase):
    """Enhanced base class for SpiderFoot scanner tests.

    Features:
    - Automatic scanner registration and cleanup
    - Thread leak detection and prevention
    - Database connection management
    - Scan status tracking and cleanup
    """

    def setUp(self: 'TestScannerBase') -> None:
        """Set up test with scanner-specific resource tracking."""
        super().setUp()

        # Get resource managers
        self.resource_manager = get_test_resource_manager()
        self.thread_registry = get_test_thread_registry()

        # Track initial thread count
        self.initial_thread_count = threading.active_count()

        # Scanner-specific tracking
        self._test_scanners = []
        self._test_databases = []
        self._scan_instances = []

        # Record test start time
        self.test_start_time = time.time()

        # Set up test-specific temporary directory
        import tempfile
        self._temp_dir = tempfile.mkdtemp(prefix='spiderfoot_test_')

        # Set up default options (inherited from SpiderFootTestBase)
        from spiderfoot import SpiderFootHelpers
        self.default_options = {
            '_debug': False,
            '__logging': True,
            '__outputfilter': None,
            '_useragent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
            '_dnsserver': '',
            '_fetchtimeout': 5,
            '_internettlds': 'https://publicsuffix.org/list/effective_tld_names.dat',
            '_internettlds_cache': 72,
            '_genericusers': ','.join(SpiderFootHelpers.usernamesFromWordlists(['generic-usernames'])),
            '__database': _build_test_dsn(),
            '__dbtype': 'postgresql',
            '__modules__': {
                'sfp_example': {
                    'descr': 'Example module for testing',
                    'provides': ['EXAMPLE_EVENT'],
                    'consumes': ['ROOT'],
                    'group': 'passive',
                    'optdescs': {
                        'example_option': 'Example option description'
                    },
                    'opts': {
                        'example_option': 'default_value'
                    },
                    'meta': {
                        'targetType': 'INTERNET_NAME',
                        'name': 'sfp_example',
                        'title': 'Example',
                        'summary': 'Example module for testing',
                        'flags': [],
                        'categories': ['test'],
                        'labels': ['test']
                    }
                }
            },
            '__correlationrules__': None,
            '__globaloptdescs__': {
                'global_option1': 'Description for global option 1',
                'global_option2': 'Description for global option 2'
            },
            '_socks1type': '',
            '_socks2addr': '',
            '_socks3port': '',
            '_socks4user': '',
            '_socks5pwd': '',
            '__logstdout': False
        }

        print(
            'Setting up scanner test class: '
            + self.__class__.__name__
        )

    def register_thread(
        self: 'TestScannerBase',
        thread: Any,
        stop_func: Any = None,
        timeout: float = 5.0,
    ) -> int:
        """Register a thread for automatic cleanup via the resource manager.

        Args:
            thread: Thread to track.
            stop_func: Optional function to stop thread gracefully.
            timeout: Timeout for thread join.

        Returns:
            int: Resource ID for tracking.
        """
        return self.resource_manager.register_thread(
            thread, stop_func=stop_func, timeout=timeout
        )

    def register_scanner(
        self: 'TestScannerBase',
        scanner: Any,
        scan_id: str = None,
    ) -> int:
        """Register a SpiderFoot scanner for automatic cleanup.

        Args:
            scanner: Scanner instance to track.
            scan_id: Optional scan ID for tracking.

        Returns:
            int: Resource ID for tracking.
        """
        resource_id = self.resource_manager.register_scanner(scanner)
        self._test_scanners.append((scanner, resource_id, scan_id))
        return resource_id

    def register_scan_instance(
        self: 'TestScannerBase', scan_instance: Any
    ) -> int:
        """Register a scan instance for cleanup.

        Args:
            scan_instance: Scan instance to track.

        Returns:
            int: Resource ID for tracking.
        """
        def cleanup_scan() -> None:
            with suppress(Exception):
                # Set scan status to aborted
                if hasattr(scan_instance, 'setStatus'):
                    scan_instance.setStatus('ABORTED')

                # Clear scan queue
                if hasattr(scan_instance, 'scanQueue'):
                    scan_instance.scanQueue = []

                # Clear results
                if hasattr(scan_instance, 'results'):
                    scan_instance.results = {}

        resource_id = self.resource_manager.register_resource(
            scan_instance, cleanup_scan,
            category='scan',
            description='Scan: ' + scan_instance.__class__.__name__
        )

        self._scan_instances.append((scan_instance, resource_id))
        return resource_id

    def register_database(
        self: 'TestScannerBase', database: Any
    ) -> int:
        """Register a database connection for cleanup.

        Args:
            database: Database instance to track.

        Returns:
            int: Resource ID for tracking.
        """
        def cleanup_database() -> None:
            with suppress(Exception):
                # Close database connections
                if hasattr(database, 'close'):
                    database.close()
                elif hasattr(database, 'disconnect'):
                    database.disconnect()

                # Clear cached data
                if hasattr(database, 'cache'):
                    database.cache.clear()

        resource_id = self.resource_manager.register_resource(
            database, cleanup_database,
            category='database',
            description='Database: ' + database.__class__.__name__
        )

        self._test_databases.append((database, resource_id))
        return resource_id

    def create_test_scanner(
        self: 'TestScannerBase',
        scanner_class: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Create and register a test scanner.

        Args:
            scanner_class: Scanner class to instantiate.
            *args: Positional arguments for scanner.
            **kwargs: Keyword arguments for scanner.

        Returns:
            Any: Scanner instance with automatic cleanup.
        """
        # Create scanner instance
        scanner = scanner_class(*args, **kwargs)

        # Register for cleanup
        self.register_scanner(scanner)

        return scanner

    def force_abort_scanners(self: 'TestScannerBase') -> None:
        """Force abort all registered scanners."""
        print(
            'Force aborting '
            + str(len(self._test_scanners))
            + ' scanners...'
        )

        for scanner, _resource_id, scan_id in self._test_scanners:
            with suppress(Exception):
                # Force abort status
                if hasattr(scanner, '_SpiderFootScanner__setStatus'):
                    scanner._SpiderFootScanner__setStatus('ABORTED')

                # Set error state
                if hasattr(scanner, 'errorState'):
                    scanner.errorState = True

                # Stop scanning
                if hasattr(scanner, '_SpiderFootScanner__setStatus'):
                    scanner._SpiderFootScanner__setStatus('FINISHED')

                print(
                    '  Aborted scanner '
                    + scanner.__class__.__name__
                )
                if scan_id:
                    print('     Scan ID: ' + str(scan_id))

    def cleanup_scanner_threads(self: 'TestScannerBase') -> None:
        """Clean up all scanner-related threads."""
        print('Cleaning up scanner threads...')

        # Look for scanner-specific threads
        scanner_threads = []
        for thread in threading.enumerate():
            thread_name = thread.name.lower()
            if any(keyword in thread_name for keyword in [
                'scanner', 'spider', 'crawl', 'fetch', 'query'
            ]):
                scanner_threads.append(thread)

        if scanner_threads:
            print(
                '  Found '
                + str(len(scanner_threads))
                + ' scanner threads to cleanup'
            )

            for thread in scanner_threads:
                with suppress(Exception):
                    if thread.is_alive():
                        print(
                            '    Joining thread: ' + thread.name
                        )
                        thread.join(timeout=2.0)

                        if thread.is_alive():
                            print(
                                '    Thread ' + thread.name
                                + ' still alive after join'
                            )

    def cleanup_scan_data(self: 'TestScannerBase') -> None:
        """Clean up all scan-related data."""
        print('Cleaning up scan data...')

        # Clean up scan instances
        for scan_instance, _resource_id in self._scan_instances:
            with suppress(Exception):
                # Clear scan queue
                if hasattr(scan_instance, 'scanQueue'):
                    scan_instance.scanQueue = []

                # Clear results
                if hasattr(scan_instance, 'results'):
                    scan_instance.results = {}

                # Set to finished
                if hasattr(scan_instance, 'setStatus'):
                    scan_instance.setStatus('FINISHED')

        self._scan_instances.clear()

    def cleanup_database_connections(self: 'TestScannerBase') -> None:
        """Clean up all database connections."""
        print('Cleaning up database connections...')

        for database, _resource_id in self._test_databases:
            with suppress(Exception):
                # Close database connections
                if hasattr(database, 'close'):
                    database.close()
                elif hasattr(database, 'disconnect'):
                    database.disconnect()

                print(
                    '  Closed database: '
                    + database.__class__.__name__
                )

        self._test_databases.clear()

    def aggressive_scanner_cleanup(self: 'TestScannerBase') -> None:
        """Perform aggressive cleanup of all scanner resources."""
        print('Performing aggressive scanner cleanup...')

        # Force abort all scanners
        self.force_abort_scanners()

        # Clean up scan data
        self.cleanup_scan_data()

        # Clean up database connections
        self.cleanup_database_connections()

        # Clean up scanner threads
        self.cleanup_scanner_threads()

        # Clean up test threads
        cleanup_test_threads()

        # Clean up shared pools
        cleanup_shared_pools()

        # Brief pause for cleanup to complete
        time.sleep(0.2)

    def check_scanner_integrity(self: 'TestScannerBase') -> list:
        """Check that all scanners are in a clean state.

        Returns:
            list: A list of integrity issue strings.
        """
        issues = []

        for scanner, _resource_id, _scan_id in self._test_scanners:
            scanner_name = scanner.__class__.__name__

            # Check if scanner is still running
            if hasattr(scanner, '_SpiderFootScanner__scanStatus'):
                status = getattr(
                    scanner, '_SpiderFootScanner__scanStatus', None
                )
                if status and status not in [
                    'FINISHED', 'ABORTED', 'ERROR-FAILED'
                ]:
                    issues.append(
                        'Scanner ' + scanner_name
                        + ' still running: ' + str(status)
                    )

            # Check for active threads
            if hasattr(scanner, '_SpiderFootScanner__moduleThreads'):
                threads = getattr(
                    scanner,
                    '_SpiderFootScanner__moduleThreads', {}
                )
                if threads:
                    active_threads = [
                        t for t in threads.values() if t.is_alive()
                    ]
                    if active_threads:
                        issues.append(
                            'Scanner ' + scanner_name
                            + ' has '
                            + str(len(active_threads))
                            + ' active threads'
                        )

        return issues

    def tearDown(self: 'TestScannerBase') -> None:
        """Enhanced tearDown with comprehensive scanner cleanup."""
        try:
            # Aggressive cleanup first
            self.aggressive_scanner_cleanup()

            # Clean up all registered resources
            self.resource_manager.cleanup_category('scanner')
            self.resource_manager.cleanup_category('database')
            self.resource_manager.cleanup_category('scan')
            self.resource_manager.cleanup_category('thread')

            # Check scanner integrity
            integrity_issues = self.check_scanner_integrity()
            if integrity_issues:
                print('Scanner integrity issues:')
                for issue in integrity_issues:
                    print('    - ' + issue)

            # Final thread cleanup
            cleanup_test_threads()
            cleanup_shared_pools()

            # Check for thread leaks
            current_count = threading.active_count()
            leaked = current_count - self.initial_thread_count

            if leaked > 0:
                print(
                    'Thread leak detected: '
                    + str(leaked) + ' threads'
                )

                # List remaining threads
                remaining_threads = threading.enumerate()
                print('Remaining threads:')
                for thread in remaining_threads:
                    print(
                        '  - ' + thread.name
                        + ' (alive: '
                        + str(thread.is_alive()) + ')'
                    )

        except Exception as e:
            print('Error during scanner tearDown: ' + str(e))

        finally:
            # Clean up temporary directory
            try:
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                # Suppress any filesystem cleanup errors
                pass

            # Clear tracking lists
            self._test_scanners.clear()
            self._test_databases.clear()
            self._scan_instances.clear()

            # Call parent tearDown
            super().tearDown()

            print(
                'Tearing down scanner test class: '
                + self.__class__.__name__
            )

    @classmethod
    def setUpClass(cls: type) -> None:
        """Set up class-level scanner resources."""
        super().setUpClass()
        print('Setting up scanner test class: ' + cls.__name__)

    @classmethod
    def tearDownClass(cls: type) -> None:
        """Clean up class-level scanner resources."""
        try:
            print(
                'Tearing down scanner test class: ' + cls.__name__
            )

            # Force cleanup of any remaining resources
            manager = get_test_resource_manager()
            manager.force_cleanup_leaked_resources()

            # Final cleanup
            cleanup_test_threads()
            cleanup_shared_pools()

        except Exception as e:
            print(
                'Error during scanner tearDownClass: ' + str(e)
            )

        finally:
            super().tearDownClass()


class TestScannerAdvanced(TestScannerBase):
    """Advanced scanner test base with timeout protection and performance monitoring.

    Features:
    - Scan timeout protection
    - Performance metrics
    - Memory usage tracking
    - Database integrity checks
    """

    def setUp(self: 'TestScannerAdvanced') -> None:
        """Set up advanced scanner test features."""
        super().setUp()

        # Timeout settings
        self.scan_timeout = 60.0  # 60 second default scan timeout
        self.module_timeout = 30.0  # 30 second module timeout

        # Performance tracking
        self.performance_metrics = {}
        self.memory_usage = {}

    def run_scan_with_timeout(
        self: 'TestScannerAdvanced',
        scanner: Any,
        timeout: float = None,
    ) -> Any:  # noqa: DAR401
        """Run a scanner with timeout protection.

        Args:
            scanner: Scanner to run.
            timeout: Timeout in seconds.

        Returns:
            Any: Scanner result.

        Raises:
            TimeoutError: If scan exceeds timeout.
        """
        timeout = timeout or self.scan_timeout

        result = [None]
        captured_error = [None]

        def scan_target() -> None:
            try:
                result[0] = scanner.start()
            except Exception as e:
                captured_error[0] = e

        scan_thread = threading.Thread(
            target=scan_target,
            name='scan_timeout_' + str(int(time.time()))
        )

        self.register_thread(scan_thread)

        start_time = time.time()
        scan_thread.start()
        scan_thread.join(timeout)

        elapsed = time.time() - start_time

        if scan_thread.is_alive():
            # Force abort the scanner
            if hasattr(scanner, '_SpiderFootScanner__setStatus'):
                scanner._SpiderFootScanner__setStatus('ABORTED')

            raise TimeoutError(
                'Scan timed out after ' + str(timeout) + ' seconds'
            )

        if captured_error[0]:
            raise captured_error[0]

        # Record performance metrics
        self.performance_metrics['scan_duration'] = elapsed

        return result[0]

    def monitor_memory_usage(
        self: 'TestScannerAdvanced', description: str
    ) -> None:
        """Monitor memory usage at a specific point.

        Args:
            description: Description of the monitoring point.
        """
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            self.memory_usage[description] = {
                'rss': memory_info.rss,
                'vms': memory_info.vms,
                'timestamp': time.time()
            }
        except ImportError:
            # psutil not available, skip memory monitoring
            pass

    def check_database_integrity(
        self: 'TestScannerAdvanced', database: Any
    ) -> list:
        """Check database integrity after test.

        Args:
            database: Database instance to check.

        Returns:
            list: List of integrity issues found.
        """
        issues = []

        try:
            # Check for open connections
            if (hasattr(database, 'connection')
                    and database.connection
                    and not database.connection.closed):
                issues.append('Database connection not closed')

            # Check for uncommitted transactions
            if (hasattr(database, 'in_transaction')
                    and database.in_transaction()):
                issues.append('Uncommitted transaction found')

            # Check for temp tables
            if hasattr(database, 'temp_tables') and database.temp_tables:
                issues.append(
                    str(len(database.temp_tables))
                    + ' temp tables not cleaned up'
                )

        except Exception as e:
            issues.append(
                'Error checking database integrity: ' + str(e)
            )

        return issues

    def assertScanCompleted(
        self: 'TestScannerAdvanced', scanner: Any
    ) -> None:
        """Assert that a scan completed successfully.

        Args:
            scanner: Scanner instance to check.
        """
        if hasattr(scanner, '_SpiderFootScanner__scanStatus'):
            status = scanner._SpiderFootScanner__scanStatus
            self.assertIn(
                status, ['FINISHED', 'ABORTED'],
                'Scan did not complete properly: ' + str(status)
            )

    def assertNoActiveThreads(
        self: 'TestScannerAdvanced', scanner: Any
    ) -> None:
        """Assert that scanner has no active threads.

        Args:
            scanner: Scanner instance to check.
        """
        if hasattr(scanner, '_SpiderFootScanner__moduleThreads'):
            threads = getattr(
                scanner, '_SpiderFootScanner__moduleThreads', {}
            )
            active_threads = [
                t for t in threads.values() if t.is_alive()
            ]
            self.assertEqual(
                len(active_threads), 0,
                'Scanner has '
                + str(len(active_threads))
                + ' active threads'
            )

    def tearDown(self: 'TestScannerAdvanced') -> None:
        """Enhanced tearDown with integrity checks."""
        try:
            # Check database integrity
            for database, _resource_id in self._test_databases:
                issues = self.check_database_integrity(database)
                if issues:
                    print(
                        'Database integrity issues: '
                        + str(issues)
                    )

            # Monitor final memory usage
            self.monitor_memory_usage('teardown')

            # Print performance metrics
            if self.performance_metrics:
                print(
                    'Performance metrics: '
                    + str(self.performance_metrics)
                )

            # Run base tearDown
            super().tearDown()

        except Exception as e:
            print(
                'Error in advanced scanner tearDown: ' + str(e)
            )


# Convenience decorator for scanner tests
def scanner_test(timeout: float = 60.0) -> Any:
    """Decorate a test method with scanner-specific features.

    Args:
        timeout: Scan timeout in seconds.

    Returns:
        Any: The decorator function.
    """
    def decorator(test_method: Any) -> Any:
        """Apply scanner test decoration.

        Args:
            test_method: The test method to decorate.

        Returns:
            Any: The wrapped test method.
        """
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            """Wrap the test method with timeout handling.

            Args:
                self: The test instance.
                *args: Positional arguments.
                **kwargs: Keyword arguments.

            Returns:
                Any: The test method result.
            """
            # Set timeout for this test
            if hasattr(self, 'scan_timeout'):
                original_timeout = self.scan_timeout
                self.scan_timeout = timeout

            try:
                return test_method(self, *args, **kwargs)
            finally:
                # Restore original timeout
                if hasattr(self, 'scan_timeout'):
                    self.scan_timeout = original_timeout

        wrapper.__name__ = test_method.__name__
        wrapper.__doc__ = test_method.__doc__
        return wrapper

    return decorator
