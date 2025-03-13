"""Unit tests for sfwebui.py."""

from sfwebui import SpiderFootWebUi
import unittest
from unittest import mock
import json
import tempfile
import os
import sys

# Mock modules to avoid importing real ones in testing
sys.modules["cherrypy"] = mock.MagicMock()
sys.modules["spiderfoot"] = mock.MagicMock()
sys.modules["sflib"] = mock.MagicMock()
sys.modules["sfscan"] = mock.MagicMock()

# Now we can safely import from sfwebui.py


class TestSpiderFootWebUi(unittest.TestCase):
    """Test cases for SpiderFootWebUi class."""

    def setUp(self):
        """Set up test case."""
        # Mock config
        self.config = {
            "_debug": False,
            "__database": ":memory:",
            "_maxthreads": 3,
            "__modules__": {
                "sfp_dns": {"provides": ["DNS_NAME"]},
                "sfp_whois": {"provides": ["WHOIS_DATA"]},
            },
        }

        # Create a temporary directory for templates
        self.temp_dir = tempfile.mkdtemp()

        # Create WebUI instance
        with mock.patch("os.path.dirname", return_value=self.temp_dir):
            with mock.patch("sflib.SpiderFoot"):
                self.webui = SpiderFootWebUi(self.config)
                self.webui.sfdb = mock.MagicMock()
                self.webui.sf = mock.MagicMock()

    def tearDown(self):
        """Clean up after test case."""
        # Remove temporary directory
        os.rmdir(self.temp_dir)

    def test_init(self):
        """Test initialization."""
        with mock.patch("os.path.dirname", return_value=self.temp_dir):
            with mock.patch("sflib.SpiderFoot"):
                webui = SpiderFootWebUi(self.config)
                self.assertEqual(webui.config, self.config)

    def test_index(self):
        """Test index page."""
        with mock.patch.object(self.webui, "cleanUserInput", return_value=""):
            with mock.patch.object(self.webui, "render_template") as mock_render:
                self.webui.index()
                mock_render.assert_called_once()
                args, _ = mock_render.call_args
                self.assertEqual(args[0], "NEWSCAN")

    def test_newscan(self):
        """Test new scan page."""
        with mock.patch.object(self.webui, "cleanUserInput", return_value=""):
            with mock.patch.object(self.webui, "render_template") as mock_render:
                self.webui.newscan()
                mock_render.assert_called_once()
                args, _ = mock_render.call_args
                self.assertEqual(args[0], "NEWSCAN")

    @mock.patch("cherrypy.request")
    def test_startscan(self, mock_request):
        """Test starting a scan."""
        # Mock form data
        mock_request.method = "POST"
        mock_request.headers = {
            "Content-Type": "application/x-www-form-urlencoded"}
        mock_form_data = {
            "scanname": "Test Scan",
            "scantarget": "example.com",
            "usecase": "all",
            "modulelist": "",
        }

        with mock.patch.object(self.webui, "getform", return_value=mock_form_data):
            with mock.patch.object(
                self.webui, "cleanUserInput", return_value="cleaned"
            ):
                with mock.patch(
                    "sflib.SpiderFoot.genScanInstanceId", return_value="abc123"
                ):
                    with mock.patch("sfscan.startSpiderFootScanner") as mock_start_scan:
                        with mock.patch("cherrypy.HTTPRedirect") as mock_redirect:
                            self.webui.startscan()

                            # Check if scan was started
                            mock_start_scan.assert_called_once()

                            # Check if redirect happened
                            mock_redirect.assert_called_once()

    @mock.patch("cherrypy.request")
    def test_startscan_invalid(self, mock_request):
        """Test starting a scan with invalid data."""
        # Mock form data with missing required fields
        mock_request.method = "POST"
        mock_request.headers = {
            "Content-Type": "application/x-www-form-urlencoded"}
        mock_form_data = {
            "scanname": "",  # Missing scan name
            "scantarget": "example.com",
            "usecase": "all",
            "modulelist": "",
        }

        with mock.patch.object(self.webui, "getform", return_value=mock_form_data):
            with mock.patch.object(self.webui, "cleanUserInput", return_value=""):
                with mock.patch.object(self.webui, "render_template") as mock_render:
                    self.webui.startscan()

                    # Check if rendering template with error
                    mock_render.assert_called_once()
                    args, kwargs = mock_render.call_args
                    self.assertEqual(args[0], "NEWSCAN")
                    self.assertIn("errors", kwargs)

    def test_stopscanrun(self):
        """Test stopping a scan."""
        with mock.patch.object(
            self.webui.sfdb,
            "scanInstanceGet",
            return_value=["", "", "", "", "", "RUNNING"],
        ):
            with mock.patch.object(self.webui.sfdb, "scanInstanceSet") as mock_set:
                with mock.patch("cherrypy.HTTPRedirect") as mock_redirect:
                    self.webui.stopscanrun("abc123")

                    # Check if scan was stopped
                    mock_set.assert_called_once_with(
                        "abc123", status="ABORT-REQUESTED")

                    # Check if redirect happened
                    mock_redirect.assert_called_once()

    def test_stopscanrun_not_running(self):
        """Test stopping a scan that's not running."""
        with mock.patch.object(
            self.webui.sfdb,
            "scanInstanceGet",
            return_value=["", "", "", "", "", "FINISHED"],
        ):
            with mock.patch.object(self.webui.sfdb, "scanInstanceSet") as mock_set:
                with mock.patch("cherrypy.HTTPRedirect") as mock_redirect:
                    self.webui.stopscanrun("abc123")

                    # Check scan status was not changed
                    mock_set.assert_not_called()

                    # For a scan not running, it should still redirect
                    mock_redirect.assert_called_once()

    def test_scandeletefromdashboard(self):
        """Test deleting a scan from dashboard."""
        with mock.patch.object(self.webui.sfdb, "scanInstanceDelete") as mock_delete:
            with mock.patch("cherrypy.HTTPRedirect") as mock_redirect:
                self.webui.scandeletefromdashboard("abc123")

                # Check if scan was deleted
                mock_delete.assert_called_once_with("abc123")

                # Check if redirect happened
                mock_redirect.assert_called_once()

    def test_scanviz(self):
        """Test scan visualization."""
        with mock.patch.object(self.webui, "render_template") as mock_render:
            with mock.patch.object(
                self.webui.sfdb,
                "scanInstanceGet",
                return_value=["Test Scan", "example.com", 0, 0, 0, "FINISHED"],
            ):
                self.webui.scanviz("abc123", "all")

                # Check if template was rendered
                mock_render.assert_called_once()
                args, kwargs = mock_render.call_args
                self.assertEqual(args[0], "SCANVIZ")
                self.assertEqual(kwargs["id"], "abc123")
                self.assertEqual(kwargs["name"], "Test Scan")
                self.assertEqual(kwargs["filter"], "all")

    def test_scanopts(self):
        """Test scan options page."""
        # First, mock the database to return a scan
        with mock.patch.object(
            self.webui.sfdb,
            "scanInstanceGet",
            return_value=["Test Scan", "example.com", 0, 0, 0, "FINISHED"],
        ):
            # Then, mock the scan config
            with mock.patch.object(
                self.webui.sfdb, "scanConfigGet", return_value={"module.enabled": "1"}
            ):
                # Finally, mock the render_template
                with mock.patch.object(self.webui, "render_template") as mock_render:
                    self.webui.scanopts("abc123")

                    # Check if template was rendered
                    mock_render.assert_called_once()
                    args, kwargs = mock_render.call_args
                    self.assertEqual(args[0], "SCANOPTS")
                    self.assertEqual(kwargs["id"], "abc123")
                    self.assertEqual(kwargs["name"], "Test Scan")

    @mock.patch("cherrypy.request")
    def test_savescanopts(self, mock_request):
        """Test saving scan options."""
        # Mock form data
        mock_request.method = "POST"
        mock_request.headers = {
            "Content-Type": "application/x-www-form-urlencoded"}
        mock_form_data = {"module.enabled": "1",
                          "module.opt1": "val1", "_id": "abc123"}

        with mock.patch.object(self.webui, "getform", return_value=mock_form_data):
            with mock.patch.object(self.webui.sfdb, "scanConfigSet") as mock_set:
                with mock.patch("cherrypy.HTTPRedirect") as mock_redirect:
                    self.webui.savescanopts("abc123")

                    # Check if scan options were saved
                    mock_set.assert_called_once()

                    # Check if redirect happened
                    mock_redirect.assert_called_once()

    def test_rerunscan(self):
        """Test re-running a scan."""
        # Mock database to return scan data and config
        scan_data = ["Test Scan", "example.com", 0, 0, 0, "FINISHED"]
        scan_config = {
            "modules": '["sfp_dns", "sfp_whois"]',
            "types": "",
            "usecase": "all",
        }

        with mock.patch.object(
            self.webui.sfdb, "scanInstanceGet", return_value=scan_data
        ):
            with mock.patch.object(
                self.webui.sfdb, "scanConfigGet", return_value=scan_config
            ):
                with mock.patch(
                    "sflib.SpiderFoot.genScanInstanceId", return_value="new_scan_id"
                ):
                    with mock.patch("sfscan.startSpiderFootScanner") as mock_start_scan:
                        with mock.patch("cherrypy.HTTPRedirect") as mock_redirect:
                            self.webui.rerunscan("abc123")

                            # Check if new scan was started with same config
                            mock_start_scan.assert_called_once()
                            # Check redirect
                            mock_redirect.assert_called_once()

    def test_rerunscan_invalid_id(self):
        """Test re-running a scan with invalid scan ID."""
        with mock.patch.object(self.webui.sfdb, "scanInstanceGet", return_value=None):
            with mock.patch("cherrypy.HTTPRedirect") as mock_redirect:
                self.webui.rerunscan("invalid_id")
                # Should redirect back to scan list
                mock_redirect.assert_called_once()

    def test_resultexport(self):
        """Test exporting scan results."""
        scan_data = ["Test Scan", "example.com", 0, 0, 0, "FINISHED"]

        with mock.patch.object(
            self.webui.sfdb, "scanInstanceGet", return_value=scan_data
        ):
            with mock.patch.object(self.webui, "cleanUserInput", return_value="gexf"):
                with mock.patch.object(
                    self.webui, "exportResultsGEXF"
                ) as mock_export_gexf:
                    # Set up mock response
                    mock_export_gexf.return_value = "GEXF_DATA"

                    # Call method
                    result = self.webui.resultexport("abc123", "gexf")

                    # Verify export was called
                    mock_export_gexf.assert_called_once_with(
                        "abc123", "example.com")
                    self.assertEqual(result, "GEXF_DATA")

    def test_resultexport_json(self):
        """Test exporting scan results as JSON."""
        scan_data = ["Test Scan", "example.com", 0, 0, 0, "FINISHED"]

        with mock.patch.object(
            self.webui.sfdb, "scanInstanceGet", return_value=scan_data
        ):
            with mock.patch.object(self.webui, "cleanUserInput", return_value="json"):
                with mock.patch.object(
                    self.webui, "exportResultsJSON"
                ) as mock_export_json:
                    # Set up mock response
                    mock_export_json.return_value = "JSON_DATA"

                    # Call method
                    result = self.webui.resultexport("abc123", "json")

                    # Verify export was called
                    mock_export_json.assert_called_once_with(
                        "abc123", "example.com")
                    self.assertEqual(result, "JSON_DATA")

    def test_eventresults(self):
        """Test getting event results."""
        with mock.patch.object(self.webui, "cleanUserInput", return_value="IP_ADDRESS"):
            with mock.patch.object(
                self.webui.sfdb,
                "scanInstanceGet",
                return_value=["Test Scan", "example.com", 0, 0, 0, "FINISHED"],
            ):
                with mock.patch.object(
                    self.webui.sfdb, "scanResultEvent"
                ) as mock_result:
                    # Set up mock response
                    mock_result.return_value = [
                        [
                            1,
                            "192.168.0.1",
                            "example.com",
                            "sfp_dns",
                            "IP_ADDRESS",
                            100,
                            100,
                            1,
                            "hash1",
                            "source_hash",
                            "module1",
                            12345,
                        ]
                    ]

                    # Call method
                    with mock.patch.object(self.webui, "jsonify") as mock_jsonify:
                        self.webui.eventresults("abc123", "IP_ADDRESS")

                        # Verify database call and JSON response
                        mock_result.assert_called_once_with(
                            "abc123", eventType="IP_ADDRESS"
                        )
                        mock_jsonify.assert_called_once()

    def test_scansummary(self):
        """Test getting scan summary."""
        with mock.patch.object(
            self.webui.sfdb,
            "scanInstanceGet",
            return_value=["Test Scan", "example.com", 0, 0, 0, "FINISHED"],
        ):
            with mock.patch.object(
                self.webui.sfdb, "scanResultSummary"
            ) as mock_summary:
                # Set up mock response
                mock_summary.return_value = [
                    ["IP_ADDRESS", 5], ["DOMAIN_NAME", 3]]

                # Call method
                with mock.patch.object(self.webui, "jsonify") as mock_jsonify:
                    self.webui.scansummary("abc123")

                    # Verify database call and JSON response
                    mock_summary.assert_called_once_with("abc123")
                    mock_jsonify.assert_called_once()

    def test_scaneventresults(self):
        """Test getting scan event results."""
        with mock.patch.object(
            self.webui.sfdb,
            "scanInstanceGet",
            return_value=["Test Scan", "example.com", 0, 0, 0, "FINISHED"],
        ):
            with mock.patch.object(self.webui, "render_template") as mock_render:
                self.webui.scaneventresults("abc123", "ALL")

                # Check if template was rendered
                mock_render.assert_called_once()
                args, kwargs = mock_render.call_args
                self.assertEqual(args[0], "SCANRESULTS")
                self.assertEqual(kwargs["id"], "abc123")
                self.assertEqual(kwargs["name"], "Test Scan")
                self.assertEqual(kwargs["eventType"], "ALL")

    def test_cleanUserInput(self):
        """Test cleanUserInput method."""
        test_cases = [
            ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
            ("normal text", "normal text"),
            ("", ""),
            (None, None),
        ]

        for input_value, expected in test_cases:
            result = self.webui.cleanUserInput(input_value)
            self.assertEqual(result, expected)

    def test_jsonify(self):
        """Test jsonify method."""
        data = {"test": "value", "number": 123}

        # Replace the cherrypy.response mock with our own
        original_response = sys.modules["cherrypy"].response
        sys.modules["cherrypy"].response = mock.MagicMock()

        try:
            result = self.webui.jsonify(data)

            # Check that headers were set and data was serialized
            sys.modules["cherrypy"].response.headers[
                "Content-Type"
            ] = "application/json"
            self.assertEqual(result, json.dumps(data))
        finally:
            # Restore original mock
            sys.modules["cherrypy"].response = original_response

    def test_error_page(self):
        """Test error page handler."""
        with mock.patch.object(self.webui, "render_template") as mock_render:
            error_msg = "Test error"
            self.webui.error_page(error_msg)

            # Check if error template was rendered
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            self.assertEqual(args[0], "ERROR")
            self.assertEqual(kwargs["message"], error_msg)


if __name__ == "__main__":
    unittest.main()
