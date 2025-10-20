# Beryl AX Pineapple - Architecture Specification

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2025-10-20

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Component Specifications](#component-specifications)
4. [Data Flow](#data-flow)
5. [Security Architecture](#security-architecture)
6. [Resource Management](#resource-management)
7. [Deployment Models](#deployment-models)

---

## 1. Executive Summary

### 1.1 Purpose

Beryl AX Pineapple is a split-architecture security automation platform that combines:
- **Edge Device (GL.iNet Beryl AX MT-3000)**: Lightweight real-time network operations
- **Remote Host (Server/Laptop/VM)**: Heavy computational analysis and AI integration

### 1.2 Key Design Principles

1. **Resource-Aware**: Optimized for embedded device constraints (512MB RAM, 256MB flash)
2. **Security-First**: Authentication, input validation, least privilege throughout
3. **AI-Native**: Model Context Protocol (MCP) integration for Claude and other AI assistants
4. **Modular**: Clean separation between router and host components
5. **Observable**: Comprehensive logging, metrics, and telemetry

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GL.iNet Beryl AX (MT-3000)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   hostapd    │  │  dnsmasq     │  │  nodogsplash │          │
│  │  (WiFi AP)   │  │ (DHCP/DNS)   │  │   (Captive)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  tcpdump     │  │ Lua Collector│  │  init.d      │          │
│  │  (Capture)   │  │ (Telemetry)  │  │  (Services)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                           │                                      │
│                           │ HTTPS/SSH                            │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Remote Host (Server)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  FastAPI     │  │  MCP Server  │  │  PostgreSQL  │          │
│  │  (REST API)  │  │  (AI Bridge) │  │  (Database)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  nmap        │  │  bettercap   │  │  Scapy       │          │
│  │  gobuster    │  │  tshark      │  │  pyshark     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │  Prometheus  │  │  Grafana     │                            │
│  │  (Metrics)   │  │  (Dashboards)│                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

#### Router-Side (Beryl AX)

| Component | Purpose | Memory Budget | Criticality |
|-----------|---------|---------------|-------------|
| hostapd | WiFi AP management | ~8-20 MB | Critical |
| dnsmasq | DHCP/DNS services | ~5-10 MB | Critical |
| nodogsplash | Captive portal | ~8-20 MB | Optional |
| tcpdump | Packet capture | ~2-5 MB | High |
| Lua collector | Telemetry forwarding | ~2-6 MB | High |
| SSH daemon (dropbear) | Remote access | ~2-6 MB | Critical |

**Total Working Set:** ~80-160 MB (fits in 512MB with headroom)

#### Remote Host

| Component | Purpose | Dependencies | Port |
|-----------|---------|--------------|------|
| FastAPI | REST API | Python 3.11+, PostgreSQL | 8000 |
| MCP Server | AI integration | Python 3.11+, mcp library | 9000 |
| PostgreSQL | Data persistence | - | 5432 |
| Background Worker | Scan execution | nmap, gobuster, etc. | - |
| Prometheus | Metrics | - | 9090 |
| Grafana | Visualization | Prometheus | 3000 |

---

## 3. Component Specifications

### 3.1 Router-Side Components

#### 3.1.1 Lua Telemetry Collector

**Functional Requirements:**
- FR-LUA-001: Collect wireless probe requests every 10 seconds
- FR-LUA-002: Collect interface statistics (RX/TX bytes, packet counts)
- FR-LUA-003: Forward events to remote host via HTTPS POST
- FR-LUA-004: Queue events locally if network unavailable (max 100 events)
- FR-LUA-005: Identify router by MAC address

**Technical Requirements:**
- TR-LUA-001: Memory footprint < 10 MB
- TR-LUA-002: CPU usage < 5% average
- TR-LUA-003: Graceful degradation if remote unreachable
- TR-LUA-004: JSON payload format
- TR-LUA-005: API key authentication

**Dependencies:**
- lua (base)
- lua-cjson (JSON encoding)
- curl (HTTP client)

#### 3.1.2 PCAP Rotation Script

**Functional Requirements:**
- FR-PCAP-001: Capture packets on specified interface
- FR-PCAP-002: Rotate files every 10 MB (configurable)
- FR-PCAP-003: Keep maximum 10 files locally (circular buffer)
- FR-PCAP-004: Detect USB storage and prefer over /tmp
- FR-PCAP-005: Transfer completed files to remote via SCP
- FR-PCAP-006: Delete local files after successful transfer
- FR-PCAP-007: Notify remote API after transfer

**Technical Requirements:**
- TR-PCAP-001: USB detection via mountpoint check
- TR-PCAP-002: Fallback to /tmp if USB unavailable
- TR-PCAP-003: SCP with key-based authentication
- TR-PCAP-004: 32 GB USB budget assumption
- TR-PCAP-005: Process management via PID file
- TR-PCAP-006: Background offload daemon

**Dependencies:**
- tcpdump
- openssh (scp)
- kmod-usb-storage (optional)

#### 3.1.3 Init.d Service Manager

**Functional Requirements:**
- FR-INIT-001: Start/stop telemetry collector
- FR-INIT-002: Load configuration from UCI
- FR-INIT-003: Respawn on crash (with limits)
- FR-INIT-004: Validate configuration before start
- FR-INIT-005: Resource limit enforcement
- FR-INIT-006: Status reporting
- FR-INIT-007: Connection testing

**Technical Requirements:**
- TR-INIT-001: procd integration for process management
- TR-INIT-002: UCI configuration schema at /etc/config/beryl-mcp
- TR-INIT-003: Memory limit: 50 MB (enforced via procd)
- TR-INIT-004: Nice level: 10 (lower priority)
- TR-INIT-005: Syslog integration

### 3.2 Remote Host Components

#### 3.2.1 FastAPI REST API

**Functional Requirements:**
- FR-API-001: Authentication via JWT tokens
- FR-API-002: Router authentication via API keys
- FR-API-003: CRUD operations for scans
- FR-API-004: Telemetry ingestion endpoint
- FR-API-005: PCAP upload metadata registration
- FR-API-006: Health/readiness endpoints
- FR-API-007: Pagination for list endpoints
- FR-API-008: Rate limiting (60 req/min default)

**Technical Requirements:**
- TR-API-001: OpenAPI 3.0 schema (automatic via FastAPI)
- TR-API-002: CORS configuration
- TR-API-003: Security headers (HSTS, X-Frame-Options, etc.)
- TR-API-004: Async SQLAlchemy for database
- TR-API-005: Pydantic models for validation
- TR-API-006: Logging via loguru
- TR-API-007: Metrics exposition for Prometheus

**Security Requirements:**
- SR-API-001: TLS required in production
- SR-API-002: Input sanitization on all endpoints
- SR-API-003: Command injection prevention
- SR-API-004: Path traversal prevention
- SR-API-005: SQL injection prevention (via ORM)

#### 3.2.2 MCP Server

**Functional Requirements:**
- FR-MCP-001: Expose 7 security tools via MCP protocol
- FR-MCP-002: Input validation for all tool parameters
- FR-MCP-003: Async tool execution
- FR-MCP-004: Result streaming for long-running tasks
- FR-MCP-005: Error handling and reporting
- FR-MCP-006: AI-assisted report generation

**Technical Requirements:**
- TR-MCP-001: MCP protocol v1.0 compliance
- TR-MCP-002: Stdio transport (for AI assistant integration)
- TR-MCP-003: Tool timeout handling
- TR-MCP-004: Resource limits per tool

**Exposed Tools:**
1. `nmap_scan`: Port scanning
2. `capture_packets`: Packet capture control
3. `analyze_pcap`: PCAP analysis
4. `wireless_scan`: WiFi reconnaissance
5. `run_gobuster`: Directory enumeration
6. `get_router_telemetry`: Telemetry retrieval
7. `generate_report`: AI-generated reports

#### 3.2.3 Background Worker

**Functional Requirements:**
- FR-WORKER-001: Execute security scans asynchronously
- FR-WORKER-002: Parse tool output
- FR-WORKER-003: Extract findings and store in database
- FR-WORKER-004: Update scan status in real-time
- FR-WORKER-005: Handle tool failures gracefully
- FR-WORKER-006: Resource management (max 3 concurrent scans)

**Technical Requirements:**
- TR-WORKER-001: Celery or Python multiprocessing
- TR-WORKER-002: Tool output parsing (regex, JSON)
- TR-WORKER-003: Timeout enforcement
- TR-WORKER-004: Process isolation
- TR-WORKER-005: Signal handling (SIGTERM, SIGINT)

---

## 4. Data Flow

### 4.1 Telemetry Flow

```
Router → Lua Collector → HTTPS POST → FastAPI /api/router/telemetry → PostgreSQL
```

1. Lua collector detects probe request via `iw scan`
2. Event formatted as JSON
3. HTTP POST to remote host with API key
4. FastAPI validates and stores in `router_telemetry` table
5. Available for query via API or MCP

### 4.2 PCAP Flow

```
Router → tcpdump → Rotation → SCP → Remote Storage → API Notification → Database
```

1. tcpdump captures to `/mnt/usb/capture_XXXXXX.pcap`
2. File reaches 10 MB, rotation occurs
3. Offload daemon SCPs file to remote host
4. API notification registers metadata
5. File available for analysis

### 4.3 Scan Flow

```
API Request → Database Record → Worker Queue → Tool Execution → Result Parsing → Database Update
```

1. Client creates scan via `POST /api/scans`
2. Record created with status=PENDING
3. Worker picks up scan from queue
4. Tool executed with timeout
5. Output parsed, findings extracted
6. Status updated to COMPLETED/FAILED

---

## 5. Security Architecture

### 5.1 Authentication Layers

| Layer | Method | Purpose |
|-------|--------|---------|
| User → API | JWT Bearer Token | Human users accessing API |
| Router → API | X-API-Key Header | Router telemetry submission |
| API → Database | Password Auth | Database connection |
| Router → Remote | SSH Key | SCP file transfers |

### 5.2 Input Validation Strategy

1. **Target Validation**: IP address or domain via validators library
2. **Path Validation**: Prevent traversal via Path.resolve() checks
3. **Command Validation**: Allowlist pattern, no shell injection
4. **Filename Sanitization**: Alphanumeric + dash/underscore only

### 5.3 Principle of Least Privilege

- Router services run as `root` (required for packet capture)
- Remote API runs as non-root user (`appuser`)
- Database access via limited-privilege user
- Docker containers drop unnecessary capabilities

---

## 6. Resource Management

### 6.1 Router Resource Budgets

**Flash Storage (256 MB total):**
- Firmware: ~120-180 MB
- Packages: ~40-60 MB
- Free space: ~20-60 MB (for config, logs)

**RAM (512 MB total):**
- Base OS: ~40-80 MB
- Services: ~80-160 MB
- Kernel/cache: ~200 MB
- Free: ~100 MB (buffer)

**USB Storage (32 GB recommended):**
- PCAP circular buffer: ~100 MB (10 files × 10 MB)
- Logs: ~10 MB
- Free: ~31.9 GB

### 6.2 Remote Host Resource Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 50 GB
- Network: 100 Mbps

**Recommended:**
- CPU: 4+ cores
- RAM: 8 GB
- Disk: 500 GB SSD
- Network: 1 Gbps

---

## 7. Deployment Models

### 7.1 Lab/Development

- Router: Beryl AX on isolated network
- Remote Host: Docker Compose on laptop
- Database: SQLite (lightweight)
- Monitoring: Optional

### 7.2 Production

- Router: Beryl AX with USB storage
- Remote Host: VPS or dedicated server
- Database: PostgreSQL with replication
- Monitoring: Prometheus + Grafana
- TLS: Let's Encrypt certificates
- Backup: Automated daily backups

### 7.3 Multi-Router

- Multiple Beryl AX devices
- Centralized remote host
- Router identification via MAC address
- Load balancing for API

---

## 8. Future Enhancements

### 8.1 Planned Features

1. **Wireless Deauth Testing**: Controlled deauthentication for testing (ethical use only)
2. **Evil Twin Detection**: Identify rogue access points
3. **AI-Assisted Analysis**: GPT-4 integration for vulnerability assessment
4. **Mobile App**: React Native companion app
5. **Blockchain Logging**: Immutable audit trail

### 8.2 Optimization Opportunities

1. **Redis Caching**: Reduce database load
2. **WebSocket Support**: Real-time scan updates
3. **gRPC**: Higher performance router↔host communication
4. **eBPF**: Kernel-level packet filtering on router

---

**Next Steps:**
1. Review and approve this architecture
2. Create detailed implementation specs for each component
3. Build branch-by-branch guided by specs
4. Continuous integration and testing
