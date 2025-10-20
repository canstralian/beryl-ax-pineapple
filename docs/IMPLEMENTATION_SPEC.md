# Beryl AX Pineapple - Implementation Specification

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2025-10-20

## Table of Contents

1. [Configuration Files](#1-configuration-files)
2. [Router Scripts](#2-router-scripts)
3. [Firmware Components](#3-firmware-components)
4. [Testing Framework](#4-testing-framework)
5. [Deployment Procedures](#5-deployment-procedures)
6. [Implementation Roadmap](#6-implementation-roadmap)

---

## 1. Configuration Files

### 1.1 UCI Configuration Schema

**File:** `/etc/config/beryl-mcp`

```uci
config collector 'collector'
    option enabled '1'
    option remote_host '192.168.1.100'
    option remote_port '8000'
    option api_key 'CHANGE_THIS_SECURE_API_KEY'
    option monitor_interface 'wlan0'
    option scan_interval '10'
    option batch_size '20'
    option max_queue_size '100'
    option log_level 'INFO'

config capture 'capture'
    option enabled '1'
    option interface 'wlan0'
    option size_mb '10'
    option count '10'
    option filter ''
    option auto_offload '1'

config security 'security'
    option ssh_key_path '/root/.ssh/beryl_key'
    option require_tls '1'
    option validate_cert '1'

config features 'features'
    option probe_collection '1'
    option beacon_spoofing '0'
    option deauth_testing '0'
    option packet_capture '1'
```

**Implementation Tasks:**
- [ ] Create UCI schema definition file
- [ ] Write validation functions in Lua
- [ ] Create LuCI web UI integration (optional)
- [ ] Document configuration options

### 1.2 Network Configuration

**File:** `/etc/config/network` (additions)

```uci
config interface 'beryl_mon'
    option proto 'none'
    option device 'wlan0'
    option ifname 'wlan0'

config route 'beryl_route'
    option interface 'wan'
    option target '0.0.0.0'
    option netmask '0.0.0.0'
    option gateway '192.168.1.1'
```

### 1.3 Firewall Rules

**File:** `/etc/config/firewall` (additions)

```uci
# Allow outbound HTTPS to remote host
config rule
    option name 'Allow Beryl Telemetry'
    option src 'lan'
    option dest 'wan'
    option dest_ip '192.168.1.100'
    option dest_port '8000 22'
    option proto 'tcp'
    option target 'ACCEPT'

# Block unauthorized access to router
config rule
    option name 'Block External SSH'
    option src 'wan'
    option dest_port '22'
    option proto 'tcp'
    option target 'REJECT'
```

### 1.4 Environment Configuration Templates

**File:** `deployment/openwrt/router.env.example`

```bash
# Router-side environment configuration
export BERYL_REMOTE_HOST="192.168.1.100"
export BERYL_REMOTE_PORT="8000"
export BERYL_API_KEY="your-api-key-here"
export BERYL_SSH_KEY="/root/.ssh/beryl_key"
export BERYL_CAPTURE_SIZE_MB="10"
export BERYL_CAPTURE_COUNT="10"
export BERYL_LOG_LEVEL="INFO"
```

---

## 2. Router Scripts

### 2.1 Installation Script

**File:** `deployment/openwrt/install.sh`

**Purpose:** Automated installation of all router components

**Functional Requirements:**
- FR-INST-001: Detect router model and validate compatibility
- FR-INST-002: Check available flash/RAM space
- FR-INST-003: Install required opkg packages
- FR-INST-004: Copy scripts to appropriate locations
- FR-INST-005: Generate SSH keys if not present
- FR-INST-006: Configure UCI settings interactively or from file
- FR-INST-007: Create systemd/procd service
- FR-INST-008: Validate installation
- FR-INST-009: Create backup of original configuration

**Pseudo-code:**
```bash
#!/bin/sh
# Installation flow
1. Pre-flight checks
   - Verify router model (GL.iNet Beryl AX)
   - Check OpenWrt version (23.05+)
   - Verify flash space (> 20 MB free)
   - Verify RAM (> 100 MB free)

2. Backup existing configuration
   - /etc/config/* → /root/backup-TIMESTAMP/

3. Install dependencies
   - opkg update
   - opkg install lua lua-cjson tcpdump curl openssh-sftp-server

4. Deploy components
   - Copy telemetry_collector.lua → /usr/local/lib/lua/
   - Copy pcap_rotation.sh → /usr/local/bin/
   - Copy beryl-collector.init → /etc/init.d/
   - Chmod +x all scripts

5. Generate SSH keys
   - ssh-keygen -t ed25519 -f /root/.ssh/beryl_key -N ""
   - Display public key for user to add to remote host

6. Configure UCI
   - Interactive prompts for remote_host, api_key
   - Write to /etc/config/beryl-mcp

7. Enable services
   - /etc/init.d/beryl-collector enable
   - /etc/init.d/beryl-collector start

8. Validation
   - Test connectivity to remote host
   - Check service status
   - View initial logs

9. Print summary
   - Service status
   - Next steps
   - Troubleshooting tips
```

**Implementation Tasks:**
- [ ] Write install.sh with error handling
- [ ] Create pre-flight check functions
- [ ] Implement interactive configuration wizard
- [ ] Add rollback capability on failure
- [ ] Create post-install verification tests

### 2.2 Update Script

**File:** `deployment/openwrt/update.sh`

**Purpose:** Update existing installation without losing configuration

**Functional Requirements:**
- FR-UPD-001: Check current version
- FR-UPD-002: Download new version
- FR-UPD-003: Backup current installation
- FR-UPD-004: Stop services
- FR-UPD-005: Replace binaries
- FR-UPD-006: Restart services
- FR-UPD-007: Rollback on failure

### 2.3 Diagnostic Script

**File:** `deployment/openwrt/diagnostics.sh`

**Purpose:** Collect diagnostic information for troubleshooting

**Outputs:**
- System information (model, version, uptime)
- Resource usage (CPU, RAM, flash, USB)
- Service status (all beryl services)
- Network connectivity (ping remote host)
- Log files (last 100 lines)
- Configuration (sanitized, no secrets)
- Recent telemetry events (count)
- Recent PCAPs (list, sizes)

**Implementation Tasks:**
- [ ] Create comprehensive diagnostic collection
- [ ] Sanitize sensitive data (API keys, passwords)
- [ ] Generate markdown or JSON output
- [ ] Add option to upload diagnostics to remote host

### 2.4 Health Check Script

**File:** `src/router/scripts/health_check.sh`

**Purpose:** Periodic health monitoring (cron job)

**Checks:**
- Memory usage < 90%
- Flash usage < 80%
- USB mounted (if expected)
- Services running
- Remote host reachable
- Log file sizes < 1 MB

**Actions on Failure:**
- Restart service if crashed
- Rotate logs if too large
- Send alert to remote host

---

## 3. Firmware Components

### 3.1 Custom OpenWrt Build (Optional)

**Purpose:** Create custom firmware image with pre-installed components

**Benefits:**
- Single-flash installation
- Smaller footprint (remove unused packages)
- Consistent deployment across multiple routers

**Build Process:**
```bash
# Clone OpenWrt ImageBuilder
git clone https://github.com/openwrt/imagebuilder.git
cd imagebuilder

# Configure for MT-3000
make menuconfig  # Select GL.iNet Beryl AX target

# Add packages
PACKAGES="lua lua-cjson tcpdump-mini curl openssh-sftp-server"

# Add custom files
mkdir -p files/usr/local/lib/lua/
cp ../src/router/lua/telemetry_collector.lua files/usr/local/lib/lua/

mkdir -p files/etc/init.d/
cp ../src/router/config/beryl-collector.init files/etc/init.d/beryl-collector

# Build image
make image PROFILE=glinet_beryl-ax PACKAGES="$PACKAGES" FILES=files/

# Output: bin/targets/mediatek/mt7981/openwrt-*-beryl-ax-squashfs-sysupgrade.bin
```

**Implementation Tasks:**
- [ ] Create ImageBuilder configuration
- [ ] Test custom build on physical device
- [ ] Document build process
- [ ] Create automated build pipeline (GitHub Actions)
- [ ] Version and release firmware images

### 3.2 Package Feed

**Purpose:** Host custom packages for easy installation via opkg

**Structure:**
```
beryl-ax-pineapple-feed/
├── Makefile
├── packages/
│   ├── beryl-collector/
│   │   ├── Makefile
│   │   └── files/
│   └── beryl-scripts/
│       ├── Makefile
│       └── files/
```

**Implementation Tasks:**
- [ ] Create package Makefiles
- [ ] Set up package signing
- [ ] Host feed on GitHub Pages or CDN
- [ ] Document package installation
- [ ] Create update mechanism

---

## 4. Testing Framework

### 4.1 Unit Tests

**Router-Side (Lua):**

**File:** `tests/router/test_telemetry_collector.lua`

```lua
-- Test framework: busted (opkg install lua-busted)
describe("Telemetry Collector", function()
    describe("Event Queue", function()
        it("should add events to queue", function()
            local event = {event_type = "probe", data = {}}
            add_event(event)
            assert.equals(1, #event_queue)
        end)

        it("should prevent queue overflow", function()
            for i = 1, 150 do
                add_event({event_type = "test", data = {}})
            end
            assert.is_true(#event_queue <= 100)
        end)
    end)

    describe("JSON Encoding", function()
        it("should encode events correctly", function()
            local event = {event_type = "probe", data = {ssid = "Test"}}
            local json = json.encode(event)
            assert.is_not_nil(json:match('"event_type"'))
        end)
    end)
end)
```

**Implementation Tasks:**
- [ ] Set up busted test framework
- [ ] Write unit tests for all Lua functions
- [ ] Create test fixtures
- [ ] Automate test execution

**Remote Host (Python):**

**File:** `tests/unit/test_security_validation.py`

```python
import pytest
from remote_host.security.validation import validate_ip_address, validate_target

def test_validate_ip_address_valid():
    assert validate_ip_address("192.168.1.1") == "192.168.1.1"
    assert validate_ip_address("::1") == "::1"

def test_validate_ip_address_invalid():
    with pytest.raises(HTTPException):
        validate_ip_address("not.an.ip")

def test_validate_target_domain():
    assert validate_target("example.com", allow_domains=True) == "example.com"

def test_validate_target_localhost_blocked():
    with pytest.raises(HTTPException):
        validate_target("localhost", allow_domains=True)
```

**Implementation Tasks:**
- [ ] Write unit tests for all modules (target: >80% coverage)
- [ ] Create test fixtures and factories
- [ ] Mock external dependencies (database, SSH)
- [ ] Automate with pytest

### 4.2 Integration Tests

**File:** `tests/integration/test_router_communication.py`

```python
import pytest
from fastapi.testclient import TestClient
from remote_host.api.main import app

client = TestClient(app)

def test_telemetry_submission():
    """Test router can submit telemetry"""
    payload = {
        "event_type": "probe_request",
        "router_id": "AA:BB:CC:DD:EE:FF",
        "data": {"ssid": "TestNet", "rssi": -65},
        "client_mac": "11:22:33:44:55:66",
    }
    headers = {"X-API-Key": "test-api-key"}

    response = client.post("/api/router/telemetry", json=payload, headers=headers)
    assert response.status_code == 201
    assert "id" in response.json()

def test_pcap_upload_notification():
    """Test PCAP upload metadata registration"""
    payload = {
        "filename": "capture_test.pcap",
        "interface": "wlan0",
        "router_id": "AA:BB:CC:DD:EE:FF",
    }
    # Pre-create file
    # ... create test PCAP file ...

    response = client.post("/api/router/pcap/upload", json=payload)
    assert response.status_code == 200
```

**Implementation Tasks:**
- [ ] Set up test database (PostgreSQL in Docker)
- [ ] Create integration test suite
- [ ] Test router↔API communication
- [ ] Test file upload flows
- [ ] Test authentication flows

### 4.3 End-to-End Tests

**Scenario:** Full workflow from router to analysis

1. Router captures packets
2. PCAP transferred to remote host
3. API notified
4. Scan created via API
5. Worker executes analysis
6. Results stored
7. Report generated via MCP

**Implementation Tasks:**
- [ ] Create E2E test scenarios
- [ ] Set up test router (or VM)
- [ ] Automate workflow testing
- [ ] Verify data integrity throughout

---

## 5. Deployment Procedures

### 5.1 Router Deployment

**Manual Deployment (Development):**

```bash
# 1. SSH into router
ssh root@192.168.8.1

# 2. Download deployment script
wget https://github.com/canstralian/beryl-ax-pineapple/releases/latest/download/install.sh

# 3. Run installation
chmod +x install.sh
./install.sh

# 4. Follow interactive prompts
# - Enter remote host IP
# - Enter API key
# - Configure options

# 5. Verify installation
/etc/init.d/beryl-collector status
```

**Automated Deployment (Production):**

```bash
# Ansible playbook
ansible-playbook -i inventory.ini deploy-router.yml

# Playbook tasks:
# - Pre-flight checks
# - Install packages
# - Deploy scripts
# - Configure UCI
# - Enable services
# - Validate deployment
```

**Implementation Tasks:**
- [ ] Create Ansible playbook
- [ ] Write deployment documentation
- [ ] Create deployment checklist
- [ ] Test on multiple routers

### 5.2 Remote Host Deployment

**Docker Deployment (Recommended):**

```bash
# 1. Clone repository
git clone https://github.com/canstralian/beryl-ax-pineapple.git
cd beryl-ax-pineapple/deployment/docker

# 2. Configure environment
cp .env.example .env
nano .env  # Edit configuration

# 3. Generate secrets
openssl rand -hex 32  # SECRET_KEY
openssl rand -hex 32  # ROUTER_API_KEY

# 4. Start services
docker-compose up -d

# 5. Run migrations
docker-compose exec api alembic upgrade head

# 6. Create first user
docker-compose exec api python -m remote_host.cli create-user admin admin@example.com

# 7. Verify deployment
curl http://localhost:8000/health
```

**Systemd Deployment (Alternative):**

```bash
# Install dependencies
sudo apt install python3.11 postgresql

# Create virtual environment
python3.11 -m venv /opt/beryl-venv
source /opt/beryl-venv/bin/activate
pip install -e .

# Configure systemd service
sudo cp deployment/systemd/beryl-api.service /etc/systemd/system/
sudo systemctl enable beryl-api
sudo systemctl start beryl-api
```

**Implementation Tasks:**
- [ ] Test Docker deployment
- [ ] Create systemd unit files
- [ ] Write deployment documentation
- [ ] Create deployment checklist

---

## 6. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)

**Branch:** `feature/core-infrastructure`

- [ ] Complete router-side scripts (install, update, diagnostics)
- [ ] Implement UCI configuration schema
- [ ] Create comprehensive tests
- [ ] Write router deployment guide

**Deliverables:**
- Functional router installation script
- UCI configuration
- Unit tests (>80% coverage)
- Documentation

### Phase 2: Security Hardening (Week 3)

**Branch:** `feature/security-hardening`

- [ ] Implement TLS/HTTPS enforcement
- [ ] Add certificate validation
- [ ] Create security audit script
- [ ] Penetration testing

**Deliverables:**
- TLS configuration guide
- Security audit report
- Hardening checklist

### Phase 3: Workflow Automation (Week 4)

**Branch:** `feature/workflow-automation`

- [ ] Implement background worker
- [ ] Create scan execution engine
- [ ] Add result parsing
- [ ] Implement notifications

**Deliverables:**
- Functional background worker
- Scan execution tests
- Email/webhook notifications

### Phase 4: AI Integration (Week 5)

**Branch:** `feature/ai-integration`

- [ ] Complete MCP tool implementations
- [ ] Add AI-assisted analysis
- [ ] Create report generation
- [ ] Claude integration examples

**Deliverables:**
- Fully functional MCP server
- AI analysis examples
- Integration documentation

### Phase 5: Monitoring & Observability (Week 6)

**Branch:** `feature/monitoring`

- [ ] Set up Prometheus metrics
- [ ] Create Grafana dashboards
- [ ] Implement alerting
- [ ] Add distributed tracing

**Deliverables:**
- Prometheus configuration
- Grafana dashboards
- Alert rules
- Monitoring guide

### Phase 6: Production Readiness (Week 7-8)

**Branch:** `feature/production-ready`

- [ ] Performance optimization
- [ ] Load testing
- [ ] Disaster recovery procedures
- [ ] Backup/restore automation
- [ ] Documentation review

**Deliverables:**
- Performance benchmarks
- DR runbook
- Backup scripts
- Complete documentation

---

## 7. Quality Assurance

### 7.1 Code Quality Standards

- **Coverage:** Minimum 80% test coverage
- **Linting:** All code passes ruff/mypy (Python), luacheck (Lua)
- **Security:** Passes bandit, safety, semgrep scans
- **Documentation:** All public functions documented
- **Type Hints:** All Python functions type-annotated

### 7.2 Performance Benchmarks

**Router:**
- Telemetry collector: < 5% CPU, < 10 MB RAM
- PCAP rotation: < 2% CPU when idle
- Total memory footprint: < 160 MB

**Remote Host:**
- API response time: < 200ms (p95)
- Scan throughput: > 10 concurrent scans
- Database queries: < 100ms (p95)

### 7.3 Acceptance Criteria

Each feature branch must pass:
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Security scans pass (no high/critical issues)
- [ ] Code review approved (2 reviewers)
- [ ] Documentation updated
- [ ] Changelog entry added

---

**Approval Required:**
- [ ] Architecture specification approved
- [ ] Implementation specification approved
- [ ] Resource allocation confirmed
- [ ] Timeline agreed

**Next Action:** Await approval, then begin Phase 1 implementation.
