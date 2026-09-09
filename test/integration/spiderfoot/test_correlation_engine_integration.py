import pytest
import os
import uuid
from spiderfoot import SpiderFootDb
from spiderfoot.correlation.rule_executor import RuleExecutor
import yaml

def _insert_event(dbh, scan_id, event_type, data, module='test_module',
                   generated=0, source_event_hash='ROOT', false_positive=0):
    """Insert a row matching the real production tbl_scan_results schema."""
    event_hash = uuid.uuid4().hex
    dbh.dbh.execute(
        "INSERT INTO tbl_scan_results "
        "(scan_instance_id, hash, type, generated, module, data, false_positive, source_event_hash) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (scan_id, event_hash, event_type, generated, module, data, false_positive, source_event_hash)
    )
    return event_hash

def _ensure_scan_instance(dbh, scan_id, name=None):
    """Insert a tbl_scan_instance row for scan_id if one doesn't exist yet.

    tbl_scan_correlation_results.scan_instance_id has a real FK to
    tbl_scan_instance(guid), so any scan_id used to create a correlation
    result must exist there first.
    """
    dbh.dbh.execute(
        "INSERT INTO tbl_scan_instance (guid, name, seed_target, status) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT (guid) DO NOTHING",
        (scan_id, name or scan_id, 'test-target.example.com', 'FINISHED')
    )

@pytest.fixture
def dbh():
    # Build DSN from environment variables
    db_user = os.environ['SPIDERFOOT_DB_USER']
    db_pass = os.environ['SPIDERFOOT_DB_PASSWORD']
    db_host = os.environ['SPIDERFOOT_DB_HOST']
    db_port = os.environ['SPIDERFOOT_DB_PORT']
    db_name = os.environ['SPIDERFOOT_DB_NAME']
    dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    config = {'__database': dsn, '__dbtype': 'postgresql'}
    dbh = SpiderFootDb(config, init=True)
    scan_id = 'integration_scan'
    # Ensure table is dropped and created fresh, matching the REAL production
    # tbl_scan_results schema (see spiderfoot/db/db_core.py) rather than a
    # simplified stand-in -- _get_scan_events() queries the real columns
    # (scan_instance_id, hash, module, generated, source_event_hash,
    # false_positive), so the fixture must provide them.
    dbh.dbh.execute("DROP TABLE IF EXISTS tbl_scan_results")
    dbh.dbh.execute("""
        CREATE TABLE tbl_scan_results (
            scan_instance_id VARCHAR NOT NULL,
            hash VARCHAR NOT NULL,
            type VARCHAR NOT NULL,
            generated INT NOT NULL,
            module VARCHAR NOT NULL,
            data VARCHAR,
            false_positive INT NOT NULL DEFAULT 0,
            source_event_hash VARCHAR DEFAULT 'ROOT'
        )
    """)
    _ensure_scan_instance(dbh, scan_id)
    _insert_event(dbh, scan_id, 'EMAILADDR', 'integration@example.com')
    dbh.conn.commit()
    return dbh, scan_id

def test_correlation_engine_integration(dbh):
    dbh, scan_id = dbh
    sample_rule = {
        'id': 'integration_rule',
        'meta': {
            'name': 'Integration Rule',
            'description': 'Integration test rule',
            'risk': 'INFO',
            'scope': 'scan',
        },
        'collections': [
            {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': 'EMAILADDR'}]}}
        ],
        'aggregation': {'field': 'data'},
        'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': 1}],
        'headline': 'Integration headline {data}',
    }
    rules = [sample_rule]
    executor = RuleExecutor(dbh, rules, scan_ids=[scan_id])
    results = executor.run()
    print('DEBUG: correlation engine results:', results)
    assert 'integration_rule' in results
    assert 'meta' in results['integration_rule']
    assert 'matched' in results['integration_rule']
    assert results['integration_rule']['matched'] is True
    assert 'Integration Rule' in results['integration_rule']['meta']['name']
    assert results['integration_rule']['correlations_created'] > 0

def test_multiple_rules(dbh):
    dbh, scan_id = dbh
    rules = [
        {
            'id': 'match_rule',
            'meta': {'name': 'Match Rule', 'description': '', 'risk': 'INFO', 'scope': 'scan'},
            'collections': [
                {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': 'EMAILADDR'}]}}
            ],
            'aggregation': {'field': 'data'},
            'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': 1}],
            'headline': 'Match headline {data}',
        },
        {
            'id': 'no_match_rule',
            'meta': {'name': 'No Match Rule', 'description': '', 'risk': 'INFO', 'scope': 'scan'},
            'collections': [
                {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': 'SOMETHINGELSE'}]}}
            ],
            'aggregation': {'field': 'data'},
            'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': 1}],
            'headline': 'No match headline {data}',
        }
    ]
    executor = RuleExecutor(dbh, rules, scan_ids=[scan_id])
    results = executor.run()
    assert 'match_rule' in results
    assert 'no_match_rule' in results
    assert 'Match Rule' in results['match_rule']['meta']['name']
    assert 'No Match Rule' in results['no_match_rule']['meta']['name']
    assert results['match_rule']['matched'] is True
    assert results['no_match_rule']['matched'] is False

