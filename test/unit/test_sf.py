"""Unit tests for sf.py."""

import unittest
from unittest import mock
import os
import sys
import argparse
import tempfile
import cherrypy

# Mock modules to avoid importing real ones in testing
sys.modules['sflib'] = mock.MagicMock()
sys.modules['sfscan'] = mock.MagicMock()
sys.modules['sfwebui'] = mock.MagicMock()

# Now we can safely import from sf.py
from sf import parse_args, load_modules, validate_scan_arguments, process_target, prepare_modules, start_web_server


class TestSf(unittest.TestCase):
    """Test cases for sf.py main wrapper module."""
    
    def setUp(self):
        """Set up test case."""
        # Create a mock config for testing
        self.config = {
            '_debug': False,
            '_maxthreads': 3,
            '__database': ':memory:',
            '__modules__': {
                'sfp_module1': {
                    'provides': ['DOMAIN_NAME'],
                    'meta': {
                        'flags': ['passive']
                    }
                },
                'sfp_module2': {
                    'provides': ['IP_ADDRESS'],
                    'meta': {
                        'flags': ['investigate']
                    }
                },
                'sfp__stor_stdout': {
                    'opts': {}
                }
            }
        }
        
    def test_parse_args(self):
        """Test argument parser."""
        with mock.patch('sys.argv', ['sf.py', '-d', '--start', 'example.com']):
            args = parse_args()
            self.assertTrue(args.debug)
            self.assertEqual(args.start, 'example.com')
    
    @mock.patch('os.path.isdir')
    @mock.patch('spiderfoot.SpiderFootHelpers.loadModulesAsDict')
    def test_load_modules(self, mock_load_modules, mock_isdir):
        """Test module loading."""
        mock_isdir.return_value = True
        mock_load_modules.return_value = {
            'sfp_module1': {'provides': ['DOMAIN_NAME']},
            'sfp_module2': {'provides': ['IP_ADDRESS']}
        }
        
        result = load_modules({})
        
        self.assertTrue(result)
        mock_load_modules.assert_called_once()
    
    def test_validate_scan_arguments_valid(self):
        """Test validation of scan arguments with valid args."""
        args = mock.MagicMock()
        args.start = "example.com"
        args.x = False
        args.t = None
        args.m = None
        args.r = None
        args.o = None
        args.H = False
        args.D = False
        
        self.assertTrue(validate_scan_arguments(args))
    
    def test_validate_scan_arguments_missing_target(self):
        """Test validation of scan arguments with missing target."""
        args = mock.MagicMock()
        args.start = None
        
        with mock.patch('sf.log') as mock_log:
            self.assertFalse(validate_scan_arguments(args))
            mock_log.error.assert_called_once()
    
    def test_validate_scan_arguments_invalid_combination(self):
        """Test validation of scan arguments with invalid combination."""
        args = mock.MagicMock()
        args.start = "example.com"
        args.x = True
        args.t = None
        
        with mock.patch('sf.log') as mock_log:
            self.assertFalse(validate_scan_arguments(args))
            mock_log.error.assert_called_once()
    
    def test_process_target_domain(self):
        """Test processing a domain target."""
        with mock.patch('spiderfoot.SpiderFootHelpers.targetTypeFromString', return_value="DOMAIN_NAME"):
            result = process_target("example.com")
            self.assertEqual(result, "example.com")
    
    def test_process_target_human_name(self):
        """Test processing a human name target."""
        with mock.patch('spiderfoot.SpiderFootHelpers.targetTypeFromString', return_value="HUMAN_NAME"):
            result = process_target("John Doe")
            self.assertEqual(result, "John Doe")
    
    def test_prepare_modules_all(self):
        """Test preparing all modules for a scan."""
        # Mock database and args
        dbh = mock.MagicMock()
        args = mock.MagicMock()
        args.t = None
        args.m = None
        args.u = None
        
        result = prepare_modules(args, dbh, self.config, "DOMAIN_NAME")
        
        self.assertIn('sfp__stor_stdout', result)
        self.assertGreaterEqual(len(result), 1)
    
    def test_prepare_modules_by_type(self):
        """Test preparing modules by type."""
        # Mock database and args
        dbh = mock.MagicMock()
        args = mock.MagicMock()
        args.t = "DOMAIN_NAME"
        args.m = None
        args.u = None
        args.f = None
        args.F = None
        args.o = None
        args.n = None
        args.r = None
        args.S = None
        args.D = None
        args.x = None
        
        # Mock signal handling
        with mock.patch('signal.signal'):
            result = prepare_modules(args, dbh, self.config, "DOMAIN_NAME")
            
            self.assertIn('sfp__stor_stdout', result)
            self.assertIn('sfp_module1', result)
            self.assertNotIn('sfp_module2', result)
    
    def test_prepare_modules_by_module(self):
        """Test preparing modules by module name."""
        # Mock database and args
        dbh = mock.MagicMock()
        args = mock.MagicMock()
        args.t = None
        args.m = "sfp_module1"
        args.u = None
        args.f = None
        args.F = None
        args.o = None
        args.n = None
        args.r = None
        args.S = None
        args.D = None
        args.x = None
        
        # Mock signal handling
        with mock.patch('signal.signal'):
            result = prepare_modules(args, dbh, self.config, "DOMAIN_NAME")
            
            self.assertIn('sfp__stor_stdout', result)
            self.assertIn('sfp_module1', result)
            self.assertNotIn('sfp_module2', result)
    
    def test_prepare_modules_by_usecase(self):
        """Test preparing modules by use case."""
        # Mock database and args
        dbh = mock.MagicMock()
        args = mock.MagicMock()
        args.t = None
        args.m = None
        args.u = "passive"
        args.f = None
        args.F = None
        args.o = None
        args.n = None
        args.r = None
        args.S = None
        args.D = None
        args.x = None
        
        # Mock signal handling
        with mock.patch('signal.signal'):
            result = prepare_modules(args, dbh, self.config, "DOMAIN_NAME")
            
            self.assertIn('sfp__stor_stdout', result)
            self.assertIn('sfp_module1', result)
            self.assertNotIn('sfp_module2', result)
    
    @mock.patch('cherrypy.config.update')
    @mock.patch('cherrypy.quickstart')
    def test_start_web_server(self, mock_quickstart, mock_config_update):
        """Test starting the web server."""
        config = {
            '__webserver_host': '127.0.0.1',
            '__webserver_port': 5001,
            '__webserver_root': '/'
        }
        
        with mock.patch('sfwebui.SpiderFootWebUi') as mock_webui:
            start_web_server(config)
            
            mock_config_update.assert_called_once()
            mock_quickstart.assert_called_once()


if __name__ == '__main__':
    unittest.main()
