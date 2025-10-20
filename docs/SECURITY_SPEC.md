# Beryl AX Pineapple - Security Specification

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2025-10-20

## Table of Contents

1. [Security Policy](#1-security-policy)
2. [Threat Model](#2-threat-model)
3. [Authentication & Authorization](#3-authentication--authorization)
4. [Input Validation](#4-input-validation)
5. [Secure Communication](#5-secure-communication)
6. [Secrets Management](#6-secrets-management)
7. [Security Testing](#7-security-testing)
8. [Incident Response](#8-incident-response)

---

## 1. Security Policy

### 1.1 Intended Use

Beryl AX Pineapple is designed **exclusively for defensive security purposes**:

**Authorized Use Cases:**
- ✅ Penetration testing with explicit written authorization
- ✅ Security research in isolated lab environments
- ✅ Network administration of owned infrastructure
- ✅ Educational purposes in controlled settings
- ✅ Vulnerability assessment with proper scope

**Prohibited Use Cases:**
- ❌ Unauthorized network access or scanning
- ❌ Malicious attacks or exploitation
- ❌ Credential harvesting or theft
- ❌ Privacy violations
- ❌ Any illegal activity

### 1.2 Legal Compliance

Users must comply with:
- Computer Fraud and Abuse Act (CFAA) - US
- Computer Misuse Act - UK
- Local cybersecurity laws and regulations
- Organizational security policies
- Ethical hacking guidelines (EC-Council Code of Ethics)

### 1.3 Responsible Disclosure

Security vulnerabilities should be reported to:
- **Email:** security@beryl-pineapple.example (create this)
- **GPG Key:** [Public key ID]
- **Response Time:** < 48 hours
- **Disclosure Timeline:** 90 days (coordinated)

---

## 2. Threat Model

### 2.1 Assets

| Asset | Criticality | Description |
|-------|-------------|-------------|
| Router Control | Critical | Administrative access to Beryl AX router |
| Captured Traffic | High | PCAP files containing network traffic |
| Scan Results | High | Security scan outputs and findings |
| API Credentials | Critical | JWT tokens, API keys |
| Router Credentials | Critical | SSH keys, passwords |
| Database | High | All persistent data |
| AI Integration | Medium | MCP access, AI API keys |

### 2.2 Threat Actors

#### TA-1: External Attacker
- **Motivation:** Data theft, system compromise
- **Capabilities:** Network access, vulnerability exploitation
- **Mitigations:** Firewall rules, authentication, TLS

#### TA-2: Malicious Insider
- **Motivation:** Abuse of legitimate access
- **Capabilities:** Valid credentials, system knowledge
- **Mitigations:** Audit logging, least privilege, monitoring

#### TA-3: Compromised Router
- **Motivation:** Pivot to remote host
- **Capabilities:** Router-level access, network position
- **Mitigations:** API key rotation, network segmentation, validation

### 2.3 Attack Scenarios

#### Scenario 1: Unauthorized API Access

**Attack Vector:** Attacker obtains leaked API key

**Impact:**
- Unauthorized scan execution
- Data exfiltration (telemetry, PCAPs)
- Denial of service

**Mitigations:**
- API key rotation policy
- Rate limiting
- IP allowlisting (optional)
- Audit logging
- Anomaly detection

#### Scenario 2: Command Injection

**Attack Vector:** Malicious input in scan parameters

**Example:**
```python
# Vulnerable (example of what NOT to do)
target = request.json["target"]
os.system(f"nmap {target}")  # ❌ VULNERABLE

# Secure (what we do)
target = validate_target(request.json["target"])
subprocess.run(["nmap", target], check=True)  # ✅ SAFE
```

**Impact:**
- Remote code execution on remote host
- Data theft
- System compromise

**Mitigations:**
- Input validation (allowlist pattern)
- Subprocess with argument arrays (no shell)
- Least privilege user
- Resource limits

#### Scenario 3: Path Traversal

**Attack Vector:** Malicious filename in PCAP upload

**Example:**
```python
# Vulnerable
filename = request.json["filename"]
path = f"/var/lib/beryl/pcaps/{filename}"  # ❌ VULNERABLE

# Secure
filename = sanitize_filename(request.json["filename"])
path = sanitize_path(filename, PCAP_STORAGE_PATH)  # ✅ SAFE
```

**Impact:**
- Read/write arbitrary files
- Configuration tampering
- Code execution

**Mitigations:**
- Filename sanitization
- Path resolution with base directory check
- File operation restrictions

#### Scenario 4: Router Compromise via Wireless

**Attack Vector:** Exploit in hostapd or related services

**Impact:**
- Router control
- Traffic interception
- Pivot to remote host

**Mitigations:**
- Regular firmware updates
- Firewall hardening
- Network segmentation
- Intrusion detection

---

## 3. Authentication & Authorization

### 3.1 Authentication Mechanisms

#### User Authentication (JWT)

**Specification:**
- **Algorithm:** HS256 (HMAC-SHA256)
- **Token Expiration:** 30 minutes (configurable)
- **Refresh Tokens:** Not implemented (use re-authentication)
- **Storage:** Client-side only (not in database)

**Security Requirements:**
- SR-AUTH-001: Secret key MUST be >= 32 bytes of random data
- SR-AUTH-002: Tokens MUST include expiration (`exp`) claim
- SR-AUTH-003: Tokens MUST include issued-at (`iat`) claim
- SR-AUTH-004: Token validation MUST check signature and expiration
- SR-AUTH-005: Failed authentication attempts MUST be rate-limited

**Implementation:**
```python
# Token creation
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

# Token validation
def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.JWTError:
        raise HTTPException(401, "Invalid token")
```

#### Router Authentication (API Key)

**Specification:**
- **Method:** X-API-Key header
- **Format:** 64 hexadecimal characters (256 bits)
- **Rotation:** Manual (on-demand)
- **Validation:** Constant-time comparison

**Security Requirements:**
- SR-AUTH-006: API keys MUST be generated with cryptographic RNG
- SR-AUTH-007: API key comparison MUST use constant-time algorithm
- SR-AUTH-008: Failed API key attempts MUST be logged
- SR-AUTH-009: API keys MUST NOT be logged or displayed

**Implementation:**
```python
def verify_router_api_key(api_key: str) -> bool:
    import hmac
    # Constant-time comparison prevents timing attacks
    return hmac.compare_digest(api_key, settings.router_api_key)
```

### 3.2 Authorization Model

**Role-Based Access Control (RBAC):**

| Role | Permissions |
|------|-------------|
| Admin | All operations, user management |
| Operator | Run scans, view results |
| Viewer | Read-only access |
| Router | Submit telemetry, upload PCAPs |

**Implementation:**
```python
# Decorator for role enforcement
def require_role(required_role: str):
    def decorator(func):
        async def wrapper(*args, current_user: dict, **kwargs):
            if current_user["role"] != required_role:
                raise HTTPException(403, "Insufficient permissions")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@app.delete("/api/scans/{scan_id}")
@require_role("admin")
async def delete_scan(scan_id: int, current_user: dict = Depends(get_current_user)):
    # ...
```

---

## 4. Input Validation

### 4.1 Validation Requirements

**General Principles:**
- **Allowlist > Blocklist:** Define what IS allowed, not what ISN'T
- **Fail Securely:** Reject invalid input, don't attempt to sanitize
- **Validate Early:** At API boundary, before processing
- **Specific Validation:** Different rules for different input types

### 4.2 Validation Rules

#### IP Addresses

**Requirements:**
- SR-VAL-001: MUST validate IPv4 and IPv6 syntax
- SR-VAL-002: SHOULD reject loopback/link-local if configured
- SR-VAL-003: MUST use `ipaddress` library (not regex)

**Implementation:**
```python
def validate_ip_address(ip: str, allow_private: bool = True) -> str:
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(400, f"Invalid IP address: {ip}")

    if not allow_private and ip_obj.is_private:
        raise HTTPException(400, "Private IPs not allowed")

    return str(ip_obj)
```

#### Domain Names

**Requirements:**
- SR-VAL-004: MUST validate DNS syntax
- SR-VAL-005: MUST reject localhost/internal domains
- SR-VAL-006: SHOULD use `validators` library

**Implementation:**
```python
def validate_domain(domain: str) -> str:
    if not validators.domain(domain):
        raise HTTPException(400, "Invalid domain name")

    if domain.lower() in ["localhost", "localhost.localdomain"]:
        raise HTTPException(400, "Localhost not allowed")

    return domain
```

#### Filenames

**Requirements:**
- SR-VAL-007: MUST strip path components
- SR-VAL-008: MUST allow only alphanumeric + dash/underscore/dot
- SR-VAL-009: MUST reject hidden files (starting with .)
- SR-VAL-010: MUST enforce maximum length (255 characters)

**Implementation:**
```python
def sanitize_filename(filename: str, max_length: int = 255) -> str:
    # Remove path components
    filename = Path(filename).name

    # Allow only safe characters
    sanitized = re.sub(r"[^\w\-.]", "_", filename)

    # No hidden files
    sanitized = sanitized.lstrip(".")

    if not sanitized or len(sanitized) > max_length:
        raise HTTPException(400, "Invalid filename")

    return sanitized
```

#### Command Arguments

**Requirements:**
- SR-VAL-011: MUST reject shell metacharacters: `;`, `&`, `|`, `` ` ``, `$`, `(`, `)`, `<`, `>`
- SR-VAL-012: MUST use subprocess argument arrays (not shell)
- SR-VAL-013: SHOULD validate against allowlist pattern

**Implementation:**
```python
def validate_scan_type(scan_type: str) -> str:
    allowed = ["syn", "connect", "udp", "ack", "window"]
    if scan_type not in allowed:
        raise HTTPException(400, f"Invalid scan type: {scan_type}")
    return scan_type

# Safe execution
subprocess.run(
    ["nmap", "-sS", "-p", ports, target],  # Argument array
    check=True,
    capture_output=True,
    timeout=300,
)
```

---

## 5. Secure Communication

### 5.1 TLS Configuration

**Requirements:**
- SR-TLS-001: TLS 1.2+ REQUIRED in production
- SR-TLS-002: Certificate validation MUST be enforced
- SR-TLS-003: Self-signed certificates PROHIBITED in production
- SR-TLS-004: Certificate pinning RECOMMENDED for router↔host

**Implementation (nginx reverse proxy):**

```nginx
server {
    listen 443 ssl http2;
    server_name beryl-api.example.com;

    # TLS configuration
    ssl_certificate /etc/letsencrypt/live/beryl-api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/beryl-api.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5.2 SSH Hardening (Router)

**Requirements:**
- SR-SSH-001: Password authentication DISABLED
- SR-SSH-002: Root login via key only
- SR-SSH-003: Non-standard port RECOMMENDED
- SR-SSH-004: ed25519 keys REQUIRED (not RSA)

**Configuration (`/etc/config/dropbear`):**

```uci
config dropbear
    option PasswordAuth '0'
    option RootPasswordAuth '0'
    option Port '22'
    option GatewayPorts '0'
```

**Key generation:**
```bash
ssh-keygen -t ed25519 -f /root/.ssh/beryl_key -N ""
```

---

## 6. Secrets Management

### 6.1 Storage

**Requirements:**
- SR-SEC-001: Secrets MUST NOT be committed to git
- SR-SEC-002: Secrets MUST be loaded from environment variables
- SR-SEC-003: Secrets MUST be rotated regularly (90 days)
- SR-SEC-004: Secrets MUST be generated with crypto RNG

**Implementation:**
```bash
# Generate secure secrets
openssl rand -hex 32  # 256-bit secret

# Store in .env (not committed)
SECRET_KEY=abc123...
ROUTER_API_KEY=def456...

# Load in application
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = Field(..., min_length=32)
    router_api_key: str = Field(..., min_length=32)

    class Config:
        env_file = ".env"
```

### 6.2 Transit

**Requirements:**
- SR-SEC-005: Secrets MUST be transmitted over TLS only
- SR-SEC-006: Secrets MUST NOT be logged
- SR-SEC-007: Secrets MUST NOT appear in URLs (use headers/body)

---

## 7. Security Testing

### 7.1 Automated Security Scanning

**Tools:**
- **Bandit:** Python security linting
- **Safety:** Dependency vulnerability scanning
- **Semgrep:** SAST (static analysis)
- **Trivy:** Container vulnerability scanning
- **OWASP ZAP:** Dynamic application security testing

**CI/CD Integration:**
```yaml
# .github/workflows/security.yml
name: Security Scanning

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Bandit Scan
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json

      - name: Safety Check
        run: |
          pip install safety
          safety check --json

      - name: Semgrep Scan
        run: |
          pip install semgrep
          semgrep --config=auto src/

      - name: Trivy Container Scan
        run: |
          docker build -t beryl-api -f deployment/docker/Dockerfile.api .
          trivy image beryl-api
```

### 7.2 Manual Security Testing

**Penetration Testing Checklist:**

- [ ] Authentication bypass attempts
- [ ] Authorization escalation
- [ ] SQL injection (via ORM)
- [ ] Command injection
- [ ] Path traversal
- [ ] XSS (if web UI present)
- [ ] CSRF protection
- [ ] Rate limiting bypass
- [ ] Token manipulation
- [ ] Session fixation

**Tools:**
- Burp Suite Professional
- OWASP ZAP
- sqlmap (negative test)
- Metasploit (controlled)

---

## 8. Incident Response

### 8.1 Security Incident Classification

| Severity | Description | Response Time |
|----------|-------------|---------------|
| Critical | Active exploitation, data breach | < 1 hour |
| High | Vulnerability discovered, no exploit | < 4 hours |
| Medium | Potential security issue | < 24 hours |
| Low | Security enhancement | < 7 days |

### 8.2 Incident Response Plan

**Phase 1: Detection**
- Monitor logs for anomalies
- Review security alerts
- User reports

**Phase 2: Containment**
- Isolate affected systems
- Revoke compromised credentials
- Block malicious IPs

**Phase 3: Eradication**
- Identify root cause
- Apply patches/fixes
- Remove backdoors

**Phase 4: Recovery**
- Restore from backups
- Verify system integrity
- Resume operations

**Phase 5: Post-Incident**
- Write incident report
- Update security controls
- Conduct lessons learned

---

## 9. Compliance Checklist

### Pre-Deployment

- [ ] All secrets rotated from defaults
- [ ] TLS certificates obtained
- [ ] Firewall rules configured
- [ ] SSH keys generated
- [ ] Passwords disabled
- [ ] Security scanning passed
- [ ] Penetration testing completed

### Ongoing

- [ ] Monthly security scans
- [ ] Quarterly penetration testing
- [ ] 90-day secret rotation
- [ ] Weekly backup verification
- [ ] Daily log review
- [ ] Dependency updates (weekly)

---

**Approval Required:**
- [ ] Security policy approved
- [ ] Threat model validated
- [ ] Security controls implemented
- [ ] Testing completed
- [ ] Incident response plan accepted

**Next Action:** Review and approve security specifications before deployment.