def test_threshold_logic(dbh):
    dbh, scan_id = dbh
    # Rule with threshold minimum 2, but only 1 event in DB
    rule = {
        'id': 'threshold_rule',
        'meta': {'name': 'Threshold Rule', 'description': '', 'risk': 'INFO', 'scope': 'scan'},
        'collections': [
            {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': 'EMAILADDR'}]}}
        ],
        'aggregation': {'field': 'data'},
        'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': 2}],
        'headline': 'Threshold headline {data}',
    }
    executor = RuleExecutor(dbh, [rule], scan_ids=[scan_id])
    results = executor.run()
    assert 'threshold_rule' in results
    assert 'Threshold Rule' in results['threshold_rule']['meta']['name']
    assert results['threshold_rule']['matched'] is False  # Should be False because threshold minimum 2 but only 1 event

def test_non_matching_event_type(dbh):
    dbh, scan_id = dbh
    # Rule for a type not present in DB
    rule = {
        'id': 'nonmatch_type_rule',
        'meta': {'name': 'Nonmatch Type Rule', 'description': '', 'risk': 'INFO', 'scope': 'scan'},
        'collections': [
            {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': 'IP_ADDRESS'}]}}
        ],
        'aggregation': {'field': 'data'},
        'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': 1}],
        'headline': 'Nonmatch type headline {data}',
    }
    executor = RuleExecutor(dbh, [rule], scan_ids=[scan_id])
    results = executor.run()
    assert 'nonmatch_type_rule' in results
    assert 'Nonmatch Type Rule' in results['nonmatch_type_rule']['meta']['name']
    assert results['nonmatch_type_rule']['matched'] is False

def test_empty_ruleset(dbh):
    dbh, scan_id = dbh
    rules = []
    executor = RuleExecutor(dbh, rules, scan_ids=[scan_id])
    results = executor.run()
    assert results == {}

def test_empty_events(dbh):
    dbh, scan_id = dbh
    # Remove all events from DB
    dbh.dbh.execute("DELETE FROM tbl_scan_results")
    dbh.conn.commit()
    rule = {
        'id': 'no_events_rule',
        'meta': {'name': 'No Events Rule', 'description': '', 'risk': 'INFO', 'scope': 'scan'},
        'collections': [
            {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': 'EMAILADDR'}]}}
        ],
        'aggregation': {'field': 'data'},
        'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': 1}],
        'headline': 'No events headline {data}',
    }
    executor = RuleExecutor(dbh, [rule], scan_ids=[scan_id])
    results = executor.run()
    assert 'no_events_rule' in results
    assert 'No Events Rule' in results['no_events_rule']['meta']['name']
    assert results['no_events_rule']['matched'] is False

def test_invalid_rule_format(dbh):
    dbh, scan_id = dbh
    # Rule missing required fields
    rule = {'id': 'invalid_rule'}
    executor = RuleExecutor(dbh, [rule], scan_ids=[scan_id])
    results = executor.run()
    # Should not include invalid_rule in results
    assert 'invalid_rule' not in results

def test_multiple_scans(dbh):
    dbh, scan_id = dbh
    # Add a second scan with a different event
    scan_id2 = 'integration_scan2'
    _ensure_scan_instance(dbh, scan_id2)
    _insert_event(dbh, scan_id2, 'EMAILADDR', 'integration2@example.com')
    dbh.conn.commit()
    rule = {
        'id': 'multi_scan_rule',
        'meta': {'name': 'Multi Scan Rule', 'description': '', 'risk': 'INFO', 'scope': 'scan'},
        'collections': [
            {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': 'EMAILADDR'}]}}
        ],
        'aggregation': {'field': 'data'},
        'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': 1}],
        'headline': 'Multi scan headline {data}',
    }
    executor = RuleExecutor(dbh, [rule], scan_ids=[scan_id, scan_id2])
    results = executor.run()
    assert 'multi_scan_rule' in results
    assert 'Multi Scan Rule' in results['multi_scan_rule']['meta']['name']
    assert results['multi_scan_rule']['matched'] is True

