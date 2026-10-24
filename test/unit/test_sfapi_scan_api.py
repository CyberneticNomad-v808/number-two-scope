import os

# MUST set TESTING_MODE before importing sfapi to prevent Config() from
# attempting a real database connection at module load time (sfapi.py line 28)
os.environ['TESTING_MODE'] = '1'

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402
import sfapi  # noqa: E402


@pytest.fixture(autouse=True)
def mock_api_dependencies() -> None:
    """Mock all API dependencies for scan API tests.

    Yields:
        Tuple of mock_config and mock_db objects.
    """
    mock_config = MagicMock()
    mock_config.get_config.return_value = {
        '__database': 'postgresql://test:test@localhost:5432/spiderfoot_test',
        '__dbtype': 'postgresql',
        '__modules__': {},
        '__correlationrules__': [],
        '_debug': False,
        '__webaddr': '127.0.0.1',
        '__webport': '5001',
        '__webaddr_apikey': None,
        '__globaloptdescs__': {},
    }
    mock_config.config = mock_config.get_config()

    mock_db = MagicMock()
    mock_db.scanInstanceList.return_value = []
    mock_db.scanInstanceGet.return_value = None
    mock_db.scanResultEvent.return_value = []
    mock_db.scanConfigGet.return_value = {}
    mock_db.scanCorrelations.return_value = []
    mock_db.scanLogs.return_value = []
    mock_db.scanMetadataGet.return_value = {}
    mock_db.scanNotesGet.return_value = ''
    mock_db.search.return_value = []

    with patch('spiderfoot.api.dependencies.get_app_config', return_value=mock_config), \
         patch('spiderfoot.api.routers.scan.get_app_config', return_value=mock_config), \
         patch('spiderfoot.api.routers.scan.SpiderFootDb', return_value=mock_db), \
         patch('spiderfoot.api.dependencies.app_config', mock_config):
        yield mock_config, mock_db


client = TestClient(sfapi.app)


# --- SCAN ENDPOINTS ---
def test_list_scans() -> None:
    """Test listing scans returns 200 with scans key."""
    resp = client.get('/api/scans')
    assert resp.status_code == 200
    assert 'scans' in resp.json()


def test_create_scan_invalid() -> None:
    """Test creating scan with missing fields returns error."""
    resp = client.post('/api/scans', json={})
    assert resp.status_code in (400, 422)


def test_get_scan_not_found() -> None:
    """Test getting nonexistent scan returns 404."""
    resp = client.get('/api/scans/FAKESCANID')
    assert resp.status_code == 404


def test_delete_scan_not_found() -> None:
    """Test deleting nonexistent scan returns 404."""
    resp = client.delete('/api/scans/FAKESCANID')
    assert resp.status_code == 404


def test_delete_scan_full_not_found() -> None:
    """Test full-deleting nonexistent scan returns 404."""
    resp = client.delete('/api/scans/FAKESCANID/full')
    assert resp.status_code == 404


def test_stop_scan_not_found() -> None:
    """Test stopping nonexistent scan returns 404."""
    resp = client.post('/api/scans/FAKESCANID/stop')
    assert resp.status_code == 404


def test_export_scan_event_results_not_found() -> None:
    """Test exporting events for nonexistent scan returns error."""
    resp = client.get('/api/scans/FAKESCANID/events/export')
    assert resp.status_code in (404, 500)


def test_export_scan_json_multi_empty() -> None:
    """Test exporting multi-scan JSON with fake ID."""
    resp = client.get('/api/scans/export-multi?ids=FAKESCANID')
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.headers['content-type'].startswith('application/json')


def test_export_scan_search_results_not_found() -> None:
    """Test exporting search results for nonexistent scan returns error."""
    resp = client.get('/api/scans/FAKESCANID/search/export')
    assert resp.status_code in (404, 500)


def test_export_scan_viz_not_found() -> None:
    """Test exporting viz for nonexistent scan returns 404."""
    resp = client.get('/api/scans/FAKESCANID/viz')
    assert resp.status_code == 404


def test_export_scan_viz_multi_empty() -> None:
    """Test exporting multi-scan viz with fake ID."""
    resp = client.get('/api/scans/viz-multi?ids=FAKESCANID')
    assert resp.status_code in (404, 400)


def test_get_scan_options_not_found() -> None:
    """Test getting options for nonexistent scan returns empty dict."""
    resp = client.get('/api/scans/FAKESCANID/options')
    assert resp.status_code == 200
    assert resp.json() == {}


def test_rerun_scan_not_found() -> None:
    """Test rerunning nonexistent scan returns 404."""
    resp = client.post('/api/scans/FAKESCANID/rerun')
    assert resp.status_code == 404


def test_rerun_scan_multi_empty() -> None:
    """Test rerunning multi-scan with fake ID."""
    resp = client.post('/api/scans/rerun-multi?ids=FAKESCANID')
    assert resp.status_code == 200
    assert 'new_scan_ids' in resp.json()


def test_clone_scan_not_found() -> None:
    """Test cloning nonexistent scan returns 404."""
    resp = client.post('/api/scans/FAKESCANID/clone')
    assert resp.status_code == 404


def test_set_results_false_positive_invalid() -> None:
    """Test setting false positive with invalid data."""
    resp = client.post(
        '/api/scans/FAKESCANID/results/falsepositive',
        json={'resultids': ['id1'], 'fp': '2'}
    )
    assert resp.status_code in (400, 422)


def test_export_scan_logs_not_found() -> None:
    """Test exporting logs for nonexistent scan returns 404."""
    resp = client.get('/api/scans/FAKESCANID/logs/export')
    assert resp.status_code == 404


def test_export_scan_correlations_not_found() -> None:
    """Test exporting correlations for nonexistent scan."""
    resp = client.get('/api/scans/FAKESCANID/correlations/export')
    # Endpoint returns 200 with empty CSV when scan has no correlations
    assert resp.status_code in (200, 404)


def test_get_scan_metadata_not_found() -> None:
    """Test getting metadata for nonexistent scan returns 404."""
    resp = client.get('/api/scans/FAKESCANID/metadata')
    assert resp.status_code == 404


def test_update_scan_metadata_not_found() -> None:
    """Test updating metadata for nonexistent scan returns 404."""
    resp = client.patch('/api/scans/FAKESCANID/metadata', json={'foo': 'bar'})
    assert resp.status_code == 404


def test_get_scan_notes_not_found() -> None:
    """Test getting notes for nonexistent scan returns 404."""
    resp = client.get('/api/scans/FAKESCANID/notes')
    assert resp.status_code == 404


def test_update_scan_notes_not_found() -> None:
    """Test updating notes for nonexistent scan returns 404."""
    resp = client.patch('/api/scans/FAKESCANID/notes', json='test note')
    assert resp.status_code == 404


def test_archive_scan_not_found() -> None:
    """Test archiving nonexistent scan returns 404."""
    resp = client.post('/api/scans/FAKESCANID/archive')
    assert resp.status_code == 404


def test_unarchive_scan_not_found() -> None:
    """Test unarchiving nonexistent scan returns 404."""
    resp = client.post('/api/scans/FAKESCANID/unarchive')
    assert resp.status_code == 404


def test_clear_scan_not_found() -> None:
    """Test clearing nonexistent scan returns 404."""
    resp = client.post('/api/scans/FAKESCANID/clear')
    assert resp.status_code == 404
