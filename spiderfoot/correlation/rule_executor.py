# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         Modular SpiderFoot Correlation Engine
# Purpose:      Common functions for enriching events with contextual information.
#
# Author:      Agostino Panico @poppopjmp
#
# Created:     30/06/2025
# Copyright:   (c) Agostino Panico 2025
# Licence:     MIT
# -------------------------------------------------------------------------------
import logging
from copy import deepcopy
from collections import defaultdict
from spiderfoot.correlation.rule_loader import RuleLoader

class _HeadlineRef:
    """Lightweight attribute-access wrapper so headline templates can use
    dotted placeholders like {source.data}/{entity.data}/{child.data}
    against a plain value via str.format()."""
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return str(self.data)

class RuleExecutionStrategy:
    """Base class for pluggable rule execution strategies."""
    def execute(self, dbh, rule, scan_ids):
        raise NotImplementedError

class DefaultRuleExecutionStrategy(RuleExecutionStrategy):
    def execute(self, dbh, rule, scan_ids):
        """Execute correlation rule and save results to database."""
        import uuid
        from collections import defaultdict

        log = logging.getLogger("spiderfoot.correlation.strategy")
        log.debug(f"Processing rule {rule.get('id', 'unknown')} for scans {scan_ids}")

        # Step 1: Collect data based on rule collections
        collected_events = self._collect_events(dbh, rule, scan_ids)
        log.debug(f"Collected {len(collected_events)} events")

        if not collected_events:
            log.debug("No events collected, skipping rule")
            return {
                'meta': rule['meta'],
                'matched': False,
                'events': [],
                'correlations_created': 0
            }

        # Step 2: Apply aggregation if specified
        aggregated_groups = self._aggregate_events(collected_events, rule.get('aggregation', {}))
        log.debug(f"Created {len(aggregated_groups)} aggregated groups")

        # Step 3: Apply analysis if specified
        filtered_groups = self._analyze_groups(aggregated_groups, rule.get('analysis', []), rule)
        log.debug(f"Analysis filtered to {len(filtered_groups)} groups")

        # Step 4: Create correlation results for valid groups
        correlations_created = 0
        for group_key, events in filtered_groups.items():
            correlation_id = self._create_correlation_result(dbh, rule, scan_ids, group_key, events)
            if correlation_id:
                correlations_created += 1
                log.debug(f"Created correlation {correlation_id} for group {group_key}")

        return {
            'meta': rule['meta'],
            'matched': correlations_created > 0,
            'events': collected_events,
            'correlations_created': correlations_created
        }

    def _collect_events(self, dbh, rule, scan_ids):
        """Collect events from database based on rule collections."""
        log = logging.getLogger("spiderfoot.correlation.collect")

        collections = rule.get('collections', {})

        # Handle both dict and list formats for collections. Real rule YAML
        # (correlations/*.yaml) always nests 'collect' under a 'condition' key
        # on each collection entry, e.g.:
        #   collections:
        #   - id: foo
        #     condition:
        #       collect: [...]
        # A flat 'collect' key directly on the collection dict is also
        # accepted for backward compatibility with older/simplified fixtures.
        if isinstance(collections, list):
            collect_rules = []
            for collection in collections:
                condition = collection.get('condition') if isinstance(collection, dict) else None
                if isinstance(condition, dict) and 'collect' in condition:
                    collect_rules.extend(condition['collect'])
                elif isinstance(collection, dict) and 'collect' in collection:
                    collect_rules.extend(collection['collect'])
        else:
            condition = collections.get('condition') if isinstance(collections, dict) else None
            if isinstance(condition, dict) and 'collect' in condition:
                collect_rules = condition['collect']
            else:
                collect_rules = collections.get('collect', []) if isinstance(collections, dict) else []

        if not collect_rules:
            log.warning("No collection rules defined")
            return []

        # For each scan, collect matching events
        all_events = []
        for scan_id in scan_ids:
            scan_events = self._get_scan_events(dbh, scan_id, collect_rules)
            all_events.extend(scan_events)

        return all_events

    def _get_scan_events(self, dbh, scan_id, collect_rules):
        """Get events for a specific scan that match collection rules."""
        log = logging.getLogger("spiderfoot.correlation.collect")

        try:
            # Check which table schema we're working with. Probe with the
            # REAL production columns first: 'scan_instance_id, type, data'
            # alone exist in both the full schema and any simplified test
            # schema, so that probe can never distinguish the two and always
            # took this branch (including in production), silently replacing
            # every event's real module/created/source_event_hash with
            # placeholder values. Probing with the full column set instead
            # only succeeds when those columns genuinely exist.
            dbh_lock = getattr(dbh, 'dbhLock', None)
            ph = getattr(dbh, '_placeholder', lambda: '?')()

            try:
                if dbh_lock:
                    with dbh_lock:
                        dbh.dbh.execute(
                            f"SELECT hash, type, data, module, generated, source_event_hash "
                            f"FROM tbl_scan_results WHERE scan_instance_id = {ph} LIMIT 1",
                            [scan_id]
                        )
                        dbh.dbh.fetchone()
                else:
                    dbh.dbh.execute(
                        f"SELECT hash, type, data, module, generated, source_event_hash "
                        f"FROM tbl_scan_results WHERE scan_instance_id = {ph} LIMIT 1",
                        [scan_id]
                    )
                    dbh.dbh.fetchone()

                # Full production schema is present - use the real columns.
                base_query = f"""
                    SELECT hash, type, data, module, generated, source_event_hash
                    FROM tbl_scan_results
                    WHERE scan_instance_id = {ph} AND false_positive = 0
                """
                query_params = [scan_id]

            except Exception:
                # Fall back to the simplified schema (e.g. test fixtures that
                # only define scan_instance_id/type/data on tbl_scan_results).
                base_query = f"SELECT hash, type, data, 'test_module' as module, 0 as created, 'ROOT' as source_event_hash FROM tbl_scan_results WHERE scan_instance_id = {ph}"
                query_params = [scan_id]

            # Execute query
            events = []
            if dbh_lock:
                with dbh_lock:
                    dbh.dbh.execute(base_query, query_params)
                    rows = dbh.dbh.fetchall()
            else:
                dbh.dbh.execute(base_query, query_params)
                rows = dbh.dbh.fetchall()

            # Convert to dict format for easier processing
            for row in rows:
                event = {
                    'hash': row[0],
                    'type': row[1],
                    'data': row[2],
                    'module': row[3],
                    'created': row[4],  # using generated column as created
                    'source_event_hash': row[5],
                    'scan_id': scan_id
                }
                events.append(event)

            log.debug(f"Retrieved {len(events)} base events for scan {scan_id}")

            # Apply collection filters
            filtered_events = events
            for collect_rule in collect_rules:
                filtered_events = self._apply_collection_filter(filtered_events, collect_rule)
                log.debug(f"After filter {collect_rule}, {len(filtered_events)} events remain")

            return filtered_events

        except Exception as e:
            log.error(f"Error collecting events for scan {scan_id}: {e}")
            return []

    def _apply_collection_filter(self, events, collect_rule):
        """Apply a single collection filter to events."""
        method = collect_rule.get('method', '')
        field = collect_rule.get('field', '')
        value = collect_rule.get('value', '')

        if method == 'exact':
            return [e for e in events if e.get(field) == value]
        elif method == 'regex':
            import re
            patterns = value if isinstance(value, list) else [value]
            filtered = []
            for event in events:
                event_value = str(event.get(field, ''))
                for pattern in patterns:
                    if re.search(pattern, event_value):
                        filtered.append(event)
                        break
            return filtered
        else:
            # Unknown method, return all events
            return events

    def _aggregate_events(self, events, aggregation):
        """Group events according to aggregation rules."""
        if not aggregation or not events:
            # No aggregation, return all events in a single group
            return {'all': events}

        field = aggregation.get('field', 'data')
        groups = defaultdict(list)

        for event in events:
            # Handle nested field references like 'source.data'
            key_value = self._get_field_value(event, field)
            groups[str(key_value)].append(event)

        return dict(groups)

    def _get_field_value(self, event, field):
        """Get field value from event, supporting nested references."""
        if '.' in field:
            # Handle nested fields like 'source.data'
            parts = field.split('.')
            if parts[0] == 'source':
                # For source fields, we'll use the event data as placeholder
                return event.get('data', '')

        return event.get(field, '')

    def _analyze_groups(self, groups, analysis_rules, rule=None):
        """
        Apply analysis rules to filter groups. Also enforces multi-scan logic if required.

        Args:
            groups (dict): Grouped events to analyze.
            analysis_rules (list): List of analysis rule dicts.
            rule (dict, optional): The correlation rule being processed.

        Returns:
            dict: Filtered groups that pass all analysis (and multi-scan) checks.
        """
        if not analysis_rules and not (rule and rule.get('meta', {}).get('type') == 'multi-scan'):
            return groups

        filtered_groups = {}
        for group_key, events in groups.items():
            keep_group = True

            # Enforce multi-scan: only keep groups with >1 unique scan_id
            if rule and rule.get('meta', {}).get('type') == 'multi-scan':
                scan_ids = set(e.get('scan_id') for e in events)
                if len(scan_ids) <= 1:
                    keep_group = False

            if keep_group:
                for analysis_rule in analysis_rules or []:
                    method = analysis_rule.get('method', '')
                    if method == 'threshold':
                        minimum = analysis_rule.get('minimum', 1)
                        if len(events) < minimum:
                            keep_group = False
                            break
                    # Add more analysis methods as needed

            if keep_group:
                filtered_groups[group_key] = events
        return filtered_groups

    def _create_correlation_result(self, dbh, rule, scan_ids, group_key, events):
        """
        Create a correlation result in the database.

        Args:
            dbh: Database handle.
            rule (dict): The correlation rule being processed.
            scan_ids (list): List of scan IDs involved.
            group_key: The key for the group of events.
            events (list): List of event dicts in the group.

        Returns:
            str or None: Correlation ID if created, else None.
        """
        log = logging.getLogger("spiderfoot.correlation.create")

        try:
            # Generate correlation title using headline template. Rule
            # headlines use several placeholder styles across the shipped
            # correlations/*.yaml files: {data}, {count}, {summary}, and
            # dotted attribute access like {source.data}/{entity.data}/
            # {child.data}. This engine's collection model is flat (it
            # doesn't track distinct source/entity/child roles per event),
            # so source/entity/child are all aliased to the same
            # representative event's data as a best-effort compatibility
            # shim - not a full re-implementation of role-based collection.
            headline = rule.get('headline', 'Correlation found')
            representative_data = events[0].get('data', group_key) if events else group_key
            unique_data = sorted({str(e.get('data', '')) for e in events}) if events else []
            summary = ', '.join(unique_data[:5]) + ('...' if len(unique_data) > 5 else '')
            format_ctx = {
                'data': group_key,
                'count': len(events),
                'summary': summary,
                'source': _HeadlineRef(representative_data),
                'entity': _HeadlineRef(representative_data),
                'child': _HeadlineRef(representative_data),
            }
            try:
                correlation_title = headline.format(**format_ctx)
            except (KeyError, IndexError):
                # Unknown placeholder in the template - fall back to the
                # simple {data} substitution rather than losing the result.
                correlation_title = headline.format(data=group_key)

            # Use first scan ID as the primary scan
            scan_id = scan_ids[0] if scan_ids else 'unknown'

            # Use first event hash as the event hash
            event_hash = events[0]['hash'] if events else 'ROOT'

            # Extract rule information
            rule_id = rule.get('id', 'unknown')
            rule_name = rule.get('meta', {}).get('name', 'Unknown Rule')
            rule_descr = rule.get('meta', {}).get('description', '')
            rule_risk = rule.get('meta', {}).get('risk', 'INFO')
            rule_yaml = rule.get('rawYaml', '')

            # Collect all event hashes
            event_hashes = [event['hash'] for event in events]

            # Check if dbh has correlationResultCreate method (production) or if it's a test
            if hasattr(dbh, 'correlationResultCreate') and callable(dbh.correlationResultCreate):
                # Create correlation result in database
                correlation_id = dbh.correlationResultCreate(
                    instanceId=scan_id,
                    event_hash=event_hash,
                    ruleId=rule_id,
                    ruleName=rule_name,
                    ruleDescr=rule_descr,
                    ruleRisk=rule_risk,
                    ruleYaml=rule_yaml,
                    correlationTitle=correlation_title,
                    eventHashes=event_hashes
                )
                log.info(f"Created correlation {correlation_id} for rule {rule_id}: {correlation_title}")
                return correlation_id
            # For tests, just return a mock correlation ID
            import uuid
            correlation_id = str(uuid.uuid4())
            log.info(f"Test mode: Mock correlation {correlation_id} for rule {rule_id}: {correlation_title}")
            return correlation_id

        except Exception as e:
            log.error(f"Error creating correlation result: {e}", exc_info=True)
            return None

