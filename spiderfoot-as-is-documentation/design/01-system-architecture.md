# SpiderFoot As-Is System Architecture Design

**Version:** 1.0
**Date:** 2025-11-02
**Status:** Documentation of Current System

---

## Table of Contents

1. [Overview](#overview)
2. [System Context](#system-context)
3. [High-Level Architecture](#high-level-architecture)
4. [Component Architecture](#component-architecture)
5. [Data Architecture](#data-architecture)
6. [Module System Architecture](#module-system-architecture)
7. [Event Processing Architecture](#event-processing-architecture)
8. [Correlation Engine Architecture](#correlation-engine-architecture)
9. [API Architecture](#api-architecture)
10. [Deployment Architecture](#deployment-architecture)
11. [Security Architecture](#security-architecture)

---

## Overview

SpiderFoot is an OSINT (Open Source Intelligence) automation platform that collects, correlates, and analyzes data from 277+ data sources. The system uses an event-driven, plugin-based architecture where modules consume and produce events in recursive chains, with parallel correlation analysis.

### Key Characteristics

- **Architecture Pattern:** Event-Driven, Plugin-Based
- **Language:** Python 3.11+
- **Web Framework:** CherryPy (Web UI) + FastAPI (REST API)
- **Database:** SQLite (default) / PostgreSQL (enterprise)
- **Modules:** 277 OSINT collection plugins
- **Correlation Rules:** 56+ YAML-based rules
- **Event Types:** 389 classified data types

---

## System Context

```mermaid
graph TB
    User[User/Analyst] -->|Web Browser| WebUI[Web UI :5001]
    User -->|CLI Commands| CLI[CLI Interface]
    User -->|HTTP/REST| API[REST API :8001]

    WebUI --> SpiderFoot[SpiderFoot Core]
    CLI --> SpiderFoot
    API --> SpiderFoot

    SpiderFoot -->|OSINT Queries| External[External Data Sources]
    SpiderFoot -->|Store Results| Database[(Database)]

    External -->|DNS| DNS[DNS Servers]
    External -->|Threat Intel| ThreatIntel[VirusTotal, Shodan, etc]
    External -->|Breach Data| BreachDB[HIBP, Dehashed]
    External -->|Social Media| Social[LinkedIn, Twitter]
    External -->|Search| Search[Google, Bing]

    style SpiderFoot fill:#4CAF50
    style Database fill:#2196F3
    style External fill:#FF9800
```

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "Entry Points"
        SF[sf.py<br/>Main Entry]
        SFCLI[sfcli.py<br/>CLI Interface]
        SFWEBUI[sfwebui.py<br/>Web UI Server]
        SFAPI[sfapi.py<br/>API Server]
    end

    subgraph "Orchestration Layer"
        ORCH[sf_orchestrator.py<br/>Modular Orchestrator]
        CONFMGR[ConfigManager]
        MODMGR[ModuleManager]
        SCANMGR[ScanManager]
        SRVMGR[ServerManager]
        VALMGR[ValidationUtils]
    end

    subgraph "Service Layer"
        WEBUI[Web UI Layer<br/>CherryPy]
        APILAY[API Layer<br/>FastAPI]
        SFLIB[SpiderFoot Core<br/>sflib/]
        DBLAY[Database Layer<br/>db/]
        SCANNER[Scan Service<br/>scanner.py]
    end

    subgraph "Plugin Layer"
        PLUGIN[SpiderFootPlugin<br/>Base Class]
        MOD1[sfp_dns]
        MOD2[sfp_whois]
        MOD3[sfp_shodan]
        MODN[277 Total Modules]
    end

    subgraph "Analysis Layer"
        CORR[Correlation Engine]
        RULES[56+ YAML Rules]
    end

    subgraph "Data Layer"
        DB[(SQLite/PostgreSQL)]
        CACHE[(Redis Cache)]
    end

    SF --> ORCH
    SFCLI --> ORCH
    SFWEBUI --> ORCH
    SFAPI --> ORCH

    ORCH --> CONFMGR
    ORCH --> MODMGR
    ORCH --> SCANMGR
    ORCH --> SRVMGR
    ORCH --> VALMGR

    CONFMGR --> SFLIB
    MODMGR --> SFLIB
    SCANMGR --> SCANNER

    WEBUI --> SFLIB
    APILAY --> SFLIB

    SFLIB --> DBLAY
    SCANNER --> DBLAY

    SCANNER --> PLUGIN
    PLUGIN --> MOD1
    PLUGIN --> MOD2
    PLUGIN --> MOD3
    PLUGIN --> MODN

    SCANNER --> CORR
    CORR --> RULES

    DBLAY --> DB
    SFLIB --> CACHE

    style ORCH fill:#4CAF50
    style SCANNER fill:#2196F3
    style PLUGIN fill:#FF9800
    style CORR fill:#9C27B0
```

---

## Component Architecture

### Core Components Detail

```mermaid
graph LR
    subgraph "SpiderFoot Core (sflib/core.py)"
        CORE[SpiderFoot Class]
        CORE_CONF[Configuration Management]
        CORE_NET[Network Utilities]
        CORE_MOD[Module Loading]
        CORE_EVT[Event Processing]
        CORE_VAL[Data Validation]
    end

    subgraph "Database Layer (db/)"
        DB_CORE[db_core.py<br/>Connection & Schema]
        DB_SCAN[db_scan.py<br/>ScanManager]
        DB_EVENT[db_event.py<br/>EventManager]
        DB_CONF[db_config.py<br/>ConfigManager]
        DB_CORR[db_correlation.py<br/>CorrelationManager]
    end

    subgraph "Scan Service"
        SCANNER[SpiderFootScanner]
        SCAN_ORCH[Scan Orchestration]
        SCAN_THREAD[Thread Pool]
        SCAN_QUEUE[Event Queue]
        SCAN_STATUS[Status Tracking]
    end

    CORE --> CORE_CONF
    CORE --> CORE_NET
    CORE --> CORE_MOD
    CORE --> CORE_EVT
    CORE --> CORE_VAL

    DB_CORE --> DB_SCAN
    DB_CORE --> DB_EVENT
    DB_CORE --> DB_CONF
    DB_CORE --> DB_CORR

    SCANNER --> SCAN_ORCH
    SCANNER --> SCAN_THREAD
    SCANNER --> SCAN_QUEUE
    SCANNER --> SCAN_STATUS

    CORE --> DB_CORE
    SCANNER --> DB_CORE

    style CORE fill:#4CAF50
    style DB_CORE fill:#2196F3
    style SCANNER fill:#FF9800
```

---

## Data Architecture

### Database Schema

```mermaid
erDiagram
    tbl_event_types ||--o{ tbl_scan_results : "defines"
    tbl_scan_instance ||--o{ tbl_scan_results : "contains"
    tbl_scan_instance ||--o{ tbl_scan_log : "tracks"
    tbl_scan_instance ||--o{ tbl_scan_config : "configures"
    tbl_scan_instance ||--o{ tbl_scan_correlation_results : "produces"
    tbl_scan_correlation_results ||--o{ tbl_scan_correlation_results_events : "maps"
    tbl_scan_results ||--o{ tbl_scan_correlation_results_events : "linked_to"

    tbl_event_types {
        string event string PK
        string event_descr
        string event_raw
        string event_type
    }

    tbl_scan_instance {
        string guid PK
        string name
        string scanTarget
        string targetType
        string scanStatus
        timestamp created
        timestamp started
        timestamp ended
    }

    tbl_scan_results {
        string scan_instance_id FK
        string hash PK
        string type FK
        datetime generated
        int confidence
        int visibility
        int risk
        string module
        string data
        string source_event_hash
    }

    tbl_scan_log {
        string scan_instance_id FK
        timestamp generated
        string component
        string type
        string message
    }

    tbl_scan_config {
        string scan_instance_id FK
        string component
        string opt
        string val
    }

    tbl_config {
        string scope
        string opt
        string val
    }

    tbl_scan_correlation_results {
        string scan_instance_id FK
        string rule_id
        timestamp created
        string title
        string risk
        string description
        text data
    }

    tbl_scan_correlation_results_events {
        string correlation_result_id FK
        string scan_result_id FK
    }
```

### Data Flow Architecture

```mermaid
flowchart TB
    subgraph "Input Layer"
        TARGET[Target Input]
        CONFIG[Configuration]
    end

    subgraph "Processing Layer"
        ROOT[ROOT Event<br/>Creation]
        QUEUE[Event Queue]
        DISPATCH[Event Dispatcher]
        MOD[Module Execution]
    end

    subgraph "Storage Layer"
        SCANDB[(Scan Instance<br/>tbl_scan_instance)]
        EVENTDB[(Events<br/>tbl_scan_results)]
        CORRDB[(Correlations<br/>tbl_scan_correlation_results)]
    end

    subgraph "Analysis Layer"
        CORR_ENG[Correlation Engine]
        RULE_EXEC[Rule Executor]
        ENRICH[Event Enricher]
    end

    subgraph "Output Layer"
        WEBUI[Web UI Display]
        API[API Response]
        EXPORT[Export Files]
    end

    TARGET --> ROOT
    CONFIG --> ROOT
    ROOT --> QUEUE
    ROOT --> SCANDB

    QUEUE --> DISPATCH
    DISPATCH --> MOD
    MOD -->|New Events| QUEUE
    MOD -->|Store| EVENTDB

    EVENTDB --> CORR_ENG
    CORR_ENG --> RULE_EXEC
    RULE_EXEC --> ENRICH
    ENRICH --> CORRDB

    SCANDB --> WEBUI
    EVENTDB --> WEBUI
    CORRDB --> WEBUI

    SCANDB --> API
    EVENTDB --> API
    CORRDB --> API

    EVENTDB --> EXPORT
    CORRDB --> EXPORT

    style ROOT fill:#4CAF50
    style QUEUE fill:#FF9800
    style CORR_ENG fill:#9C27B0
```

---

## Module System Architecture

### Plugin Architecture

```mermaid
classDiagram
    class SpiderFootPlugin {
        <<abstract>>
        +meta: dict
        +opts: dict
        +sf: SpiderFoot
        +__init__(sf: SpiderFoot)
        +setup(sfc: SpiderFoot, userOpts: dict)
        +enrichTarget(target: string) string
        +watchedEvents() list
        +producedEvents() list
        +handleEvent(event: SpiderFootEvent)*
        +checkForStop() bool
        +notifyListeners(event: SpiderFootEvent)
    }

    class sfp_dns {
        +meta: dict
        +opts: dict
        +watchedEvents() list
        +producedEvents() list
        +handleEvent(event: SpiderFootEvent)
    }

    class sfp_whois {
        +meta: dict
        +opts: dict
        +watchedEvents() list
        +producedEvents() list
        +handleEvent(event: SpiderFootEvent)
    }

    class sfp_shodan {
        +meta: dict
        +opts: dict
        +watchedEvents() list
        +producedEvents() list
        +handleEvent(event: SpiderFootEvent)
    }

    class SpiderFootEvent {
        +eventType: string
        +data: string
        +module: string
        +sourceEvent: SpiderFootEvent
        +confidence: int
        +visibility: int
        +risk: int
        +hash: string
        +__init__(eventType, data, module, sourceEvent)
        +asDict() dict
    }

    SpiderFootPlugin <|-- sfp_dns
    SpiderFootPlugin <|-- sfp_whois
    SpiderFootPlugin <|-- sfp_shodan
    SpiderFootPlugin --> SpiderFootEvent : produces
```

### Event Chain Flow

```mermaid
flowchart TB
    ROOT[ROOT Event<br/>example.com]

    subgraph "DNS Module Chain"
        DNS[sfp_dnsresolve<br/>watches: DOMAIN_NAME]
        IP[Event: IP_ADDRESS<br/>1.2.3.4]
    end

    subgraph "IP Analysis Chain"
        GEO[sfp_geoip<br/>watches: IP_ADDRESS]
        GEO_EVT[Event: GEOINFO]

        BGP[sfp_bgpinfo<br/>watches: IP_ADDRESS]
        BGP_EVT[Event: BGP_AS_MEMBER]

        SHODAN[sfp_shodan<br/>watches: IP_ADDRESS]
        SHODAN_EVT[Event: TCP_PORT_OPEN]
    end

    subgraph "Port Analysis Chain"
        PORT[sfp_portscan_tcp<br/>watches: TCP_PORT_OPEN]
        BANNER[Event: TCP_PORT_OPEN_BANNER]
    end

    subgraph "WHOIS Chain"
        WHOIS[sfp_whois<br/>watches: DOMAIN_NAME]
        WHOIS_EVT[Event: DOMAIN_WHOIS]

        EMAIL[sfp_email<br/>watches: DOMAIN_WHOIS]
        EMAIL_EVT[Event: EMAILADDR]

        HIBP[sfp_haveibeenpwned<br/>watches: EMAILADDR]
        HIBP_EVT[Event: EMAILADDR_COMPROMISED]
    end

    ROOT --> DNS
    DNS --> IP

    IP --> GEO
    GEO --> GEO_EVT

    IP --> BGP
    BGP --> BGP_EVT

    IP --> SHODAN
    SHODAN --> SHODAN_EVT

    SHODAN_EVT --> PORT
    PORT --> BANNER

    ROOT --> WHOIS
    WHOIS --> WHOIS_EVT

    WHOIS_EVT --> EMAIL
    EMAIL --> EMAIL_EVT

    EMAIL_EVT --> HIBP
    HIBP --> HIBP_EVT

    style ROOT fill:#4CAF50
    style IP fill:#2196F3
    style SHODAN_EVT fill:#FF9800
    style HIBP_EVT fill:#F44336
```

---

## Event Processing Architecture

### Scan Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant ScanManager
    participant Scanner
    participant ModulePool
    participant EventQueue
    participant Database

    User->>WebUI: Start Scan (target, config)
    WebUI->>ScanManager: create_scan(target, modules)
    ScanManager->>Database: INSERT scan_instance
    ScanManager->>Scanner: __init__(scanId, target, ...)

    Scanner->>ModulePool: Load & instantiate modules
    ModulePool-->>Scanner: 277 modules ready

    Scanner->>EventQueue: Add ROOT event
    Scanner->>Database: Store ROOT event

    loop Event Processing
        Scanner->>EventQueue: Pop event
        Scanner->>ModulePool: Dispatch to interested modules

        par Parallel Module Execution
            ModulePool->>Module1: handleEvent(event)
            Module1->>Database: Store results
            Module1->>EventQueue: Add new events
        and
            ModulePool->>Module2: handleEvent(event)
            Module2->>Database: Store results
            Module2->>EventQueue: Add new events
        and
            ModulePool->>Module3: handleEvent(event)
            Module3->>Database: Store results
            Module3->>EventQueue: Add new events
        end

        Scanner->>Scanner: Check queue empty + modules done
    end

    Scanner->>Database: UPDATE status=FINISHED
    Scanner-->>User: Scan Complete
```

### Thread Pool Management

```mermaid
flowchart TB
    subgraph "Scanner Thread Pool"
        MAIN[Main Scanner Thread]
        QUEUE[Event Queue<br/>Thread-Safe]

        subgraph "Worker Threads"
            T1[Thread 1<br/>Module Executor]
            T2[Thread 2<br/>Module Executor]
            T3[Thread 3<br/>Module Executor]
            TN[Thread N<br/>configurable]
        end

        STATUS[Status Monitor]
    end

    MAIN --> QUEUE
    QUEUE --> T1
    QUEUE --> T2
    QUEUE --> T3
    QUEUE --> TN

    T1 -->|New Events| QUEUE
    T2 -->|New Events| QUEUE
    T3 -->|New Events| QUEUE
    TN -->|New Events| QUEUE

    T1 --> STATUS
    T2 --> STATUS
    T3 --> STATUS
    TN --> STATUS

    STATUS -->|All Done| MAIN

    style QUEUE fill:#FF9800
    style STATUS fill:#4CAF50
```

---

## Correlation Engine Architecture

### Correlation Processing

```mermaid
flowchart TB
    subgraph "Input"
        EVENTS[Scan Events<br/>tbl_scan_results]
    end

    subgraph "Correlation Engine"
        LOADER[Rule Loader<br/>Load YAML Rules]
        RULES[56+ Rules<br/>correlations/*.yml]

        subgraph "Processing Pipeline"
            COLLECT[Collection Phase<br/>Filter events by rules]
            ENRICH[Enrichment Phase<br/>Add context]
            ANALYZE[Analysis Phase<br/>threshold/outlier/first_only]
            AGGREGATE[Aggregation Phase<br/>Group by field]
        end

        EXECUTOR[Rule Executor<br/>Execute analysis logic]
    end

    subgraph "Output"
        CORR_RESULTS[Correlation Results<br/>tbl_scan_correlation_results]
        EVENT_MAP[Event Mapping<br/>tbl_scan_correlation_results_events]
    end

    EVENTS --> LOADER
    LOADER --> RULES
    RULES --> COLLECT

    COLLECT --> ENRICH
    ENRICH --> ANALYZE
    ANALYZE --> AGGREGATE

    AGGREGATE --> EXECUTOR
    EXECUTOR --> CORR_RESULTS
    EXECUTOR --> EVENT_MAP

    style COLLECT fill:#4CAF50
    style ANALYZE fill:#FF9800
    style CORR_RESULTS fill:#9C27B0
```

### Correlation Rule Structure

```mermaid
classDiagram
    class CorrelationRule {
        +id: string
        +version: int
        +meta: RuleMeta
        +collections: Collections
        +aggregation: Aggregation
        +analysis: Analysis
        +headline: string
    }

    class RuleMeta {
        +name: string
        +description: string
        +risk: string [INFO|LOW|MEDIUM|HIGH]
        +created: date
        +updated: date
    }

    class Collections {
        +collect: list[CollectionFilter]
    }

    class CollectionFilter {
        +method: string [exact|regex]
        +field: string [type|data|module]
        +value: string
    }

    class Aggregation {
        +field: string
    }

    class Analysis {
        +method: string [threshold|outlier|first_collection_only]
        +threshold: int
        +compare: string
        +outlier_method: string
        +enable_external_checks: bool
    }

    CorrelationRule --> RuleMeta
    CorrelationRule --> Collections
    CorrelationRule --> Aggregation
    CorrelationRule --> Analysis
    Collections --> CollectionFilter
```

---

## API Architecture

### REST API Structure

```mermaid
graph TB
    subgraph "API Entry Point"
        FASTAPI[FastAPI Application<br/>:8001]
    end

    subgraph "API Routes"
        SCAN_ROUTES[/api/scan/*<br/>Scan Management]
        RESULT_ROUTES[/api/results/*<br/>Result Retrieval]
        MODULE_ROUTES[/api/modules<br/>Module Info]
        CONFIG_ROUTES[/api/config<br/>Configuration]
        WORKSPACE_ROUTES[/api/workspaces/*<br/>Workspace Mgmt]
    end

    subgraph "WebSocket"
        WS[/ws/scan/:id<br/>Real-time Events]
    end

    subgraph "Service Layer"
        SCAN_SVC[Scan Service]
        DB_SVC[Database Service]
        CONFIG_SVC[Config Service]
    end

    subgraph "Documentation"
        SWAGGER[/api/docs<br/>Swagger UI]
        REDOC[/api/redoc<br/>ReDoc]
    end

    FASTAPI --> SCAN_ROUTES
    FASTAPI --> RESULT_ROUTES
    FASTAPI --> MODULE_ROUTES
    FASTAPI --> CONFIG_ROUTES
    FASTAPI --> WORKSPACE_ROUTES
    FASTAPI --> WS

    SCAN_ROUTES --> SCAN_SVC
    RESULT_ROUTES --> DB_SVC
    MODULE_ROUTES --> CONFIG_SVC
    CONFIG_ROUTES --> CONFIG_SVC
    WORKSPACE_ROUTES --> DB_SVC

    FASTAPI --> SWAGGER
    FASTAPI --> REDOC

    style FASTAPI fill:#4CAF50
    style WS fill:#FF9800
```

### API Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Middleware
    participant Router
    participant Service
    participant Database

    Client->>FastAPI: POST /api/scan/start
    FastAPI->>Middleware: Security Check

    alt Authentication Enabled
        Middleware->>Middleware: Verify JWT Token
        Middleware->>Middleware: Rate Limiting
        Middleware->>Middleware: Input Validation
    end

    Middleware->>Router: Route to Handler
    Router->>Service: start_scan(target, modules)
    Service->>Database: Create scan instance
    Database-->>Service: scan_id
    Service->>Service: Start scan thread
    Service-->>Router: {"scan_id": "xxx", "status": "STARTING"}
    Router-->>FastAPI: JSON Response
    FastAPI-->>Client: 200 OK + scan_id

    Note over Client,Database: WebSocket for real-time updates

    Client->>FastAPI: WS /ws/scan/:id
    FastAPI->>Service: Subscribe to scan events

    loop Event Stream
        Service->>FastAPI: New event
        FastAPI->>Client: Push event
    end
```

---

## Deployment Architecture

### Docker Architecture

```mermaid
graph TB
    subgraph "Docker Container"
        subgraph "Application Layer"
            WEBUI_PROC[Web UI Process<br/>CherryPy :5001]
            API_PROC[API Process<br/>FastAPI :8001]
        end

        subgraph "Service Layer"
            SF_CORE[SpiderFoot Core]
            MODULES[277 Modules]
        end

        subgraph "External Tools"
            NUCLEI[Nuclei]
            DNSTWIST[DNStwist]
            TESTSSL[testssl.sh]
            NMAP[Nmap]
            WHATWEB[WhatWeb]
        end

        subgraph "Volumes"
            DATA[/home/spiderfoot/data<br/>Database]
            LOGS[/home/spiderfoot/logs<br/>Logs]
            CACHE[/home/spiderfoot/cache<br/>Module Cache]
        end
    end

    subgraph "External Services"
        POSTGRES[(PostgreSQL<br/>Optional)]
        REDIS[(Redis<br/>Optional)]
    end

    subgraph "Reverse Proxy"
        NGINX[Nginx]
    end

    USER[Users] --> NGINX
    NGINX --> WEBUI_PROC
    NGINX --> API_PROC

    WEBUI_PROC --> SF_CORE
    API_PROC --> SF_CORE

    SF_CORE --> MODULES
    MODULES --> NUCLEI
    MODULES --> DNSTWIST
    MODULES --> TESTSSL
    MODULES --> NMAP
    MODULES --> WHATWEB

    SF_CORE --> DATA
    SF_CORE --> LOGS
    SF_CORE --> CACHE

    SF_CORE -.->|Optional| POSTGRES
    SF_CORE -.->|Optional| REDIS

    style SF_CORE fill:#4CAF50
    style DATA fill:#2196F3
    style POSTGRES fill:#2196F3
```

### Multi-Process Architecture

```mermaid
flowchart TB
    subgraph "Process Architecture"
        MAIN[Main Process<br/>sf_orchestrator]

        subgraph "Server Processes"
            WEBUI[Web UI Server<br/>CherryPy Process]
            API[API Server<br/>FastAPI Process]
        end

        subgraph "Scan Processes"
            SCAN1[Scan Worker 1]
            SCAN2[Scan Worker 2]
            SCANN[Scan Worker N]
        end

        subgraph "Background Processes"
            CORR[Correlation Worker]
            LOG[Log Listener]
        end
    end

    subgraph "IPC Mechanisms"
        QUEUE[Multiprocessing Queue<br/>Logging]
        SHARED[Shared Memory<br/>Config]
    end

    MAIN --> WEBUI
    MAIN --> API
    MAIN --> SCAN1
    MAIN --> SCAN2
    MAIN --> SCANN
    MAIN --> CORR
    MAIN --> LOG

    WEBUI --> QUEUE
    API --> QUEUE
    SCAN1 --> QUEUE
    SCAN2 --> QUEUE
    SCANN --> QUEUE
    CORR --> QUEUE

    QUEUE --> LOG

    MAIN --> SHARED
    WEBUI --> SHARED
    API --> SHARED

    style MAIN fill:#4CAF50
    style QUEUE fill:#FF9800
```

---

## Security Architecture

### Security Layers

```mermaid
graph TB
    subgraph "Network Layer"
        NGINX[Nginx Reverse Proxy<br/>SSL/TLS Termination]
        WAF[WAF Rules]
    end

    subgraph "Application Layer"
        subgraph "Input Security"
            VAL[Input Validation<br/>jsonschema]
            SANIT[Sanitization<br/>bleach]
        end

        subgraph "Authentication & Authorization"
            JWT[JWT Authentication<br/>python-jose]
            SESSION[Session Management<br/>Secure cookies]
            BCRYPT[Password Hashing<br/>bcrypt]
        end

        subgraph "Request Security"
            CSRF[CSRF Protection<br/>Token-based]
            RATE[Rate Limiting<br/>SlowAPI]
        end

        subgraph "Response Security"
            HEADERS[Security Headers<br/>secure library]
            CSP[Content Security Policy]
        end
    end

    subgraph "Data Layer"
        ENCRYPT[Data Encryption<br/>cryptography]
        SQL[SQL Injection Prevention<br/>Parameterized Queries]
    end

    subgraph "Monitoring Layer"
        SECLOG[Security Logging]
        AUDIT[Audit Trail]
        ALERT[Security Alerts]
    end

    NGINX --> WAF
    WAF --> VAL
    VAL --> SANIT
    SANIT --> JWT
    JWT --> SESSION
    SESSION --> CSRF
    CSRF --> RATE
    RATE --> HEADERS
    HEADERS --> CSP

    BCRYPT --> SESSION

    SQL --> ENCRYPT

    VAL --> SECLOG
    JWT --> SECLOG
    CSRF --> SECLOG
    RATE --> SECLOG

    SECLOG --> AUDIT
    AUDIT --> ALERT

    style CSRF fill:#F44336
    style JWT fill:#4CAF50
    style SECLOG fill:#FF9800
```

### Security Configuration Flow

```mermaid
flowchart LR
    subgraph "Security Settings"
        CSRF_EN[CSRF Enabled]
        RATE_EN[Rate Limiting]
        AUTH_EN[API Authentication]
        INPUT_EN[Input Validation]
        SESSION_EN[Session Security]
        HEADERS_EN[Security Headers]
    end

    subgraph "Middleware Stack"
        M1[Security Headers Middleware]
        M2[CSRF Middleware]
        M3[Rate Limiting Middleware]
        M4[Authentication Middleware]
        M5[Input Validation Middleware]
        M6[Session Middleware]
    end

    HEADERS_EN -->|Enable| M1
    CSRF_EN -->|Enable| M2
    RATE_EN -->|Enable| M3
    AUTH_EN -->|Enable| M4
    INPUT_EN -->|Enable| M5
    SESSION_EN -->|Enable| M6

    M1 --> M2
    M2 --> M3
    M3 --> M4
    M4 --> M5
    M5 --> M6
    M6 --> APP[Application Routes]

    style M4 fill:#4CAF50
    style M2 fill:#F44336
    style APP fill:#2196F3
```

---

## Technology Stack Summary

```mermaid
graph TB
    subgraph "Frontend"
        HTML[HTML/Mako Templates]
        CSS[Bootstrap CSS]
        JS[jQuery + D3.js + Sigma.js]
    end

    subgraph "Backend"
        PYTHON[Python 3.11+]
        CHERRYPY[CherryPy 18.10.0]
        FASTAPI[FastAPI + Uvicorn]
    end

    subgraph "Data"
        SQLITE[SQLite 3]
        POSTGRES[PostgreSQL<br/>Optional]
        REDIS[Redis<br/>Optional]
    end

    subgraph "Libraries"
        DNS[dnspython]
        HTTP[requests + httpx]
        CRYPTO[cryptography]
        PARSE[beautifulsoup4]
    end

    subgraph "Infrastructure"
        DOCKER[Docker]
        NGINX_INF[Nginx]
    end

    JS --> PYTHON
    HTML --> CHERRYPY
    CSS --> CHERRYPY

    CHERRYPY --> PYTHON
    FASTAPI --> PYTHON

    PYTHON --> SQLITE
    PYTHON --> POSTGRES
    PYTHON --> REDIS

    PYTHON --> DNS
    PYTHON --> HTTP
    PYTHON --> CRYPTO
    PYTHON --> PARSE

    DOCKER --> NGINX_INF
    NGINX_INF --> CHERRYPY
    NGINX_INF --> FASTAPI

    style PYTHON fill:#4CAF50
    style SQLITE fill:#2196F3
```

---

## Design Patterns

### Pattern Usage

1. **Plugin/Strategy Pattern**: Module system with pluggable OSINT collectors
2. **Observer Pattern**: Event-driven architecture with event listeners
3. **Factory Pattern**: Module instantiation and configuration
4. **Chain of Responsibility**: Event chain processing through modules
5. **Facade Pattern**: SpiderFoot core class as unified interface
6. **Repository Pattern**: Database layer abstraction (SQLite/PostgreSQL)
7. **Command Pattern**: CLI command processing
8. **Singleton Pattern**: Configuration management
9. **Producer-Consumer Pattern**: Event queue processing
10. **Template Method Pattern**: SpiderFootPlugin base class

---

## Performance Characteristics

- **Concurrency**: Configurable thread pool (default: 3 threads)
- **Scalability**: Horizontal via multiple scan workers
- **Caching**: Redis support for API responses
- **Database**: PostgreSQL for large deployments
- **Async**: FastAPI async endpoints for API layer
- **Queue**: Thread-safe event queue with backpressure

---

## Conclusion

The SpiderFoot architecture is designed as a modular, event-driven OSINT automation platform. Key strengths include:

- **Modularity**: 277 pluggable modules
- **Extensibility**: Easy to add new modules and correlation rules
- **Flexibility**: Multiple interfaces (Web UI, CLI, API)
- **Scalability**: Multi-process, multi-threaded architecture
- **Security**: Comprehensive security layers
- **Analysis**: Automated correlation and pattern detection

The system follows clean separation of concerns with orchestration, service, plugin, and data layers clearly defined.