@pytest.mark.parametrize("event_type,threshold,should_match", [
    ("EMAILADDR", 1, True),
    ("EMAILADDR", 2, False),
    ("IP_ADDRESS", 1, False),
])
def test_parametrized_threshold_and_type(dbh, event_type, threshold, should_match):
    dbh, scan_id = dbh
    rule = {
        'id': 'param_rule',
        'meta': {'name': 'Param Rule', 'description': '', 'risk': 'INFO', 'scope': 'scan'},
        'collections': [
            {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': event_type}]}}
        ],
        'aggregation': {'field': 'data'},
        'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': threshold}],
        'headline': 'Param headline {data}',
    }
    executor = RuleExecutor(dbh, [rule], scan_ids=[scan_id])
    results = executor.run()
    assert 'param_rule' in results
    if should_match:
        assert 'Param Rule' in results['param_rule']['meta']['name']
        assert results['param_rule']['matched'] is True
    else:
        assert 'Param Rule' in results['param_rule']['meta']['name']
        assert results['param_rule']['matched'] is False
        # Could add more checks for non-match if engine supports

def test_cross_scan_correlation(dbh):
    dbh, scan_id = dbh
    scan_id2 = 'integration_scan2'
    _ensure_scan_instance(dbh, scan_id2)
    _insert_event(dbh, scan_id2, 'EMAILADDR', 'shared@example.com')
    _insert_event(dbh, scan_id, 'EMAILADDR', 'shared@example.com')
    dbh.conn.commit()
    rule = {
        'id': 'cross_scan_rule',
        'meta': {'name': 'Cross Scan Rule', 'description': '', 'risk': 'INFO', 'scope': 'workspace'},
        'collections': [
            {'condition': {'collect': [{'method': 'exact', 'field': 'type', 'value': 'EMAILADDR'}]}}
        ],
        'aggregation': {'field': 'data'},
        'analysis': [{'method': 'threshold', 'field': 'data', 'minimum': 2}],
        'headline': 'Cross scan headline {data}',
    }
    executor = RuleExecutor(dbh, [rule], scan_ids=[scan_id, scan_id2])
    results = executor.run()
    assert 'cross_scan_rule' in results
    assert 'Cross Scan Rule' in results['cross_scan_rule']['meta']['name']
    assert results['cross_scan_rule']['matched'] is True

def test_get_scan_events_uses_real_column_values(dbh):
    """
    Regression test for Item 2: _get_scan_events() must return the REAL
    module/generated/source_event_hash values from tbl_scan_results, not
    the hardcoded 'test_module'/0/'ROOT' literals the old schema-detection
    branch always substituted. Use values that deliberately differ from
    those literals so a regression can't hide behind a coincidental match.
    """
    from spiderfoot.correlation.rule_executor import DefaultRuleExecutionStrategy

    dbh, scan_id = dbh
    real_hash = _insert_event(
        dbh, scan_id, 'IP_ADDRESS', '203.0.113.5',
        module='sfp_dnsresolve', generated=1234567890, source_event_hash='deadbeef01'
    )
    dbh.conn.commit()

    strategy = DefaultRuleExecutionStrategy()
    collect_rules = [{'method': 'exact', 'field': 'type', 'value': 'IP_ADDRESS'}]
    events = strategy._get_scan_events(dbh, scan_id, collect_rules)

    matching = [e for e in events if e['hash'] == real_hash]
    assert len(matching) == 1, f"Expected exactly 1 event with hash {real_hash}, found {len(matching)}"
    event = matching[0]
    assert event['module'] == 'sfp_dnsresolve', f"module was overwritten: {event['module']}"
    assert event['created'] == 1234567890, f"created (generated) was overwritten: {event['created']}"
    assert event['source_event_hash'] == 'deadbeef01', f"source_event_hash was overwritten: {event['source_event_hash']}"

def test_rule_loader_yaml():
    from spiderfoot.correlation.rule_loader import RuleLoader
    yaml_str = '''
- id: yaml_rule
  meta:
    name: YAML Rule
    description: YAML loaded rule
    risk: INFO
    scope: scan
  collections:
  - id: yaml_rule_collection
    condition:
      collect:
        - method: exact
          field: type
          value: EMAILADDR
  aggregation:
    field: data
  analysis:
    - method: threshold
      field: data
      minimum: 1
  headline: YAML headline {data}
'''
    rules = yaml.safe_load(yaml_str)
    loader = RuleLoader(None)
    loader.rules = rules
    assert len(loader.rules) == 1
    assert loader.rules[0]['id'] == 'yaml_rule'
    assert loader.rules[0]['meta']['name'] == 'YAML Rule'