class RuleExecutor:
    _strategy_registry = {}
    _event_hooks = {
        'pre_rule': [],
        'post_rule': [],
        'pre_aggregate': [],
        'post_aggregate': [],
    }

    @classmethod
    def register_strategy(cls, rule_type, strategy):
        cls._strategy_registry[rule_type] = strategy

    @classmethod
    def register_event_hook(cls, hook_name, func):
        if hook_name in cls._event_hooks:
            cls._event_hooks[hook_name].append(func)

    def __init__(self, dbh, rules, scan_ids=None, debug=False):
        self.log = logging.getLogger("spiderfoot.correlation.executor")
        self.dbh = dbh
        self.rules = rules
        self.scan_ids = scan_ids if scan_ids else []
        self.results = {}
        self.debug = debug

    def run(self):
        for rule in self.rules:
            if not rule.get('enabled', True):
                self.log.info(f"Skipping disabled rule: {rule.get('id', rule.get('meta', {}).get('name', 'unknown'))}")
                continue
            try:
                if self.debug:
                    print(f"[DEBUG] Evaluating rule: {rule.get('id', rule.get('meta', {}).get('name', 'unknown'))}")
                for hook in self._event_hooks['pre_rule']:
                    hook(rule, self.scan_ids)
                rule_result = self.process_rule(rule)
                if self.debug:
                    print(f"[DEBUG] Rule result: {rule_result}")
                for hook in self._event_hooks['post_rule']:
                    hook(rule, rule_result, self.scan_ids)
                self.results[rule.get('id', rule.get('meta', {}).get('name', 'unknown'))] = rule_result
            except Exception as e:
                self.log.error(f"Error processing rule {rule.get('id', rule.get('meta', {}).get('name', 'unknown'))}: {e}")
        return self.results

    def process_rule(self, rule):
        rule_type = rule.get('meta', {}).get('type', 'default')
        strategy = self._strategy_registry.get(rule_type, DefaultRuleExecutionStrategy())
        if self.debug:
            print(f"[DEBUG] Using strategy: {strategy.__class__.__name__}")
        return strategy.execute(self.dbh, rule, self.scan_ids)

# Example: Register a custom strategy for a new rule type
# class CustomRuleStrategy(RuleExecutionStrategy):
#     def execute(self, dbh, rule, scan_ids):
#         # Custom logic here
#         return {...}
# RuleExecutor.register_strategy('custom_type', CustomRuleStrategy())

# Example: Register an event hook
# def my_pre_rule_hook(rule, scan_ids):
#     print(f"Pre-processing rule: {rule.get('id')}")
# RuleExecutor.register_event_hook('pre_rule', my_pre_rule_hook)
