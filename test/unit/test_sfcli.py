"""Unit tests for sfcli.py."""

import unittest
from unittest import mock
import io
import sys
import requests
import json

# Mock modules to avoid importing real ones in testing
sys.modules['spiderfoot'] = mock.MagicMock()

# Import the CLI class
from sfcli import SpiderFootCli


class TestSpiderFootCli(unittest.TestCase):
    """Test cases for SpiderFootCli class."""
    
    def setUp(self):
        """Set up test case."""
        # Create a test CLI instance
        with mock.patch.object(SpiderFootCli, '_get_modules_and_types'):
            self.cli = SpiderFootCli(url="http://localhost:5001")
            self.cli.modules = [
                ('sfp_dns', 'DNS Resolution'),
                ('sfp_whois', 'WHOIS Data')
            ]
            self.cli.types = [
                ('DOMAIN_NAME', 'Domain Name'),
                ('IP_ADDRESS', 'IP Address')
            ]
        
    def test_init(self):
        """Test initialization."""
        with mock.patch.object(SpiderFootCli, '_get_modules_and_types'):
            cli = SpiderFootCli(url="http://example.com:5001")
            self.assertEqual(cli.url, "http://example.com:5001")
            
    def test_request(self):
        """Test _request method."""
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {'data': 'test'}
        mock_response.status_code = 200
        
        with mock.patch('requests.request', return_value=mock_response) as mock_req:
            result = self.cli._request('GET', 'http://localhost:5001/api/test')
            mock_req.assert_called_once()
            self.assertEqual(result, {'data': 'test'})
    
    def test_request_json_error(self):
        """Test _request method with JSON error."""
        mock_response = mock.MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError('test', 'doc', 0)
        mock_response.text = 'plain text'
        mock_response.status_code = 200
        
        with mock.patch('requests.request', return_value=mock_response) as mock_req:
            result = self.cli._request('GET', 'http://localhost:5001/api/test')
            mock_req.assert_called_once()
            self.assertEqual(result, {'content': 'plain text'})
    
    def test_request_exception(self):
        """Test _request method with exception."""
        with mock.patch('requests.request', side_effect=requests.exceptions.RequestException('test error')):
            with self.assertRaises(Exception):
                self.cli._request('GET', 'http://localhost:5001/api/test')
    
    def test_do_exit(self):
        """Test exit command."""
        result = self.cli.do_exit("")
        self.assertTrue(result)
    
    @mock.patch('os.system')
    def test_do_clear(self, mock_system):
        """Test clear command."""
        self.cli.do_clear("")
        mock_system.assert_called_once()
    
    @mock.patch('sys.stdout', new_callable=io.StringIO)
    def test_do_help(self, mock_stdout):
        """Test help command."""
        self.cli.do_help("")
        output = mock_stdout.getvalue()
        self.assertIn("SpiderFoot CLI Commands", output)
        self.assertIn("General Commands", output)
        self.assertIn("Scan Commands", output)
    
    def test_do_scans(self):
        """Test scans command."""
        mock_response = {'scans': [
            {'id': 'abc123', 'target': 'example.com', 'status': 'FINISHED', 
             'created': 1600000000, 'ended': 1600001000, 'results': 100}
        ]}
        
        with mock.patch.object(self.cli, '_request', return_value=mock_response):
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_scans("")
                output = mock_stdout.getvalue()
                self.assertIn("ID", output)
                self.assertIn("Target", output)
                self.assertIn("Status", output)
                self.assertIn("example.com", output)
                self.assertIn("FINISHED", output)
    
    def test_do_scans_empty(self):
        """Test scans command with empty response."""
        mock_response = {'scans': []}
        
        with mock.patch.object(self.cli, '_request', return_value=mock_response):
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_scans("")
                output = mock_stdout.getvalue()
                self.assertIn("No scans found", output)
    
    def test_do_start_scan(self):
        """Test start scan command."""
        mock_response = {'id': 'abc123'}
        
        with mock.patch.object(self.cli, '_request', return_value=mock_response):
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_start("scan example.com sfp_dns,sfp_whois")
                output = mock_stdout.getvalue()
                self.assertIn("Scan started, ID: abc123", output)
    
    def test_do_start_scan_usecase(self):
        """Test start scan command with use case."""
        mock_response = {'id': 'abc123'}
        
        with mock.patch.object(self.cli, '_request', return_value=mock_response):
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_start("scan example.com passive")
                output = mock_stdout.getvalue()
                self.assertIn("Using modules matching use case: passive", output)
                self.assertIn("Scan started, ID: abc123", output)
    
    def test_do_start_scan_types(self):
        """Test start scan command with event types."""
        mock_response = {'id': 'abc123'}
        
        with mock.patch.object(self.cli, '_request', return_value=mock_response):
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_start("scan example.com DOMAIN_NAME")
                output = mock_stdout.getvalue()
                self.assertIn("Using modules supporting types: DOMAIN_NAME", output)
                self.assertIn("Scan started, ID: abc123", output)
    
    def test_do_stop_scan(self):
        """Test stop scan command."""
        with mock.patch.object(self.cli, '_request') as mock_request:
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_stop("scan abc123")
                mock_request.assert_called_once()
                output = mock_stdout.getvalue()
                self.assertIn("Successfully requested stop for scan abc123", output)
    
    def test_do_delete_scan(self):
        """Test delete scan command."""
        with mock.patch.object(self.cli, '_request') as mock_request:
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_delete("scan abc123")
                mock_request.assert_called_once()
                output = mock_stdout.getvalue()
                self.assertIn("Successfully deleted scan abc123", output)
    
    def test_do_scaninfo(self):
        """Test scaninfo command."""
        mock_response = {
            'id': 'abc123',
            'name': 'Test Scan',
            'target': 'example.com',
            'status': 'FINISHED',
            'created': 1600000000,
            'started': 1600000100,
            'ended': 1600001000
        }
        
        with mock.patch.object(self.cli, '_request', return_value=mock_response):
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_scaninfo("abc123")
                output = mock_stdout.getvalue()
                self.assertIn("Scan Information", output)
                self.assertIn("ID", output)
                self.assertIn("abc123", output)
                self.assertIn("Target", output)
                self.assertIn("example.com", output)
    
    def test_do_data(self):
        """Test data command."""
        mock_response = {
            'results': [
                {
                    'type': 'DOMAIN_NAME',
                    'module': 'sfp_dns',
                    'data': 'example.com',
                    'source_data': 'source'
                }
            ]
        }
        
        with mock.patch.object(self.cli, '_request', return_value=mock_response):
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_data("abc123")
                output = mock_stdout.getvalue()
                self.assertIn("Type: DOMAIN_NAME", output)
                self.assertIn("Module: sfp_dns", output)
                self.assertIn("Data: example.com", output)
    
    def test_do_data_with_filters(self):
        """Test data command with filters."""
        mock_response = {'results': []}
        
        with mock.patch.object(self.cli, '_request', return_value=mock_response) as mock_req:
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                self.cli.do_data("abc123 type=DOMAIN_NAME module=sfp_dns")
                output = mock_stdout.getvalue()
                self.assertIn("No results found", output)
                
                # Check if parameters were passed correctly
                args, kwargs = mock_req.call_args
                self.assertEqual(kwargs['params'], {'type': 'DOMAIN_NAME', 'module': 'sfp_dns'})


if __name__ == '__main__':
    unittest.main()
