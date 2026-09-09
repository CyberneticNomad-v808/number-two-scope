# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         test_correlation_schema_validation
# Purpose:      Regression test to ensure all correlation YAML files validate
#               against the schema definition.
#
# Author:      Regression Test Suite
#
# Created:     2025-12-20
# Copyright:   (c) SpiderFoot 2025
# Licence:     MIT
# -------------------------------------------------------------------------------
"""
Regression test for correlation rule schema validation.

This test ensures that all correlation YAML rule files in the correlations/
directory successfully validate against the RULE_SCHEMA defined in
spiderfoot/correlation/schema.py and rule_loader.py.

Bug History:
- Commit 447e15f7: Changed schema to expect arrays, converted YAML files
- Commit 3d4ebc85: Reverted schema to object type but forgot to revert YAML files
- Result: 51/53 correlation rules failed validation at startup

This test prevents that bug from recurring by validating all YAML files
against the schema in the test suite.
"""

import unittest
import os
from unittest.mock import MagicMock, patch
from spiderfoot.correlation.rule_loader import RuleLoader
from spiderfoot.correlation.rule_executor import DefaultRuleExecutionStrategy


class TestCorrelationSchemaValidation(unittest.TestCase):
    """Regression tests for correlation rule schema validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.correlations_dir = 'correlations/'
        self.expected_min_rules = 50  # Expect at least 50 correlation rules

    def test_all_correlation_rules_validate(self):
        """
        Test that all correlation YAML files validate against the schema.

        This is a regression test for the schema/YAML mismatch bug where
        the schema definition was changed without updating the YAML files,
        causing 51 validation errors at startup.
        """
        # Load all correlation rules from the correlations/ directory
        loader = RuleLoader(self.correlations_dir)
        loader.load_rules()

        # Assert no validation errors occurred
        self.assertEqual(
            len(loader.errors), 0,
            f"Schema validation failed for {len(loader.errors)} correlation rules:\n" +
            "\n".join([f"  {fname}: {err}" for fname, err in loader.errors])
        )

        # Assert we loaded a reasonable number of rules
        self.assertGreaterEqual(
            len(loader.rules), self.expected_min_rules,
            f"Expected at least {self.expected_min_rules} correlation rules, "
            f"but only loaded {len(loader.rules)}"
        )

    def test_correlation_directory_exists(self):
        """Test that the correlations directory exists."""
        self.assertTrue(
            os.path.isdir(self.correlations_dir),
            f"Correlations directory not found: {self.correlations_dir}"
        )

    def test_correlation_directory_has_yaml_files(self):
        """Test that the correlations directory contains YAML files."""
        yaml_files = [
            f for f in os.listdir(self.correlations_dir)
            if f.endswith('.yaml') or f.endswith('.yml')
        ]
        self.assertGreater(
            len(yaml_files), 0,
            f"No YAML files found in {self.correlations_dir}"
        )

    def test_each_correlation_rule_has_required_fields(self):
        """
        Test that each loaded correlation rule has the required fields.

        Required fields (from RULE_SCHEMA):
        - meta (with name, description, risk)
        - collections
        - headline
        """
        loader = RuleLoader(self.correlations_dir)
        loader.load_rules()

        # Skip this test if there were loading errors (handled by other test)
        if loader.errors:
            self.skipTest("Skipping due to loading errors in other test")

        for rule in loader.rules:
            # Check required top-level fields
            self.assertIn('meta', rule, f"Rule {rule.get('id')} missing 'meta' field")
            self.assertIn('collections', rule, f"Rule {rule.get('id')} missing 'collections' field")
            self.assertIn('headline', rule, f"Rule {rule.get('id')} missing 'headline' field")

            # Check required meta fields
            meta = rule['meta']
            self.assertIn('name', meta, f"Rule {rule.get('id')} missing 'meta.name'")
            self.assertIn('description', meta, f"Rule {rule.get('id')} missing 'meta.description'")
            self.assertIn('risk', meta, f"Rule {rule.get('id')} missing 'meta.risk'")

    def test_all_rules_produce_nonempty_collect_rules(self):
        """
        Regression test for the Item-1 bug: DefaultRuleExecutionStrategy
        ._collect_events() must actually extract a non-empty 'collect' list
        from every REAL on-disk rule's collections, not just from synthetic
        test fixtures. Every real rule nests 'collect' under
        collections[i]['condition']['collect'] -- if the extraction logic
        regresses to only checking collections[i]['collect'] directly, this
        test must fail.

        We can't observe the private 'collect_rules' list directly, so we
        spy on _apply_collection_filter: it is only ever invoked (once per
        collect rule, inside _get_scan_events) when collect_rules is
        non-empty. Zero calls means the rule's collections were parsed into
        an empty list, i.e. this bug has recurred.
        """
        loader = RuleLoader(self.correlations_dir)
        loader.load_rules()

        if loader.errors:
            self.skipTest("Skipping due to loading errors in other test")

        strategy = DefaultRuleExecutionStrategy()

        # Minimal mock DB handle: one dummy row shaped like a real
        # tbl_scan_results row, so _get_scan_events' query succeeds and
        # reaches the "apply collection filters" loop.
        dummy_row = ('dummyhash', 'DUMMY_EVENT_TYPE', 'dummydata', 'test_module', 0, 'ROOT')

        # These 2 rules use an entirely different, unimplemented rule schema
        # (condition: {event_type, data_contains} + multi-collection/key
        # aggregation) rather than the standard condition.collect list -- see
        # refactor plan Item 6. Tracked separately; not a Item-1 regression.
        KNOWN_UNSUPPORTED_SCHEMA_RULES = {
            'tiktok_user_correlation',
            'blockchain_risk_aggregation',
        }

        broken_rules = []
        for rule in loader.rules:
            if rule.get('id') in KNOWN_UNSUPPORTED_SCHEMA_RULES:
                continue
            mock_dbh = MagicMock()
            mock_dbh.dbhLock = None
            mock_dbh._placeholder = lambda: '%s'
            mock_dbh.dbh.fetchall.return_value = [dummy_row]

            with patch.object(
                DefaultRuleExecutionStrategy, '_apply_collection_filter',
                wraps=strategy._apply_collection_filter
            ) as spy:
                strategy._collect_events(mock_dbh, rule, ['dummy_scan'])
                if spy.call_count == 0:
                    broken_rules.append(rule.get('id', rule.get('filename', 'unknown')))

        self.assertEqual(
            broken_rules, [],
            f"{len(broken_rules)} rule(s) produced an empty collect_rules list "
            f"(correlation can never match for these): {broken_rules}"
        )

    def test_collections_field_is_array(self):
        """
        Test that the collections field in all rules is an array.

        This is a specific regression test for the bug where the schema
        expected an object but the YAML files provided arrays.
        """
        loader = RuleLoader(self.correlations_dir)
        loader.load_rules()

        # Skip this test if there were loading errors
        if loader.errors:
            self.skipTest("Skipping due to loading errors in other test")

        for rule in loader.rules:
            collections = rule.get('collections')
            self.assertIsInstance(
                collections, list,
                f"Rule {rule.get('id')} has collections of type {type(collections).__name__}, "
                f"expected list/array"
            )


if __name__ == '__main__':
    unittest.main()
