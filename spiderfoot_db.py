# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         sfdb
# Purpose:      Common functions for working with the database back-end.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     15/05/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     MIT
# -------------------------------------------------------------------------------

from pathlib import Path
import hashlib
import random
import re
import threading
import time

# Import psycopg2 conditionally
try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    psycopg2 = None


class SpiderFootDb:
    """SpiderFoot database.

    Attributes:
        conn: Database connection
        dbh: Database cursor
        dbhLock (_thread.RLock): thread lock on database handle
    """

    dbh = None
    conn = None

    # Prevent multithread access to database
    dbhLock = threading.RLock()

    def _placeholder(self, count=1):
        """Return appropriate SQL placeholder(s) for current database type.

        Args:
            count: Number of placeholders needed

        Returns:
            String with placeholders (? for SQLite, %s for PostgreSQL)
        """
        if self.db_type == 'sqlite':
            return ', '.join(['?'] * count) if count > 1 else '?'
        else:  # postgresql
            return ', '.join(['%s'] * count) if count > 1 else '%s'

    # Queries for creating the SpiderFoot database
    createSchemaQueries = [
        # "PRAGMA journal_mode=WAL",  # SQLite only - disabled for PostgreSQL compatibility
        "CREATE TABLE tbl_event_types ( \
            event       VARCHAR NOT NULL PRIMARY KEY, \
            event_descr VARCHAR NOT NULL, \
            event_raw   INT NOT NULL DEFAULT 0, \
            event_type  VARCHAR NOT NULL \
        )",
        "CREATE TABLE tbl_config ( \
            scope   VARCHAR NOT NULL, \
            opt     VARCHAR NOT NULL, \
            val     VARCHAR NOT NULL, \
            PRIMARY KEY (scope, opt) \
        )",
        "CREATE TABLE tbl_scan_instance ( \
            guid        VARCHAR NOT NULL PRIMARY KEY, \
            name        VARCHAR NOT NULL, \
            seed_target VARCHAR NOT NULL, \
            created     INT DEFAULT 0, \
            started     INT DEFAULT 0, \
            ended       INT DEFAULT 0, \
            status      VARCHAR NOT NULL \
        )",
        "CREATE TABLE tbl_scan_log ( \
            scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid) ON DELETE CASCADE, \
            generated           INT NOT NULL, \
            component           VARCHAR, \
            type                VARCHAR NOT NULL, \
            message             VARCHAR \
        )",
        "CREATE TABLE tbl_scan_config ( \
            scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid) ON DELETE CASCADE, \
            component           VARCHAR NOT NULL, \
            opt                 VARCHAR NOT NULL, \
            val                 VARCHAR NOT NULL, \
            UNIQUE (scan_instance_id, component, opt) \
        )",
        "CREATE TABLE tbl_scan_results ( \
            scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid) ON DELETE CASCADE, \
            hash                VARCHAR NOT NULL, \
            type                VARCHAR NOT NULL REFERENCES tbl_event_types(event) DEFERRABLE INITIALLY DEFERRED, \
            generated           INT NOT NULL, \
            confidence          INT NOT NULL DEFAULT 100, \
            visibility          INT NOT NULL DEFAULT 100, \
            risk                INT NOT NULL DEFAULT 0, \
            module              VARCHAR NOT NULL, \
            data                VARCHAR, \
            false_positive      INT NOT NULL DEFAULT 0, \
            source_event_hash  VARCHAR DEFAULT 'ROOT' \
        )",
        "CREATE TABLE tbl_scan_correlation_results ( \
            id                  VARCHAR NOT NULL PRIMARY KEY, \
            scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid) ON DELETE CASCADE, \
            title               VARCHAR NOT NULL, \
            rule_risk           VARCHAR NOT NULL, \
            rule_id             VARCHAR NOT NULL, \
            rule_name           VARCHAR NOT NULL, \
            rule_descr          VARCHAR NOT NULL, \
            rule_logic          VARCHAR NOT NULL \
        )",
        "CREATE TABLE tbl_scan_correlation_results_events ( \
            correlation_id      VARCHAR NOT NULL REFERENCES tbl_scan_correlation_results(id) ON DELETE CASCADE, \
            event_hash          VARCHAR NOT NULL REFERENCES tbl_scan_results(hash) ON DELETE CASCADE \
        )",
        "CREATE INDEX idx_scan_results_id ON tbl_scan_results (scan_instance_id)",
        "CREATE INDEX idx_scan_results_type ON tbl_scan_results (scan_instance_id, type)",
        "CREATE INDEX idx_scan_results_hash ON tbl_scan_results (scan_instance_id, hash)",
        "CREATE INDEX idx_scan_results_module ON tbl_scan_results(scan_instance_id, module)",
        "CREATE INDEX idx_scan_results_srchash ON tbl_scan_results (scan_instance_id, source_event_hash)",
        "CREATE INDEX idx_scan_logs ON tbl_scan_log (scan_instance_id)",
        "CREATE INDEX idx_scan_log_generated ON tbl_scan_log (scan_instance_id, generated DESC)",
        "CREATE INDEX idx_scan_correlation ON tbl_scan_correlation_results (scan_instance_id, id)",
        "CREATE INDEX idx_scan_correlation_title ON tbl_scan_correlation_results (scan_instance_id, title)",
        "CREATE INDEX idx_scan_correlation_events ON tbl_scan_correlation_results_events (correlation_id)",
        "CREATE INDEX idx_scan_results_generated ON tbl_scan_results (scan_instance_id, generated DESC)"
    ]

    # PostgreSQL-specific schema queries
    createPostgreSQLSchemaQueries = [
        "CREATE TABLE IF NOT EXISTS tbl_event_types ( \
            event       VARCHAR NOT NULL PRIMARY KEY, \
            event_descr VARCHAR NOT NULL, \
            event_raw   INT NOT NULL DEFAULT 0, \
            event_type  VARCHAR NOT NULL \
        )",
        "CREATE TABLE IF NOT EXISTS tbl_config ( \
            scope   VARCHAR NOT NULL, \
            opt     VARCHAR NOT NULL, \
            val     VARCHAR NOT NULL, \
            PRIMARY KEY (scope, opt) \
        )",
        "CREATE TABLE IF NOT EXISTS tbl_scan_instance ( \
            guid        VARCHAR NOT NULL PRIMARY KEY, \
            name        VARCHAR NOT NULL, \
            seed_target VARCHAR NOT NULL, \
            created     BIGINT DEFAULT 0, \
            started     BIGINT DEFAULT 0, \
            ended       BIGINT DEFAULT 0, \
            status      VARCHAR NOT NULL \
        )",
        "CREATE TABLE IF NOT EXISTS tbl_scan_log ( \
            scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid) ON DELETE CASCADE, \
            generated           BIGINT NOT NULL, \
            component           VARCHAR, \
            type                VARCHAR NOT NULL, \
            message             VARCHAR \
        )",
        "CREATE TABLE IF NOT EXISTS tbl_scan_config ( \
            scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid) ON DELETE CASCADE, \
            component           VARCHAR NOT NULL, \
            opt                 VARCHAR NOT NULL, \
            val                 VARCHAR NOT NULL, \
            UNIQUE (scan_instance_id, component, opt) \
        )",
        "CREATE TABLE IF NOT EXISTS tbl_scan_results ( \
            scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid) ON DELETE CASCADE, \
            hash                VARCHAR NOT NULL UNIQUE, \
            type                VARCHAR NOT NULL REFERENCES tbl_event_types(event) DEFERRABLE INITIALLY DEFERRED, \
            generated           BIGINT NOT NULL, \
            confidence          INT NOT NULL DEFAULT 100, \
            visibility          INT NOT NULL DEFAULT 100, \
            risk                INT NOT NULL DEFAULT 0, \
            module              VARCHAR NOT NULL, \
            data                TEXT, \
            false_positive      INT NOT NULL DEFAULT 0, \
            source_event_hash  VARCHAR DEFAULT 'ROOT' \
        )",
        "CREATE TABLE IF NOT EXISTS tbl_scan_correlation_results ( \
            id                  VARCHAR NOT NULL PRIMARY KEY, \
            scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid) ON DELETE CASCADE, \
            title               VARCHAR NOT NULL, \
            rule_risk           VARCHAR NOT NULL, \
            rule_id             VARCHAR NOT NULL, \
            rule_name           VARCHAR NOT NULL, \
            rule_descr          VARCHAR NOT NULL, \
            rule_logic          VARCHAR NOT NULL \
        )",
        "CREATE TABLE IF NOT EXISTS tbl_scan_correlation_results_events ( \
            correlation_id      VARCHAR NOT NULL REFERENCES tbl_scan_correlation_results(id) ON DELETE CASCADE, \
            event_hash          VARCHAR NOT NULL REFERENCES tbl_scan_results(hash) ON DELETE CASCADE \
        )",
        "CREATE INDEX IF NOT EXISTS idx_scan_results_id ON tbl_scan_results (scan_instance_id)",
        "CREATE INDEX IF NOT EXISTS idx_scan_results_type ON tbl_scan_results (scan_instance_id, type)",
        "CREATE INDEX IF NOT EXISTS idx_scan_results_hash ON tbl_scan_results (scan_instance_id, hash)",
        "CREATE INDEX IF NOT EXISTS idx_scan_results_module ON tbl_scan_results(scan_instance_id, module)",
        "CREATE INDEX IF NOT EXISTS idx_scan_results_srchash ON tbl_scan_results (scan_instance_id, source_event_hash)",
        "CREATE INDEX IF NOT EXISTS idx_scan_logs ON tbl_scan_log (scan_instance_id)",
        "CREATE INDEX IF NOT EXISTS idx_scan_log_generated ON tbl_scan_log (scan_instance_id, generated DESC)",
        "CREATE INDEX IF NOT EXISTS idx_scan_correlation ON tbl_scan_correlation_results (scan_instance_id, id)",
        "CREATE INDEX IF NOT EXISTS idx_scan_correlation_title ON tbl_scan_correlation_results (scan_instance_id, title)",
        "CREATE INDEX IF NOT EXISTS idx_scan_correlation_events ON tbl_scan_correlation_results_events (correlation_id)",
        "CREATE INDEX IF NOT EXISTS idx_scan_results_generated ON tbl_scan_results (scan_instance_id, generated DESC)"
    ]

    eventDetails = [
        ['ROOT', 'Internal SpiderFoot Root event', 1, 'INTERNAL'],
        ['ACCOUNT_EXTERNAL_OWNED', 'Account on External Site', 0, 'ENTITY'],
        ['ACCOUNT_EXTERNAL_OWNED_COMPROMISED',
            'Hacked Account on External Site', 0, 'DESCRIPTOR'],
        ['ACCOUNT_EXTERNAL_USER_SHARED_COMPROMISED',
            'Hacked User Account on External Site', 0, 'DESCRIPTOR'],
        ['AFFILIATE_EMAILADDR', 'Affiliate - Email Address', 0, 'ENTITY'],
        ['AFFILIATE_INTERNET_NAME', 'Affiliate - Internet Name', 0, 'ENTITY'],
        ['AFFILIATE_INTERNET_NAME_HIJACKABLE',
            'Affiliate - Internet Name Hijackable', 0, 'ENTITY'],
        ['AFFILIATE_INTERNET_NAME_UNRESOLVED',
            'Affiliate - Internet Name - Unresolved', 0, 'ENTITY'],
        ['AFFILIATE_IPADDR', 'Affiliate - IP Address', 0, 'ENTITY'],
        ['AFFILIATE_IPV6_ADDRESS', 'Affiliate - IPv6 Address', 0, 'ENTITY'],
        ['AFFILIATE_WEB_CONTENT', 'Affiliate - Web Content', 1, 'DATA'],
        ['AFFILIATE_DOMAIN_NAME', 'Affiliate - Domain Name', 0, 'ENTITY'],
        ['AFFILIATE_DOMAIN_UNREGISTERED',
            'Affiliate - Domain Name Unregistered', 0, 'ENTITY'],
        ['AFFILIATE_COMPANY_NAME', 'Affiliate - Company Name', 0, 'ENTITY'],
        ['AFFILIATE_DOMAIN_WHOIS', 'Affiliate - Domain Whois', 1, 'DATA'],
        ['AFFILIATE_DESCRIPTION_CATEGORY',
            'Affiliate Description - Category', 0, 'DESCRIPTOR'],
        ['AFFILIATE_DESCRIPTION_ABSTRACT',
            'Affiliate Description - Abstract', 0, 'DESCRIPTOR'],
        ['APPSTORE_ENTRY', 'App Store Entry', 0, 'ENTITY'],
        ['CLOUD_STORAGE_BUCKET', 'Cloud Storage Bucket', 0, 'ENTITY'],
        ['CLOUD_STORAGE_BUCKET_OPEN', 'Cloud Storage Bucket Open', 0, 'DESCRIPTOR'],
        ['COMPANY_NAME', 'Company Name', 0, 'ENTITY'],
        ['CREDIT_CARD_NUMBER', 'Credit Card Number', 0, 'ENTITY'],
        ['BASE64_DATA', 'Base64-encoded Data', 1, 'DATA'],
        ['BITCOIN_ADDRESS', 'Bitcoin Address', 0, 'ENTITY'],
        ['BITCOIN_BALANCE', 'Bitcoin Balance', 0, 'DESCRIPTOR'],
        ['BGP_AS_OWNER', 'BGP AS Ownership', 0, 'ENTITY'],
        ['BGP_AS_MEMBER', 'BGP AS Membership', 0, 'ENTITY'],
        ['BLACKLISTED_COHOST', 'Blacklisted Co-Hosted Site', 0, 'DESCRIPTOR'],
        ['BLACKLISTED_INTERNET_NAME', 'Blacklisted Internet Name', 0, 'DESCRIPTOR'],
        ['BLACKLISTED_AFFILIATE_INTERNET_NAME',
            'Blacklisted Affiliate Internet Name', 0, 'DESCRIPTOR'],
        ['BLACKLISTED_IPADDR', 'Blacklisted IP Address', 0, 'DESCRIPTOR'],
        ['BLACKLISTED_AFFILIATE_IPADDR',
            'Blacklisted Affiliate IP Address', 0, 'DESCRIPTOR'],
        ['BLACKLISTED_SUBNET', 'Blacklisted IP on Same Subnet', 0, 'DESCRIPTOR'],
        ['BLACKLISTED_NETBLOCK', 'Blacklisted IP on Owned Netblock', 0, 'DESCRIPTOR'],
        ['COUNTRY_NAME', 'Country Name', 0, 'ENTITY'],
        ['CO_HOSTED_SITE', 'Co-Hosted Site', 0, 'ENTITY'],
        ['CO_HOSTED_SITE_DOMAIN', 'Co-Hosted Site - Domain Name', 0, 'ENTITY'],
        ['CO_HOSTED_SITE_DOMAIN_WHOIS', 'Co-Hosted Site - Domain Whois', 1, 'DATA'],
        ['DARKNET_MENTION_URL', 'Darknet Mention URL', 0, 'DESCRIPTOR'],
        ['DARKNET_MENTION_CONTENT', 'Darknet Mention Web Content', 1, 'DATA'],
        ['DATE_HUMAN_DOB', 'Date of Birth', 0, 'ENTITY'],
        ['DEFACED_INTERNET_NAME', 'Defaced', 0, 'DESCRIPTOR'],
        ['DEFACED_IPADDR', 'Defaced IP Address', 0, 'DESCRIPTOR'],
        ['DEFACED_AFFILIATE_INTERNET_NAME', 'Defaced Affiliate', 0, 'DESCRIPTOR'],
        ['DEFACED_COHOST', 'Defaced Co-Hosted Site', 0, 'DESCRIPTOR'],
        ['DEFACED_AFFILIATE_IPADDR', 'Defaced Affiliate IP Address', 0, 'DESCRIPTOR'],
        ['DESCRIPTION_CATEGORY', 'Description - Category', 0, 'DESCRIPTOR'],
        ['DESCRIPTION_ABSTRACT', 'Description - Abstract', 0, 'DESCRIPTOR'],
        ['DEVICE_TYPE', 'Device Type', 0, 'DESCRIPTOR'],
        ['DNS_TEXT', 'DNS TXT Record', 0, 'DATA'],
        ['DNS_SRV', 'DNS SRV Record', 0, 'DATA'],
        ['DNS_SPF', 'DNS SPF Record', 0, 'DATA'],
        ['DOMAIN_NAME', 'Domain Name', 0, 'ENTITY'],
        ['DOMAIN_NAME_PARENT', 'Domain Name (Parent)', 0, 'ENTITY'],
        ['DOMAIN_REGISTRAR', 'Domain Registrar', 0, 'ENTITY'],
        ['DOMAIN_WHOIS', 'Domain Whois', 1, 'DATA'],
        ['EMAILADDR', 'Email Address', 0, 'ENTITY'],
        ['EMAILADDR_COMPROMISED', 'Hacked Email Address', 0, 'DESCRIPTOR'],
        ['EMAILADDR_DELIVERABLE', 'Deliverable Email Address', 0, 'DESCRIPTOR'],
        ['EMAILADDR_DISPOSABLE', 'Disposable Email Address', 0, 'DESCRIPTOR'],
        ['EMAILADDR_GENERIC', 'Email Address - Generic', 0, 'ENTITY'],
        ['EMAILADDR_UNDELIVERABLE', 'Undeliverable Email Address', 0, 'DESCRIPTOR'],
        ['ERROR_MESSAGE', 'Error Message', 0, 'DATA'],
        ['ETHEREUM_ADDRESS', 'Ethereum Address', 0, 'ENTITY'],
        ['ETHEREUM_BALANCE', 'Ethereum Balance', 0, 'DESCRIPTOR'],
        ['GEOINFO', 'Physical Location', 0, 'DESCRIPTOR'],
        ['HASH', 'Hash', 0, 'DATA'],
        ['HASH_COMPROMISED', 'Compromised Password Hash', 0, 'DATA'],
        ['HTTP_CODE', 'HTTP Status Code', 0, 'DATA'],
        ['HUMAN_NAME', 'Human Name', 0, 'ENTITY'],
        ['IBAN_NUMBER', 'IBAN Number', 0, 'ENTITY'],
        ['INTERESTING_FILE', 'Interesting File', 0, 'DESCRIPTOR'],
        ['INTERESTING_FILE_HISTORIC', 'Historic Interesting File', 0, 'DESCRIPTOR'],
        ['JUNK_FILE', 'Junk File', 0, 'DESCRIPTOR'],
        ['INTERNAL_IP_ADDRESS', 'IP Address - Internal Network', 0, 'ENTITY'],
        ['INTERNET_NAME', 'Internet Name', 0, 'ENTITY'],
        ['INTERNET_NAME_UNRESOLVED', 'Internet Name - Unresolved', 0, 'ENTITY'],
        ['IP_ADDRESS', 'IP Address', 0, 'ENTITY'],
        ['IPV6_ADDRESS', 'IPv6 Address', 0, 'ENTITY'],
        ['LEI', 'Legal Entity Identifier', 0, 'ENTITY'],
        ['JOB_TITLE', 'Job Title', 0, 'DESCRIPTOR'],
        ['LINKED_URL_INTERNAL', 'Linked URL - Internal', 0, 'SUBENTITY'],
        ['LINKED_URL_EXTERNAL', 'Linked URL - External', 0, 'SUBENTITY'],
        ['MALICIOUS_ASN', 'Malicious AS', 0, 'DESCRIPTOR'],
        ['MALICIOUS_BITCOIN_ADDRESS', 'Malicious Bitcoin Address', 0, 'DESCRIPTOR'],
        ['MALICIOUS_IPADDR', 'Malicious IP Address', 0, 'DESCRIPTOR'],
        ['MALICIOUS_COHOST', 'Malicious Co-Hosted Site', 0, 'DESCRIPTOR'],
        ['MALICIOUS_EMAILADDR', 'Malicious E-mail Address', 0, 'DESCRIPTOR'],
        ['MALICIOUS_INTERNET_NAME', 'Malicious Internet Name', 0, 'DESCRIPTOR'],
        ['MALICIOUS_AFFILIATE_INTERNET_NAME',
            'Malicious Affiliate', 0, 'DESCRIPTOR'],
        ['MALICIOUS_AFFILIATE_IPADDR',
            'Malicious Affiliate IP Address', 0, 'DESCRIPTOR'],
        ['MALICIOUS_NETBLOCK', 'Malicious IP on Owned Netblock', 0, 'DESCRIPTOR'],
        ['MALICIOUS_PHONE_NUMBER', 'Malicious Phone Number', 0, 'DESCRIPTOR'],
        ['MALICIOUS_SUBNET', 'Malicious IP on Same Subnet', 0, 'DESCRIPTOR'],
        ['NETBLOCK_OWNER', 'Netblock Ownership', 0, 'ENTITY'],
        ['NETBLOCKV6_OWNER', 'Netblock IPv6 Ownership', 0, 'ENTITY'],
        ['NETBLOCK_MEMBER', 'Netblock Membership', 0, 'ENTITY'],
        ['NETBLOCKV6_MEMBER', 'Netblock IPv6 Membership', 0, 'ENTITY'],
        ['NETBLOCK_WHOIS', 'Netblock Whois', 1, 'DATA'],
        ['OPERATING_SYSTEM', 'Operating System', 0, 'DESCRIPTOR'],
        ['LEAKSITE_URL', 'Leak Site URL', 0, 'ENTITY'],
        ['LEAKSITE_CONTENT', 'Leak Site Content', 1, 'DATA'],
        ['PASSWORD_COMPROMISED', 'Compromised Password', 0, 'DATA'],
        ['PERSON_NAME', 'Person Name', 0, 'ENTITY'],
        ['PHONE_NUMBER', 'Phone Number', 0, 'ENTITY'],
        ['PHONE_NUMBER_COMPROMISED', 'Phone Number Compromised', 0, 'DESCRIPTOR'],
        ['PHONE_NUMBER_TYPE', 'Phone Number Type', 0, 'DESCRIPTOR'],
        ['PHYSICAL_ADDRESS', 'Physical Address', 0, 'ENTITY'],
        ['PHYSICAL_COORDINATES', 'Physical Coordinates', 0, 'ENTITY'],
        ['PGP_KEY', 'PGP Public Key', 0, 'DATA'],
        ['PROXY_HOST', 'Proxy Host', 0, 'DESCRIPTOR'],
        ['PROVIDER_DNS', 'Name Server (DNS ''NS'' Records)', 0, 'ENTITY'],
        ['PROVIDER_JAVASCRIPT', 'Externally Hosted Javascript', 0, 'ENTITY'],
        ['PROVIDER_MAIL', 'Email Gateway (DNS ''MX'' Records)', 0, 'ENTITY'],
        ['PROVIDER_HOSTING', 'Hosting Provider', 0, 'ENTITY'],
        ['PROVIDER_TELCO', 'Telecommunications Provider', 0, 'ENTITY'],
        ['PUBLIC_CODE_REPO', 'Public Code Repository', 0, 'ENTITY'],
        ['RAW_RIR_DATA', 'Raw Data from RIRs/APIs', 1, 'DATA'],
        ['RAW_DNS_RECORDS', 'Raw DNS Records', 1, 'DATA'],
        ['RAW_FILE_META_DATA', 'Raw File Meta Data', 1, 'DATA'],
        ['SEARCH_ENGINE_WEB_CONTENT', 'Search Engine Web Content', 1, 'DATA'],
        ['SOCIAL_MEDIA', 'Social Media Presence', 0, 'ENTITY'],
        ['SOCIAL_MEDIA_PROFILE', 'Social Media Profile', 0, 'ENTITY'],
        ['SOCIAL_MEDIA_PROFILE_URL', 'Social Media Profile URL', 0, 'ENTITY'],
        ['SIMILAR_ACCOUNT_EXTERNAL', 'Similar Account on External Site', 0, 'ENTITY'],
        ['SIMILARDOMAIN', 'Similar Domain', 0, 'ENTITY'],
        ['SIMILARDOMAIN_WHOIS', 'Similar Domain - Whois', 1, 'DATA'],
        ['SOFTWARE_USED', 'Software Used', 0, 'SUBENTITY'],
        ['SSL_CERTIFICATE_RAW', 'SSL Certificate - Raw Data', 1, 'DATA'],
        ['SSL_CERTIFICATE_ISSUED', 'SSL Certificate - Issued to', 0, 'ENTITY'],
        ['SSL_CERTIFICATE_ISSUER', 'SSL Certificate - Issued by', 0, 'ENTITY'],
        ['SSL_CERTIFICATE_MISMATCH', 'SSL Certificate Host Mismatch', 0, 'DESCRIPTOR'],
        ['SSL_CERTIFICATE_EXPIRED', 'SSL Certificate Expired', 0, 'DESCRIPTOR'],
        ['SSL_CERTIFICATE_EXPIRING', 'SSL Certificate Expiring', 0, 'DESCRIPTOR'],
        ['TARGET_WEB_CONTENT', 'Web Content', 1, 'DATA'],
        ['TARGET_WEB_CONTENT_TYPE', 'Web Content Type', 0, 'DESCRIPTOR'],
        ['TARGET_WEB_COOKIE', 'Cookies', 0, 'DATA'],
        ['TCP_PORT_OPEN', 'Open TCP Port', 0, 'SUBENTITY'],
        ['TCP_PORT_OPEN_BANNER', 'Open TCP Port Banner', 0, 'DATA'],
        ['TOR_EXIT_NODE', 'TOR Exit Node', 0, 'DESCRIPTOR'],
        ['UDP_PORT_OPEN', 'Open UDP Port', 0, 'SUBENTITY'],
        ['UDP_PORT_OPEN_INFO', 'Open UDP Port Information', 0, 'DATA'],
        ['URL_ADBLOCKED_EXTERNAL',
            'URL (AdBlocked External)', 0, 'DESCRIPTOR'],
        ['URL_ADBLOCKED_INTERNAL',
            'URL (AdBlocked Internal)', 0, 'DESCRIPTOR'],
        ['URL_FORM', 'URL (Form)', 0, 'DESCRIPTOR'],
        ['URL_FLASH', 'URL (Uses Flash)', 0, 'DESCRIPTOR'],
        ['URL_JAVASCRIPT', 'URL (Uses Javascript)', 0, 'DESCRIPTOR'],
        ['URL_WEB_FRAMEWORK', 'URL (Uses a Web Framework)', 0, 'DESCRIPTOR'],
        ['URL_JAVA_APPLET', 'URL (Uses Java Applet)', 0, 'DESCRIPTOR'],
        ['URL_STATIC', 'URL (Purely Static)', 0, 'DESCRIPTOR'],
        ['URL_PASSWORD', 'URL (Accepts Passwords)', 0, 'DESCRIPTOR'],
        ['URL_UPLOAD', 'URL (Accepts Uploads)', 0, 'DESCRIPTOR'],
        ['URL_FORM_HISTORIC', 'Historic URL (Form)', 0, 'DESCRIPTOR'],
        ['URL_FLASH_HISTORIC', 'Historic URL (Uses Flash)', 0, 'DESCRIPTOR'],
        ['URL_JAVASCRIPT_HISTORIC',
            'Historic URL (Uses Javascript)', 0, 'DESCRIPTOR'],
        ['URL_WEB_FRAMEWORK_HISTORIC',
            'Historic URL (Uses a Web Framework)', 0, 'DESCRIPTOR'],
        ['URL_JAVA_APPLET_HISTORIC',
            'Historic URL (Uses Java Applet)', 0, 'DESCRIPTOR'],
        ['URL_STATIC_HISTORIC',
            'Historic URL (Purely Static)', 0, 'DESCRIPTOR'],
        ['URL_PASSWORD_HISTORIC',
            'Historic URL (Accepts Passwords)', 0, 'DESCRIPTOR'],
        ['URL_UPLOAD_HISTORIC',
            'Historic URL (Accepts Uploads)', 0, 'DESCRIPTOR'],
        ['USERNAME', 'Username', 0, 'ENTITY'],
        ['VPN_HOST', 'VPN Host', 0, 'DESCRIPTOR'],
        ['VULNERABILITY_DISCLOSURE',
            'Vulnerability - Third Party Disclosure', 0, 'DESCRIPTOR'],
        ['VULNERABILITY_CVE_CRITICAL', 'Vulnerability - CVE Critical', 0, 'DESCRIPTOR'],
        ['VULNERABILITY_CVE_HIGH', 'Vulnerability - CVE High', 0, 'DESCRIPTOR'],
        ['VULNERABILITY_CVE_MEDIUM', 'Vulnerability - CVE Medium', 0, 'DESCRIPTOR'],
        ['VULNERABILITY_CVE_LOW', 'Vulnerability - CVE Low', 0, 'DESCRIPTOR'],
        ['VULNERABILITY_GENERAL', 'Vulnerability - General', 0, 'DESCRIPTOR'],
        ['WEB_ANALYTICS_ID', 'Web Analytics', 0, 'ENTITY'],
        ['WEBSERVER_BANNER', 'Web Server', 0, 'DATA'],
        ['WEBSERVER_HTTPHEADERS', 'HTTP Headers', 1, 'DATA'],
        ['WEBSERVER_STRANGEHEADER', 'Non-Standard HTTP Header', 0, 'DATA'],
        ['WEBSERVER_TECHNOLOGY', 'Web Technology', 0, 'DESCRIPTOR'],
        ['WIFI_ACCESS_POINT', 'WiFi Access Point Nearby', 0, 'ENTITY'],
        ['WIKIPEDIA_PAGE_EDIT', 'Wikipedia Page Edit', 0, 'DESCRIPTOR'],
    ]

    def __init__(self, opts: dict, init: bool = False) -> None:
        """Initialize database and create handle to the database file. Creates
        the database file if it does not exist. Creates database schema if it
        does not exist.

        Args:
            opts (dict): must specify the database file path in the '__database' key
            init (bool): initialise the database schema.
                         if the database file does not exist this option will be ignored.

        Raises:
            TypeError: arg type was invalid
            ValueError: arg value was invalid
            IOError: database I/O failed
        """

        if not isinstance(opts, dict):
            raise TypeError(f"opts is {type(opts)}; expected dict()") from None
        if not opts:
            raise ValueError("opts is empty") from None
        if not opts.get('__database'):
            raise ValueError("opts['__database'] is empty") from None

        self.db_type = opts.get('__dbtype', 'postgresql')  # Default to PostgreSQL (SQLite no longer supported)

        # SQLite support has been removed - only PostgreSQL is supported
        if self.db_type == 'sqlite':
            raise ValueError("SQLite is not supported. Please use PostgreSQL by setting __dbtype='postgresql'")

        if self.db_type == 'postgresql':
            if not HAS_PSYCOPG2:
                raise ImportError("psycopg2 is required for PostgreSQL support. Install it with: pip install psycopg2-binary")
            try:
                self.conn = psycopg2.connect(opts['__database'])
                self.dbh = self.conn.cursor(
                    cursor_factory=psycopg2.extras.DictCursor)
            except Exception as e:
                raise IOError(
                    f"Error connecting to PostgreSQL database {opts['__database']}") from e

            with self.dbhLock:
                try:
                    self.dbh.execute('SELECT COUNT(*) FROM tbl_scan_config')
                except (psycopg2.Error if psycopg2 else Exception):
                    self.conn.rollback()
                    init = True
                    try:
                        self.create()
                    except Exception as e:
                        raise IOError(
                            "Tried to set up the SpiderFoot database schema, but failed") from e

                if init:
                    for row in self.eventDetails:
                        event = row[0]
                        event_descr = row[1]
                        event_raw = row[2]
                        event_type = row[3]
                        qry = "INSERT INTO tbl_event_types (event, event_descr, event_raw, event_type) VALUES (%s, %s, %s, %s)"

                        try:
                            self.dbh.execute(qry, (
                                event, event_descr, event_raw, event_type
                            ))
                            self.conn.commit()
                        except Exception:
                            continue
                    self.conn.commit()
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    #
    # Back-end database operations
    #

    def create(self) -> None:
        """Create the database schema.

        Raises:
            IOError: database I/O failed
        """

        with self.dbhLock:
            try:
                if self.db_type == 'sqlite':
                    for qry in self.createSchemaQueries:
                        self.dbh.execute(qry)
                elif self.db_type == 'postgresql':
                    for qry in self.createPostgreSQLSchemaQueries:
                        self.dbh.execute(qry)
                
                self.conn.commit()
                
                # Insert event types
                for row in self.eventDetails:
                    event = row[0]
                    event_descr = row[1]
                    event_raw = row[2]
                    event_type = row[3]
                    
                    if self.db_type == 'sqlite':
                        qry = "INSERT INTO tbl_event_types (event, event_descr, event_raw, event_type) VALUES (?, ?, ?, ?)"
                        params = (event, event_descr, event_raw, event_type)
                    else:  # postgresql
                        qry = "INSERT INTO tbl_event_types (event, event_descr, event_raw, event_type) VALUES (%s, %s, %s, %s) ON CONFLICT (event) DO NOTHING"
                        params = (event, event_descr, event_raw, event_type)

                    self.dbh.execute(qry, params)
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when setting up database") from e

    def close(self) -> None:
        """Close the database handle and connection."""

        with self.dbhLock:
            if self.dbh:
                self.dbh.close()
                self.dbh = None
            if self.conn:
                self.conn.close()
                self.conn = None

    def vacuumDB(self) -> None:
        """Vacuum the database. Clears unused database file pages.

        Returns:
            bool: success

        Raises:
            IOError: database I/O failed
        """
        with self.dbhLock:
            try:
                if ((self.db_type == 'sqlite') or (self.db_type == 'postgresql')):
                    self.dbh.execute("VACUUM")
                self.conn.commit()
                return True
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when vacuuming the database") from e
        return False

    def search(self, criteria: dict, filterFp: bool = False) -> list:
        """Search database.

        Args:
            criteria (dict): search criteria such as:
                - scan_id (search within a scan, if omitted search all)
                - type (search a specific type, if omitted search all)
                - value (search values for a specific string, if omitted search all)
                - regex (search values for a regular expression)
                ** at least two criteria must be set **
            filterFp (bool): filter out false positives

        Returns:
            list: search results

        Raises:
            TypeError: arg type was invalid
            ValueError: arg value was invalid
            IOError: database I/O failed
        """
        if not isinstance(criteria, dict):
            raise TypeError(
                f"criteria is {type(criteria)}; expected dict()") from None

        valid_criteria = ['scan_id', 'type', 'value', 'regex']

        for key in list(criteria.keys()):
            if key not in valid_criteria:
                criteria.pop(key, None)
                continue

            if not isinstance(criteria.get(key), str):
                raise TypeError(
                    f"criteria[{key}] is {type(criteria.get(key))}; expected str()") from None

            if not criteria[key]:
                criteria.pop(key, None)
                continue

        if len(criteria) == 0:
            raise ValueError(
                f"No valid search criteria provided; expected: {', '.join(valid_criteria)}") from None

        if len(criteria) == 1:
            raise ValueError(
                "Only one search criteria provided; expected at least two")

        qvars = list()
        qry = "SELECT ROUND(c.generated) AS generated, c.data, \
            s.data as source_data, \
            c.module, c.type, c.confidence, c.visibility, c.risk, c.hash, \
            c.source_event_hash, t.event_descr, t.event_type, c.scan_instance_id, \
            c.false_positive as fp, s.false_positive as parent_fp \
            FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t \
            WHERE s.scan_instance_id = c.scan_instance_id AND \
            t.event = c.type AND c.source_event_hash = s.hash "

        if filterFp:
            qry += " AND c.false_positive <> 1 "

        ph = self._placeholder()
        if criteria.get('scan_id') is not None:
            qry += f"AND c.scan_instance_id = {ph} "
            qvars.append(criteria['scan_id'])

        if criteria.get('type') is not None:
            qry += f" AND c.type = {ph} "
            qvars.append(criteria['type'])

        if criteria.get('value') is not None:
            qry += f" AND (c.data LIKE {ph} OR s.data LIKE {ph}) "
            qvars.append(criteria['value'])
            qvars.append(criteria['value'])

        if criteria.get('regex') is not None:
            qry += f" AND (c.data REGEXP {ph} OR s.data REGEXP {ph}) "
            qvars.append(criteria['regex'])
            qvars.append(criteria['regex'])

        qry += " ORDER BY c.data"

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching search results") from e

    def eventTypes(self) -> list:
        """Get event types.

        Returns:
            list: event types

        Raises:
            IOError: database I/O failed
        """

        qry = "SELECT event_descr, event, event_raw, event_type FROM tbl_event_types"
        with self.dbhLock:
            try:
                self.dbh.execute(qry)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when retrieving event types") from e

    def scanLogEvents(self, batch: list) -> bool:
        """Logs a batch of events to the database.

        Args:
            batch (list): tuples containing: instanceId, classification, message, component, logTime

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed

        Returns:
            bool: Whether the logging operation succeeded
        """
        if not batch:
            return True

        inserts = []

        for item in batch:
            if len(item) != 5:
                continue
                
            instanceId, classification, message, component, logTime = item
            
            if not isinstance(instanceId, str):
                continue

            if not isinstance(classification, str):
                continue

            if not isinstance(message, str):
                continue

            if not component:
                component = "SpiderFoot"

            # Convert logTime to proper format if needed
            if isinstance(logTime, float):
                logTime = int(logTime * 1000)
            elif isinstance(logTime, int) and logTime < 1000000000000:  # Assume seconds if too small
                logTime = logTime * 1000

            inserts.append((instanceId, logTime,
                           component, classification, message))

        if not inserts:
            return True

        if self.db_type == 'sqlite':
            qry = "INSERT INTO tbl_scan_log \
                (scan_instance_id, generated, component, type, message) \
                VALUES (?, ?, ?, ?, ?)"
        else:  # postgresql
            qry = "INSERT INTO tbl_scan_log \
                (scan_instance_id, generated, component, type, message) \
                VALUES (%s, %s, %s, %s, %s)"

        with self.dbhLock:
            try:
                # Ensure connection is alive
                if not self.conn:
                    print(f"[WARNING] Database connection lost during log batch insert")
                    return False
                    
                self.dbh.executemany(qry, inserts)
                self.conn.commit()
                return True
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                # More specific error handling with logging
                error_msg = str(e).lower()
                if "locked" in error_msg or "thread" in error_msg:
                    print(f"[WARNING] Database locked during log insert: {e}")
                    return False
                elif "connection" in error_msg or "closed" in error_msg:
                    print(f"[ERROR] Database connection error during log insert: {e}")
                    try:
                        self.conn.rollback()
                    except:
                        pass
                    return False
                else:
                    print(f"[ERROR] SQL error during log batch insert: {e}")
                    try:
                        self.conn.rollback()
                    except:
                        pass
                    return False
            except Exception as e:
                print(f"[ERROR] Unexpected error during log batch insert: {e}")
                return False

    def scanLogEvent(self, instanceId: str, classification: str, message: str, component: str = None) -> None:
        """Log an event to the database.

        Args:
            instanceId (str): scan instance ID
            classification (str): TBD
            message (str): TBD
            component (str): TBD

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed

        Todo:
            Do something smarter to handle database locks
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(classification, str):
            raise TypeError(
                f"classification is {type(classification)}; expected str()") from None

        if not isinstance(message, str):
            raise TypeError(
                f"message is {type(message)}; expected str()") from None

        if not component:
            component = "SpiderFoot"

        qry = f"INSERT INTO tbl_scan_log \
            (scan_instance_id, generated, component, type, message) \
            VALUES ({self._placeholder(5)})"

        with self.dbhLock:
            try:
                # Ensure connection is alive
                if not self.conn:
                    raise IOError("Database connection is closed")
                    
                self.dbh.execute(qry, (
                    instanceId, time.time() * 1000, component, classification, message
                ))
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                error_msg = str(e).lower()
                if "locked" in error_msg or "thread" in error_msg:
                    print(f"[WARNING] Database locked during single log insert: {e}")
                    pass  # Silent fail for lock issues
                elif "connection" in error_msg or "closed" in error_msg:
                    print(f"[ERROR] Database connection error during single log insert: {e}")
                    raise IOError("Unable to log scan event - database connection failed") from e
                else:
                    print(f"[ERROR] SQL error during single log insert: {e}")
                    raise IOError("Unable to log scan event in database") from e
            except Exception as e:
                print(f"[ERROR] Unexpected error during single log insert: {e}")
                raise IOError("Unable to log scan event in database") from e

    def scanInstanceCreate(self, instanceId: str, scanName: str, scanTarget: str) -> None:
        """Store a scan instance in the database.

        Args:
            instanceId (str): scan instance ID
            scanName(str): scan name
            scanTarget (str): scan target

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(scanName, str):
            raise TypeError(
                f"scanName is {type(scanName)}; expected str()") from None

        if not isinstance(scanTarget, str):
            raise TypeError(
                f"scanTarget is {type(scanTarget)}; expected str()") from None

        if self.db_type == 'sqlite':
            qry = "INSERT INTO tbl_scan_instance \
                (guid, name, seed_target, created, status) \
                VALUES (?, ?, ?, ?, ?)"
        else:  # postgresql
            qry = "INSERT INTO tbl_scan_instance \
                (guid, name, seed_target, created, status) \
                VALUES (%s, %s, %s, %s, %s)"

        with self.dbhLock:
            try:
                self.dbh.execute(qry, (
                    instanceId, scanName, scanTarget, time.time() * 1000, 'CREATED'
                ))
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "Unable to create scan instance in database") from e

    def scanInstanceSet(self, instanceId: str, started: str = None, ended: str = None, status: str = None) -> None:
        """Update the start time, end time or status (or all 3) of a scan
        instance.

        Args:
            instanceId (str): scan instance ID
            started (str): scan start time
            ended (str): scan end time
            status (str): scan status

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        qvars = list()
        qry = "UPDATE tbl_scan_instance SET "
        ph = self._placeholder()

        if started is not None:
            qry += f" started = {ph},"
            qvars.append(started)

        if ended is not None:
            qry += f" ended = {ph},"
            qvars.append(ended)

        if status is not None:
            qry += f" status = {ph},"
            qvars.append(status)

        # guid = guid is a little hack to avoid messing with , placement above
        qry += f" guid = guid WHERE guid = {ph}"
        qvars.append(instanceId)

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                self.conn.commit()
            except (psycopg2.Error):
                raise IOError(
                    "Unable to set information for the scan instance.") from None

    def scanInstanceGet(self, instanceId: str) -> list:
        """Return info about a scan instance (name, target, created, started,
        ended, status)

        Args:
            instanceId (str): scan instance ID

        Returns:
            list: scan instance info

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        ph = self._placeholder()
        qry = f"SELECT name, seed_target, ROUND(created/1000) AS created, \
            ROUND(started/1000) AS started, ROUND(ended/1000) AS ended, status \
            FROM tbl_scan_instance WHERE guid = {ph}"
        qvars = [instanceId]

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchone()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when retrieving scan instance") from e

    def scanResultSummary(self, instanceId: str, by: str = "type") -> list:
        """Obtain a summary of the results, filtered by event type, module or
        entity.

        Args:
            instanceId (str): scan instance ID
            by (str): filter by type

        Returns:
            list: scan instance info

        Raises:
            TypeError: arg type was invalid
            ValueError: arg value was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(by, str):
            raise TypeError(f"by is {type(by)}; expected str()") from None

        if by not in ["type", "module", "entity"]:
            raise ValueError(f"Invalid filter by value: {by}") from None

        ph = self._placeholder()

        if by == "type":
            qry = f"SELECT r.type, e.event_descr, MAX(ROUND(generated)) AS last_in, \
                count(*) AS total, count(DISTINCT r.data) as utotal FROM \
                tbl_scan_results r, tbl_event_types e WHERE e.event = r.type \
                AND r.scan_instance_id = {ph} GROUP BY r.type, e.event_descr ORDER BY e.event_descr"

        if by == "module":
            qry = f"SELECT r.module, '', MAX(ROUND(generated)) AS last_in, \
                count(*) AS total, count(DISTINCT r.data) as utotal FROM \
                tbl_scan_results r, tbl_event_types e WHERE e.event = r.type \
                AND r.scan_instance_id = {ph} GROUP BY r.module ORDER BY r.module DESC"

        if by == "entity":
            qry = f"SELECT r.data, e.event_descr, MAX(ROUND(generated)) AS last_in, \
                count(*) AS total, count(DISTINCT r.data) as utotal FROM \
                tbl_scan_results r, tbl_event_types e WHERE e.event = r.type \
                AND r.scan_instance_id = {ph} \
                AND e.event_type in ('ENTITY') \
                GROUP BY r.data, e.event_descr ORDER BY total DESC limit 50"

        qvars = [instanceId]

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching result summary") from e

    def scanCorrelationSummary(self, instanceId: str, by: str = "rule") -> list:
        """Obtain a summary of the correlations, filtered by rule or risk.

        Args:
            instanceId (str): scan instance ID
            by (str): filter by rule or risk

        Returns:
            list: scan correlation summary

        Raises:
            TypeError: arg type was invalid
            ValueError: arg value was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(by, str):
            raise TypeError(f"by is {type(by)}; expected str()") from None

        if by not in ["rule", "risk"]:
            raise ValueError(f"Invalid filter by value: {by}") from None

        ph = self._placeholder()

        if by == "risk":
            qry = f"SELECT rule_risk, count(*) AS total FROM \
                tbl_scan_correlation_results \
                WHERE scan_instance_id = {ph} GROUP BY rule_risk ORDER BY rule_risk"

        if by == "rule":
            qry = f"SELECT rule_id, rule_name, rule_risk, rule_descr, \
                count(*) AS total FROM \
                tbl_scan_correlation_results \
                WHERE scan_instance_id = {ph} GROUP BY rule_id, rule_name, rule_risk, rule_descr ORDER BY rule_id"

        qvars = [instanceId]

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching correlation summary") from e

    def scanCorrelationList(self, instanceId: str) -> list:
        """Obtain a list of the correlations from a scan.

        Args:
            instanceId (str): scan instance ID

        Returns:
            list: scan correlation list

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        ph = self._placeholder()
        qry = f"SELECT c.id, c.title, c.rule_id, c.rule_risk, c.rule_name, \
            c.rule_descr, c.rule_logic, count(e.event_hash) AS event_count FROM \
            tbl_scan_correlation_results c, tbl_scan_correlation_results_events e \
            WHERE c.scan_instance_id = {ph} AND c.id = e.correlation_id \
            GROUP BY c.id, c.title, c.rule_id, c.rule_risk, c.rule_name, c.rule_descr, c.rule_logic \
            ORDER BY c.title, c.rule_risk"

        qvars = [instanceId]

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching correlation list") from e

    def scanResultEvent(
        self,
        instanceId: str,
        eventType: str = 'ALL',
        srcModule: str = None,
        data: list = None,
        sourceId: list = None,
        correlationId: str = None,
        filterFp: bool = False
    ) -> list:
        """Obtain the data for a scan and event type.

        Args:
            instanceId (str): scan instance ID
            eventType (str): filter by event type
            srcModule (str): filter by the generating module
            data (list): filter by the data
            sourceId (list): filter by the ID of the source event
            correlationId (str): filter by the ID of a correlation result
            filterFp (bool): filter false positives

        Returns:
            list: scan results

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(eventType, str) and not isinstance(eventType, list):
            raise TypeError(
                f"eventType is {type(eventType)}; expected str() or list()") from None

        qry = "SELECT ROUND(c.generated) AS generated, c.data, \
            s.data as source_data, \
            c.module, c.type, c.confidence, c.visibility, c.risk, c.hash, \
            c.source_event_hash, t.event_descr, t.event_type, s.scan_instance_id, \
            c.false_positive as fp, s.false_positive as parent_fp \
            FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t "

        if correlationId:
            qry += ", tbl_scan_correlation_results_events ce "

        ph = self._placeholder()
        qry += f"WHERE c.scan_instance_id = {ph} AND c.source_event_hash = s.hash AND \
            s.scan_instance_id = c.scan_instance_id AND t.event = c.type"

        qvars = [instanceId]

        if correlationId:
            qry += f" AND ce.event_hash = c.hash AND ce.correlation_id = {ph}"
            qvars.append(correlationId)

        if eventType != "ALL":
            if isinstance(eventType, list):
                qry += " AND c.type in (" + self._placeholder(len(eventType)) + ")"
                qvars.extend(eventType)
            else:
                qry += f" AND c.type = {ph}"
                qvars.append(eventType)

        if filterFp:
            qry += " AND c.false_positive <> 1"

        if srcModule:
            if isinstance(srcModule, list):
                qry += " AND c.module in (" + self._placeholder(len(srcModule)) + ")"
                qvars.extend(srcModule)
            else:
                qry += f" AND c.module = {ph}"
                qvars.append(srcModule)

        if data:
            if isinstance(data, list):
                qry += " AND c.data in (" + self._placeholder(len(data)) + ")"
                qvars.extend(data)
            else:
                qry += f" AND c.data = {ph}"
                qvars.append(data)

        if sourceId:
            if isinstance(sourceId, list):
                qry += " AND c.source_event_hash in (" + self._placeholder(len(sourceId)) + ")"
                qvars.extend(sourceId)
            else:
                qry += f" AND c.source_event_hash = {ph}"
                qvars.append(sourceId)

        qry += " ORDER BY c.data"

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching result events") from e

    def scanResultEventUnique(self, instanceId: str, eventType: str = 'ALL', filterFp: bool = False) -> list:
        """Obtain a unique list of elements.

        Args:
            instanceId (str): scan instance ID
            eventType (str): filter by event type
            filterFp (bool): filter false positives

        Returns:
            list: unique scan results

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(eventType, str):
            raise TypeError(
                f"eventType is {type(eventType)}; expected str()") from None

        ph = self._placeholder()
        qry = f"SELECT DISTINCT data, type, COUNT(*) FROM tbl_scan_results \
            WHERE scan_instance_id = {ph}"
        qvars = [instanceId]

        if eventType != "ALL":
            qry += f" AND type = {ph}"
            qvars.append(eventType)

        if filterFp:
            qry += " AND false_positive <> 1"

        qry += " GROUP BY type, data ORDER BY COUNT(*)"

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching unique result events") from e

    def scanLogs(self, instanceId: str, limit: int = None, fromRowId: int = 0, reverse: bool = False) -> list:
        """Get scan logs.

        Args:
            instanceId (str): scan instance ID
            limit (int): limit number of results
            fromRowId (int): retrieve logs starting from row ID
            reverse (bool): search result order

        Returns:
            list: scan logs

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        ph = self._placeholder()
        if self.db_type == 'sqlite':
            qry = f"SELECT generated AS generated, component, \
                type, message, rowid FROM tbl_scan_log WHERE scan_instance_id = {ph}"
        else:  # postgresql - use hash of ctid as rowid equivalent
            qry = f"SELECT generated AS generated, component, \
                type, message, (CAST(('x'||lpad(split_part(replace(replace(ctid::text,'(',''),')',''),',' ,1),'8','0'))AS bit(32))::int)*1000000 + (CAST(('x'||lpad(split_part(replace(replace(ctid::text,'(',''),')',''),',',2),'8','0'))AS bit(32))::int) as rowid FROM tbl_scan_log WHERE scan_instance_id = {ph}"
        if fromRowId:
            qry += f" and rowid > {ph}"

        qry += " ORDER BY generated "
        if reverse:
            qry += "ASC"
        else:
            qry += "DESC"
        qvars = [instanceId]

        if fromRowId:
            qvars.append(str(fromRowId))

        if limit is not None:
            qry += f" LIMIT {ph}"
            qvars.append(str(limit))

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching scan logs") from e

    def scanErrors(self, instanceId: str, limit: int = 0) -> list:
        """Get scan errors.

        Args:
            instanceId (str): scan instance ID
            limit (int): limit number of results

        Returns:
            list: scan errors

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(limit, int):
            raise TypeError(
                f"limit is {type(limit)}; expected int()") from None

        ph = self._placeholder()
        qry = f"SELECT generated AS generated, component, \
            message FROM tbl_scan_log WHERE scan_instance_id = {ph} \
            AND type = 'ERROR' ORDER BY generated DESC"
        qvars = [instanceId]

        if limit:
            qry += f" LIMIT {ph}"
            qvars.append(str(limit))

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching scan errors") from e

    def scanInstanceDelete(self, instanceId: str) -> bool:
        """Delete a scan instance.

        Args:
            instanceId (str): scan instance ID

        Returns:
            bool: success

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        ph = self._placeholder()
        # Delete child records first, then parent
        # Correlation events must be deleted before correlation results
        qry1 = f"DELETE FROM tbl_scan_correlation_results_events WHERE correlation_id IN (SELECT id FROM tbl_scan_correlation_results WHERE scan_instance_id = {ph})"
        qry2 = f"DELETE FROM tbl_scan_correlation_results WHERE scan_instance_id = {ph}"
        qry3 = f"DELETE FROM tbl_scan_log WHERE scan_instance_id = {ph}"
        qry4 = f"DELETE FROM tbl_scan_config WHERE scan_instance_id = {ph}"
        qry5 = f"DELETE FROM tbl_scan_results WHERE scan_instance_id = {ph}"
        # Delete parent last
        qry6 = f"DELETE FROM tbl_scan_instance WHERE guid = {ph}"
        qvars = [instanceId]

        with self.dbhLock:
            try:
                self.dbh.execute(qry1, qvars)
                self.dbh.execute(qry2, qvars)
                self.dbh.execute(qry3, qvars)
                self.dbh.execute(qry4, qvars)
                self.dbh.execute(qry5, qvars)
                self.dbh.execute(qry6, qvars)
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when deleting scan") from e

        return True

    def scanResultsUpdateFP(self, instanceId: str, resultHashes: list, fpFlag: int) -> bool:
        """Set the false positive flag for a result.

        Args:
            instanceId (str): scan instance ID
            resultHashes (list): list of event hashes
            fpFlag (int): false positive

        Returns:
            bool: success

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(resultHashes, list):
            raise TypeError(
                f"resultHashes is {type(resultHashes)}; expected list()") from None

        ph = self._placeholder()
        with self.dbhLock:
            for resultHash in resultHashes:
                qry = f"UPDATE tbl_scan_results SET false_positive = {ph} WHERE \
                    scan_instance_id = {ph} AND hash = {ph}"
                qvars = [fpFlag, instanceId, resultHash]
                try:
                    self.dbh.execute(qry, qvars)
                except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                    raise IOError(
                        "SQL error encountered when updating false-positive") from e

            try:
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when updating false-positive") from e

        return True

    def configSet(self, optMap: dict = {}) -> bool:
        """Store the default configuration in the database.

        Args:
            optMap (dict): config options

        Returns:
            bool: success

        Raises:
            TypeError: arg type was invalid
            ValueError: arg value was invalid
            IOError: database I/O failed
        """

        if not isinstance(optMap, dict):
            raise TypeError(
                f"optMap is {type(optMap)}; expected dict()") from None
        if not optMap:
            raise ValueError("optMap is empty") from None

        if self.db_type == 'sqlite':
            qry = "REPLACE INTO tbl_config (scope, opt, val) VALUES (?, ?, ?)"
        else:  # postgresql
            qry = """
                INSERT INTO tbl_config (scope, opt, val) VALUES (%s, %s, %s)
                ON CONFLICT (scope, opt) DO UPDATE SET val = EXCLUDED.val
            """

        with self.dbhLock:
            for opt in list(optMap.keys()):
                # Module option
                if ":" in opt:
                    parts = opt.split(':')
                    qvals = [parts[0], parts[1], optMap[opt]]
                else:
                    # Global option
                    qvals = ["GLOBAL", opt, optMap[opt]]

                try:
                    self.dbh.execute(qry, qvals)
                except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                    raise IOError(
                        "SQL error encountered when storing config, aborting") from e

            try:
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when storing config, aborting") from e

        return True

    def configGet(self) -> dict:
        """Retreive the config from the database.

        Returns:
            dict: config

        Raises:
            IOError: database I/O failed
        """

        qry = "SELECT scope, opt, val FROM tbl_config"

        retval = dict()

        with self.dbhLock:
            try:
                self.dbh.execute(qry)
                for [scope, opt, val] in self.dbh.fetchall():
                    if scope == "GLOBAL":
                        retval[opt] = val
                    else:
                        retval[f"{scope}:{opt}"] = val

                return retval
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching configuration") from e

    def configClear(self) -> None:
        """Reset the config to default.

        Clears the config from the database and lets the hard-coded settings in the code take effect.

        Raises:
            IOError: database I/O failed
        """

        qry = "DELETE from tbl_config"
        with self.dbhLock:
            try:
                self.dbh.execute(qry)
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "Unable to clear configuration from the database") from e

    def scanConfigSet(self, scan_id, optMap=dict()) -> None:
        """Store a configuration value for a scan.

        Args:
            scan_id (int): scan instance ID
            optMap (dict): config options

        Raises:
            TypeError: arg type was invalid
            ValueError: arg value was invalid
            IOError: database I/O failed
        """

        if not isinstance(optMap, dict):
            raise TypeError(
                f"optMap is {type(optMap)}; expected dict()") from None
        if not optMap:
            raise ValueError("optMap is empty") from None

        if self.db_type == 'sqlite':
            qry = "REPLACE INTO tbl_scan_config \
                    (scan_instance_id, component, opt, val) VALUES (?, ?, ?, ?)"
        else:  # postgresql
            qry = """
                INSERT INTO tbl_scan_config (scan_instance_id, component, opt, val)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (scan_instance_id, component, opt) DO UPDATE SET val = EXCLUDED.val
            """

        with self.dbhLock:
            for opt in list(optMap.keys()):
                # Module option
                if ":" in opt:
                    parts = opt.split(':')
                    qvals = [scan_id, parts[0], parts[1], optMap[opt]]
                else:
                    # Global option
                    qvals = [scan_id, "GLOBAL", opt, optMap[opt]]

                try:
                    self.dbh.execute(qry, qvals)
                except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                    raise IOError(
                        "SQL error encountered when storing config, aborting") from e

            try:
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when storing config, aborting") from e

    def scanConfigGet(self, instanceId: str) -> dict:
        """Retrieve configuration data for a scan component.

        Args:
            instanceId (str): scan instance ID

        Returns:
            dict: configuration data

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        ph = self._placeholder()
        qry = f"SELECT component, opt, val FROM tbl_scan_config \
                WHERE scan_instance_id = {ph} ORDER BY component, opt"
        qvars = [instanceId]

        retval = dict()

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                for [component, opt, val] in self.dbh.fetchall():
                    if component == "GLOBAL":
                        retval[opt] = val
                    else:
                        retval[f"{component}:{opt}"] = val
                return retval
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching configuration") from e

    def scanEventStore(self, instanceId: str, sfEvent, truncateSize: int = 0) -> None:
        """Store an event in the database.

        Args:
            instanceId (str): scan instance ID
            sfEvent (SpiderFootEvent): event to be stored in the database
            truncateSize (int): truncate size for event data

        Raises:
            TypeError: arg type was invalid
            ValueError: arg value was invalid
            IOError: database I/O failed
        """
        from spiderfoot import SpiderFootEvent

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not instanceId:
            raise ValueError("instanceId is empty") from None

        if not isinstance(sfEvent, SpiderFootEvent):
            raise TypeError(
                f"sfEvent is {type(sfEvent)}; expected SpiderFootEvent()") from None

        if not isinstance(sfEvent.generated, float):
            raise TypeError(
                f"sfEvent.generated is {type(sfEvent.generated)}; expected float()") from None

        if not sfEvent.generated:
            raise ValueError("sfEvent.generated is empty") from None

        if not isinstance(sfEvent.eventType, str):
            raise TypeError(
                f"sfEvent.eventType is {type(sfEvent.eventType,)}; expected str()") from None

        if not sfEvent.eventType:
            raise ValueError("sfEvent.eventType is empty") from None

        if not isinstance(sfEvent.data, str):
            raise TypeError(
                f"sfEvent.data is {type(sfEvent.data)}; expected str()") from None

        if not sfEvent.data:
            raise ValueError("sfEvent.data is empty") from None

        if not isinstance(sfEvent.module, str):
            raise TypeError(
                f"sfEvent.module is {type(sfEvent.module)}; expected str()") from None

        if not sfEvent.module and sfEvent.eventType != "ROOT":
            raise ValueError("sfEvent.module is empty") from None

        if not isinstance(sfEvent.confidence, int):
            raise TypeError(
                f"sfEvent.confidence is {type(sfEvent.confidence)}; expected int()") from None

        if not 0 <= sfEvent.confidence <= 100:
            raise ValueError(
                f"sfEvent.confidence value is {type(sfEvent.confidence)}; expected 0 - 100") from None

        if not isinstance(sfEvent.visibility, int):
            raise TypeError(
                f"sfEvent.visibility is {type(sfEvent.visibility)}; expected int()") from None

        if not 0 <= sfEvent.visibility <= 100:
            raise ValueError(
                f"sfEvent.visibility value is {type(sfEvent.visibility)}; expected 0 - 100") from None

        if not isinstance(sfEvent.risk, int):
            raise TypeError(
                f"sfEvent.risk is {type(sfEvent.risk)}; expected int()") from None

        if not 0 <= sfEvent.risk <= 100:
            raise ValueError(
                f"sfEvent.risk value is {type(sfEvent.risk)}; expected 0 - 100") from None

        if not isinstance(sfEvent.sourceEvent, SpiderFootEvent) and sfEvent.eventType != "ROOT":
            raise TypeError(
                f"sfEvent.sourceEvent is {type(sfEvent.sourceEvent)}; expected str()") from None

        if not isinstance(sfEvent.sourceEventHash, str):
            raise TypeError(
                f"sfEvent.sourceEventHash is {type(sfEvent.sourceEventHash)}; expected str()") from None

        if not sfEvent.sourceEventHash:
            raise ValueError("sfEvent.sourceEventHash is empty") from None

        storeData = sfEvent.data

        # truncate if required
        if isinstance(truncateSize, int) and truncateSize > 0:
            storeData = storeData[0:truncateSize]

        # retrieve scan results
        qry = f"INSERT INTO tbl_scan_results \
            (scan_instance_id, hash, type, generated, confidence, \
            visibility, risk, module, data, source_event_hash) \
            VALUES ({self._placeholder(10)})"

        qvals = [instanceId, sfEvent.hash, sfEvent.eventType, sfEvent.generated,
                 sfEvent.confidence, sfEvent.visibility, sfEvent.risk,
                 sfEvent.module, storeData, sfEvent.sourceEventHash]

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvals)
                self.conn.commit()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    f"SQL error encountered when storing event data ({self.dbh})") from e

    def scanInstanceList(self) -> list:
        """List all previously run scans.

        Returns:
            list: previously run scans

        Raises:
            IOError: database I/O failed
        """

        # SQLite doesn't support OUTER JOINs, so we need a work-around that
        # does a UNION of scans with results and scans without results to
        # get a complete listing.
        qry = "SELECT i.guid, i.name, i.seed_target, ROUND(i.created/1000), \
            ROUND(i.started)/1000 as started, ROUND(i.ended)/1000, i.status, COUNT(r.type) \
            FROM tbl_scan_instance i, tbl_scan_results r WHERE i.guid = r.scan_instance_id \
            AND r.type <> 'ROOT' \
            GROUP BY i.guid, i.name, i.seed_target, i.created, i.started, i.ended, i.status \
            UNION ALL \
            SELECT i.guid, i.name, i.seed_target, ROUND(i.created/1000), \
            ROUND(i.started)/1000 as started, ROUND(i.ended)/1000, i.status, 0 \
            FROM tbl_scan_instance i WHERE i.guid NOT IN ( \
            SELECT distinct scan_instance_id FROM tbl_scan_results WHERE type <> 'ROOT') \
            ORDER BY started DESC"

        with self.dbhLock:
            try:
                self.dbh.execute(qry)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when fetching scan list") from e

    def scanResultHistory(self, instanceId: str) -> list:
        """History of data from the scan.

        Args:
            instanceId (str): scan instance ID

        Returns:
            list: scan data history

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        ph = self._placeholder()
        qry = f"SELECT TO_CHAR(TO_TIMESTAMP(generated/1000), 'HH24:MI D') AS hourmin, \
                type, COUNT(*) FROM tbl_scan_results \
                WHERE scan_instance_id = {ph} GROUP BY TO_CHAR(TO_TIMESTAMP(generated/1000), 'HH24:MI D'), type"
        qvars = [instanceId]

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    f"SQL error encountered when fetching history for scan {instanceId}") from e

    def scanElementSourcesDirect(self, instanceId: str, elementIdList: list) -> list:
        """Get the source IDs, types and data for a set of IDs.

        Args:
            instanceId (str): scan instance ID
            elementIdList (list): TBD

        Returns:
            list: TBD

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(elementIdList, list):
            raise TypeError(
                f"elementIdList is {type(elementIdList)}; expected list()") from None

        hashIds = []
        for hashId in elementIdList:
            if not hashId:
                continue
            if not hashId.isalnum():
                continue
            hashIds.append(hashId)

        # the output of this needs to be aligned with scanResultEvent,
        # as other functions call both expecting the same output.
        ph = self._placeholder()
        placeholders = ', '.join([ph] * len(hashIds))
        qry = f"SELECT ROUND(c.generated) AS generated, c.data, \
            s.data as source_data, \
            c.module, c.type, c.confidence, c.visibility, c.risk, c.hash, \
            c.source_event_hash, t.event_descr, t.event_type, s.scan_instance_id, \
            c.false_positive as fp, s.false_positive as parent_fp, \
            s.type, s.module, st.event_type as source_entity_type \
            FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t, \
            tbl_event_types st \
            WHERE c.scan_instance_id = {ph} AND c.source_event_hash = s.hash AND \
            s.scan_instance_id = c.scan_instance_id AND st.event = s.type AND \
            t.event = c.type AND c.hash IN ({placeholders})"
        qvars = [instanceId] + hashIds

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when getting source element IDs") from e

    def scanElementChildrenDirect(self, instanceId: str, elementIdList: list) -> list:
        """Get the child IDs, types and data for a set of IDs.

        Args:
            instanceId (str): scan instance ID
            elementIdList (list): TBD

        Returns:
            list: TBD

        Raises:
            TypeError: arg type was invalid
            IOError: database I/O failed
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()") from None

        if not isinstance(elementIdList, list):
            raise TypeError(
                f"elementIdList is {type(elementIdList)}; expected list()") from None

        hashIds = []
        for hashId in elementIdList:
            if not hashId:
                continue
            if not hashId.isalnum():
                continue
            hashIds.append(hashId)

        # the output of this needs to be aligned with scanResultEvent,
        # as other functions call both expecting the same output.
        ph = self._placeholder()
        placeholders = ', '.join([ph] * len(hashIds))
        qry = f"SELECT ROUND(c.generated) AS generated, c.data, \
            s.data as source_data, \
            c.module, c.type, c.confidence, c.visibility, c.risk, c.hash, \
            c.source_event_hash, t.event_descr, t.event_type, s.scan_instance_id, \
            c.false_positive as fp, s.false_positive as parent_fp \
            FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t \
            WHERE c.scan_instance_id = {ph} AND c.source_event_hash = s.hash AND \
            s.scan_instance_id = c.scan_instance_id AND \
            t.event = c.type AND s.hash IN ({placeholders})"
        qvars = [instanceId] + hashIds

        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError(
                    "SQL error encountered when getting child element IDs") from e

    def scanElementSourcesAll(self, instanceId: str, childData: list) -> list:
        """Get the full set of upstream IDs which are parents to the supplied
        set of IDs.

        Args:
            instanceId (str): scan instance ID
            childData (list): TBD

        Returns:
            list: TBD

        Raises:
            TypeError: arg type was invalid
            ValueError: arg value was invalid
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()")

        if not isinstance(childData, list):
            raise TypeError(f"childData is {type(childData)}; expected list()")

        if not childData:
            raise ValueError("childData is empty")

        # Get the first round of source IDs for the leafs
        keepGoing = True
        nextIds = list()
        datamap = dict()
        pc = dict()

        for row in childData:
            # these must be unique values!
            parentId = row[9]
            childId = row[8]
            datamap[childId] = row

            if parentId in pc:
                if childId not in pc[parentId]:
                    pc[parentId].append(childId)
            else:
                pc[parentId] = [childId]

            # parents of the leaf set
            if parentId not in nextIds:
                nextIds.append(parentId)

        while keepGoing:
            parentSet = self.scanElementSourcesDirect(instanceId, nextIds)
            nextIds = list()
            keepGoing = False

            for row in parentSet:
                parentId = row[9]
                childId = row[8]
                datamap[childId] = row

                if parentId in pc:
                    if childId not in pc[parentId]:
                        pc[parentId].append(childId)
                else:
                    pc[parentId] = [childId]
                if parentId not in nextIds:
                    nextIds.append(parentId)

                # Prevent us from looping at root
                if parentId != "ROOT":
                    keepGoing = True

        datamap[parentId] = row
        return [datamap, pc]

    def scanElementChildrenAll(self, instanceId: str, parentIds: list) -> list:
        """Get the full set of downstream IDs which are children of the
        supplied set of IDs.

        Args:
            instanceId (str): scan instance ID
            parentIds (list): TBD

        Returns:
            list: TBD

        Raises:
            TypeError: arg type was invalid

        Note: This function is not the same as the scanElementParent* functions.
              This function returns only ids.
        """

        if not isinstance(instanceId, str):
            raise TypeError(
                f"instanceId is {type(instanceId)}; expected str()")

        if not isinstance(parentIds, list):
            raise TypeError(f"parentIds is {type(parentIds)}; expected list()")

        datamap = list()
       
        keepGoing = True
        nextIds = list()

        nextSet = self.scanElementChildrenDirect(instanceId, parentIds)
        for row in nextSet:
            datamap.append(row[8])

        for row in nextSet:
            if row[8] not in nextIds:
                nextIds.append(row[8])

        while keepGoing:
            nextSet = self.scanElementChildrenDirect(instanceId, nextIds)
            if nextSet is None or len(nextSet) == 0:
                keepGoing = False
                break

            for row in nextSet:
                datamap.append(row[8])
                nextIds = list()
                nextIds.append(row[8])

        return datamap

    def correlationResultCreate(self, instanceId: str, event_hash: str, ruleId: str,
        ruleName: str,
        ruleDescr: str,
        ruleRisk: str,
        ruleYaml: str,
        correlationTitle: str, eventHashes: list
    ) -> str:
        """Create a correlation result in the database.

        Args:
            instanceId (str): scan instance ID
            event_hash (str): event hash
            ruleId (str): correlation rule ID
            ruleName (str): correlation rule name
            ruleDescr (str): correlation rule description
            ruleRisk (str): correlation rule risk level
            ruleYaml (str): correlation rule raw YAML
            correlationTitle (str): correlation title
            eventHashes (list): events mapped to the correlation result

        Returns:
            str: Correlation ID created

        Raises:
            IOError: database I/O failed
            TypeError: arg type was invalid        """
        import uuid
        correlation_id = str(uuid.uuid4())

        ph = self._placeholder()
        with self.dbhLock:
            try:
                # Ensure connection is alive
                if not self.conn:
                    raise IOError("Database connection is closed")
                    
                qry = f"INSERT INTO tbl_scan_correlation_results \
                    (id, scan_instance_id, title, rule_id, rule_risk, rule_name, \
                    rule_descr, rule_logic) \
                    VALUES ({self._placeholder(8)})"
                qvars = [correlation_id, instanceId, correlationTitle, ruleId, ruleRisk, ruleName, ruleDescr, ruleYaml]

                self.dbh.execute(qry, qvars)
                self.conn.commit()
                
                correlationId = correlation_id

                if isinstance(eventHashes, str):
                    eventHashes = [eventHashes]

                # Insert event hashes for this correlation
                event_insert_count = 0
                for eventHash in eventHashes:
                    qry = f"INSERT INTO tbl_scan_correlation_results_events (correlation_id, event_hash) VALUES ({ph}, {ph})"
                    qvars = [correlationId, eventHash]
                    try:
                        self.dbh.execute(qry, qvars)
                        event_insert_count += 1
                    except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                        print(f"[WARNING] Failed to insert correlation event {eventHash}: {e}")
                        continue  # Continue with other events instead of failing completely

                self.conn.commit()
                print(f"[INFO] Created correlation {correlationId} with {event_insert_count}/{len(eventHashes)} events")
                
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                print(f"[ERROR] SQL error creating correlation result: {e}")
                try:
                    self.conn.rollback()
                except:
                    pass
                raise IOError(f"Unable to create correlation result in database: {e}") from e
            except Exception as e:
                print(f"[ERROR] Unexpected error creating correlation result: {e}")
                try:
                    self.conn.rollback()
                except:
                    pass
                raise IOError(f"Unable to create correlation result in database: {e}") from e
        
        return str(correlationId)

    def get_sources(self, scan_id: str, event_hash: str) -> list:
        """Return the list of source events for a given event in a scan.

        Args:
            scan_id (str): The scan instance ID
            event_hash (str): The hash of the event whose sources to retrieve

        Returns:
            list: List of dicts with source event details (hash, type, data, module, etc.)
        """
        ph = self._placeholder()
        qry = f"""
            SELECT s.hash, s.type, s.data, s.module, s.generated, s.source_event_hash
            FROM tbl_scan_results c
            JOIN tbl_scan_results s
              ON c.source_event_hash = s.hash
            WHERE c.scan_instance_id = {ph}
              AND c.hash = {ph}
              AND c.source_event_hash != 'ROOT'
        """
        qvars = [scan_id, event_hash]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                rows = self.dbh.fetchall()
                sources = []
                for row in rows:
                    sources.append({
                        'hash': row[0],
                        'type': row[1],
                        'data': row[2],
                        'module': row[3],
                        'generated': row[4],
                        'source_event_hash': row[5]
                    })
                return sources
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError("SQL error encountered when fetching event sources") from e

    def get_entities(self, scan_id: str, event_hash: str) -> list:
        """Return the list of entity events that are children of a given event in a scan.

        Args:
            scan_id (str): The scan instance ID
            event_hash (str): The hash of the event whose child entities to retrieve

        Returns:
            list: List of dicts with entity event details (hash, type, data, module, etc.)
        """
        ph = self._placeholder()
        qry = f"""
            SELECT c.hash, c.type, c.data, c.module, c.generated, c.source_event_hash
            FROM tbl_scan_results c
            WHERE c.scan_instance_id = {ph}
              AND c.source_event_hash = {ph}
              AND c.type IN (
                SELECT event FROM tbl_event_types WHERE event_type = 'ENTITY'
              )
        """
        qvars = [scan_id, event_hash]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                rows = self.dbh.fetchall()
                entities = []
                for row in rows:
                    entities.append({
                        'hash': row[0],
                        'type': row[1],
                        'data': row[2],
                        'module': row[3],
                        'generated': row[4],
                        'source_event_hash': row[5]
                    })
                return entities
            except (Exception, psycopg2.Error if psycopg2 else Exception) as e:
                raise IOError("SQL error encountered when fetching entity events") from e