# Beryl AX Pineapple - MCP Kali Server Integration

AI-driven security automation for GL.iNet Beryl AX (MT-3000) router with Model Context Protocol (MCP) integration for Claude and other AI assistants.

## Architecture Overview

This project implements a **split architecture** optimized for embedded OpenWrt devices:

### Router (Beryl AX / OpenWrt)
**Hardware:** MT7981 (dual-core Cortex-A53 @1.3GHz), 512MB RAM, 256MB flash

**Responsibilities:**
- Network-facing real-time operations
- Lightweight packet capture & forwarding
- Host AP, DHCP/DNS, captive portal
- Basic telemetry collection
- Minimal local control scripts (Lua-based)

**Resource Budget:**
- Flash: ~70-120MB available (after firmware)
- RAM: ~80-160MB working set (leaves headroom)
- Storage: External USB drive (32GB+) for pcaps/logs

### Remote Host (Laptop / VM / Server)
**Responsibilities:**
- Heavy computational lifting
- PCAP storage & analysis (Wireshark, Scapy, pyshark)
- MCP server for AI integration
- REST API & web dashboard
- Database (SQLite/PostgreSQL)
- Advanced security tools (bettercap, metasploit integration)

## Project Structure

```
beryl-ax-pineapple/
├── src/
│   ├── remote_host/          # Remote server components (Python)
│   │   ├── api/              # FastAPI REST endpoints
│   │   ├── mcp_server.py     # MCP bridge for AI tools
│   │   ├── security/         # Security tool wrappers
│   │   ├── collectors/       # Data ingestion from router
│   │   └── models/           # Database models
│   └── router/               # Router-side components
│       ├── lua/              # Lightweight collectors (Lua)
│       ├── scripts/          # Shell scripts (tcpdump, rotation)
│       └── config/           # OpenWrt configs (UCI, init.d)
├── deployment/
│   ├── docker/               # Docker Compose for remote host
│   └── openwrt/              # Router deployment scripts
├── tests/
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
└── docs/                     # Documentation

```

## Key Features

### Security-First Design
- Input validation & sanitization (bleach, validators)
- Command allowlisting (no arbitrary shell execution)
- Authentication via JWT tokens
- Rate limiting & resource controls
- Security scanning in CI/CD (Bandit, Safety, Semgrep)

### Resource-Aware Implementation
- Router components written in Lua (low memory footprint: ~2-6MB)
- Automatic PCAP rotation & offload (prevents flash wear)
- Graceful degradation under resource pressure
- USB storage detection & failover

### AI Integration (MCP)
- Expose security tools via Model Context Protocol
- AI-assisted vulnerability analysis
- Automated report generation
- Code generation for exploit development (defensive only)

## Quick Start

### Remote Host Setup

```bash
# Clone repository
git clone https://github.com/canstralian/beryl-ax-pineapple.git
cd beryl-ax-pineapple

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev,ai,monitoring]"

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Start remote host server
uvicorn remote_host.api.main:app --host 0.0.0.0 --port 8000

# Start MCP server (in another terminal)
beryl-mcp
```

### Router Setup

```bash
# SSH into router
ssh root@192.168.8.1

# Install required packages (minimal set)
opkg update
opkg install lua lua-cjson tcpdump kmod-usb-storage

# Copy router scripts
scp -r deployment/openwrt/scripts/* root@192.168.8.1:/usr/local/bin/
scp -r src/router/lua/* root@192.168.8.1:/usr/local/lib/lua/

# Enable and start services
/etc/init.d/beryl-collector enable
/etc/init.d/beryl-collector start
```

### Docker Deployment (Recommended)

```bash
cd deployment/docker
docker-compose up -d
```

This starts:
- FastAPI server (port 8000)
- PostgreSQL database
- MCP server (port 9000)
- Bettercap (network analysis)
- Prometheus (metrics)

## Security Tools Available

### Network Scanning
- **nmap**: Port scanning, service detection, OS fingerprinting
- **gobuster**: Directory/DNS enumeration
- **nikto**: Web server vulnerability scanning

### Wireless Security
- **aircrack-ng**: WPA/WPA2 cracking (via remote host only)
- **kismet**: Wireless network detection
- Probe request collection (router-side Lua)

### Exploitation & Post-Exploitation
- **metasploit**: Framework integration (remote host)
- **sqlmap**: SQL injection testing
- **hydra**: Password brute-forcing

### Packet Analysis
- **tcpdump**: Lightweight capture (router)
- **wireshark/tshark**: Deep packet inspection (remote host)
- **scapy**: Packet manipulation & crafting

## OpenWrt Package Requirements

**Minimal router-side installation** (~20-40MB flash):

```bash
# Core networking
opkg install iw hostapd-common dnsmasq-full iptables-mod-nat

# Captive portal (optional)
opkg install nodogsplash

# Packet capture
opkg install tcpdump-mini

# Scripting
opkg install lua lua-cjson

# Storage & transfer
opkg install kmod-usb-storage curl openssh-sftp-server
```

See `docs/OPENWRT_PACKAGES.md` for complete list and rationale.

## API Documentation

Once the server is running, visit:
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## MCP Tools Exposed

The MCP server exposes these tools to AI assistants:

- `nmap_scan`: Network port scanning
- `capture_packets`: Start/stop packet capture
- `analyze_pcap`: Parse PCAP files with AI assistance
- `run_gobuster`: Web directory enumeration
- `wireless_scan`: Detect nearby networks
- `generate_report`: AI-generated security assessment

## Testing

```bash
# Run all tests with coverage
pytest

# Run specific test suite
pytest tests/unit/test_security.py

# Security scans
bandit -r src/
safety check
semgrep --config=auto src/
```

## Development

```bash
# Install pre-commit hooks
pre-commit install

# Format code
black src/ tests/
ruff check --fix src/ tests/

# Type checking
mypy src/
```

## Resource Monitoring

Monitor router resources:

```bash
# SSH into router
ssh root@192.168.8.1

# Check memory usage
free -m

# Check flash usage
df -h

# Monitor CPU
top

# Check USB storage
ls -lh /mnt/usb/
```

## Safety & Legal Notice

**DEFENSIVE SECURITY ONLY**

This tool is designed for:
- Authorized penetration testing
- Security research in controlled environments
- Network administration & monitoring
- Educational purposes

**DO NOT use for:**
- Unauthorized network access
- Malicious attacks
- Credential harvesting
- Any illegal activity

Always obtain proper authorization before testing networks you do not own.

## Contributing

See `CONTRIBUTING.md` for guidelines.

## License

MIT License - see `LICENSE` file.

## Acknowledgments

- GL.iNet for excellent OpenWrt hardware
- Anthropic for Claude & MCP protocol
- Kali Linux project for security tools
- OpenWrt community

## Support

- Issues: [GitHub Issues](https://github.com/canstralian/beryl-ax-pineapple/issues)
- Discussions: [GitHub Discussions](https://github.com/canstralian/beryl-ax-pineapple/discussions)
- Documentation: [Full Docs](./docs/)

---

**Status:** Alpha - Active Development

**Hardware Tested:** GL.iNet Beryl AX (MT-3000)

**OpenWrt Version:** 23.05+
