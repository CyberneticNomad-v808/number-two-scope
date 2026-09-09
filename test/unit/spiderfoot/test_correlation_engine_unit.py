import pytest
from unittest.mock import MagicMock
from spiderfoot.correlation.rule_loader import RuleLoader
from spiderfoot.correlation.rule_executor import DefaultRuleExecutionStrategy
from spiderfoot.correlation.event_enricher import EventEnricher
from spiderfoot.correlation.result_aggregator import ResultAggregator

@pytest.fixture
def mock_dbh():
    dbh = MagicMock()
    dbh.get_events_for_scan.return_value = [
        {'type': 'EMAILADDR', 'data': 'unit@example.com', 'scan_id': 'scan1'}
    ]
    return dbh

def test_event_enricher_enrich_sources(mock_dbh):
    enricher = EventEnricher(mock_dbh)
    events = [{'id': 'event1', 'type': 'EMAILADDR', 'data': 'unit@example.com'}]
    enriched = enricher.enrich_sources('scan1', events)
    assert isinstance(enriched, list)

def test_event_enricher_enrich_entities(mock_dbh):
    enricher = EventEnricher(mock_dbh)
    events = [{'id': 'event1', 'type': 'EMAILADDR', 'data': 'unit@example.com'}]
    enriched = enricher.enrich_entities('scan1', events)
    assert isinstance(enriched, list)

def test_result_aggregator_count():
    aggregator = ResultAggregator()
    results = [
        {'meta': {}, 'result': 'A'},
        {'meta': {}, 'result': 'B'}
    ]
    count = aggregator.aggregate(results, method='count')
    assert count == 2

RULES_WITH_ALTERNATE_HEADLINE_PLACEHOLDERS = [
    'cert_expired', 'dns_zone_transfer_possible', 'email_in_multiple_breaches',
    'multiple_malicious', 'multiple_malicious_affiliate', 'multiple_malicious_cohost',
    'remote_desktop_exposed', 'root_path_needs_auth',
    'http_errors', 'vulnerability_high', 'vulnerability_critical',
    'vulnerability_mediumlow', 'stale_host',
    'data_from_docmeta', 'data_from_base64',
]

@pytest.mark.parametrize("rule_id", RULES_WITH_ALTERNATE_HEADLINE_PLACEHOLDERS)
def test_create_correlation_result_handles_alternate_headline_placeholders(rule_id):
    """
    Regression test for Item 4: rules whose headline template uses
    {source.data}/{entity.data}/{child.data} used to raise KeyError inside
    _create_correlation_result() (caught by a blanket except, silently
    dropping the correlation). Confirm each of these real rules now
    produces a real correlation id and a title with the placeholder
    substituted, not left as a literal '{...}' or dropped as None.
    """
    loader = RuleLoader('correlations/')
    loader.load_rules()
    rule = next((r for r in loader.rules if r.get('id') == rule_id), None)
    assert rule is not None, f"Could not find rule {rule_id} in correlations/"

    strategy = DefaultRuleExecutionStrategy()
    mock_dbh = MagicMock()
    mock_dbh.correlationResultCreate.return_value = 'fake-correlation-id'

    events = [{'hash': 'event1', 'type': 'DUMMY', 'data': 'example-value.test'}]
    correlation_id = strategy._create_correlation_result(
        mock_dbh, rule, scan_ids=['scan1'], group_key='example-value.test', events=events
    )

    assert correlation_id is not None, f"Rule {rule_id} failed to create a correlation result"
    assert mock_dbh.correlationResultCreate.called
    title = mock_dbh.correlationResultCreate.call_args.kwargs['correlationTitle']
    assert '{' not in title, f"Rule {rule_id} left an unsubstituted placeholder in title: {title!r}"
    assert 'example-value.test' in title, f"Rule {rule_id} title missing substituted value: {title!r}"

def test_rule_loader_from_dict():
    # Simulate loading rules from a dict
    loader = RuleLoader(None)
    loader.rules = [
        {'id': 'unit_rule', 'meta': {'name': 'Unit Rule'}}
    ]
    assert len(loader.rules) == 1
    assert loader.rules[0]['id'] == 'unit_rule'
