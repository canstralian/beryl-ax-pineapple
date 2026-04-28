# 🧩 WiFiPineapple Beryl AX — Spec-Kit

## Overview

The **WiFiPineapple Beryl AX** project re-engineers the **GL.iNet GL-MT3000 (Beryl AX)** into an **open, modular wireless auditing platform** built on **OpenWrt**.
It aims to deliver *WiFi Pineapple-class* functionality with greater transparency, flexibility, and performance — all within the bounds of **lawful, ethical network security research**.

---

## ⚙️ Hardware Baseline

| Component    | Specification                                         | Role                                                                        |
| ------------ | ----------------------------------------------------- | --------------------------------------------------------------------------- |
| **CPU**      | MediaTek MT7981B (Dual-Core ARM Cortex-A53 @ 1.3 GHz) | Handles concurrent audit tasks (packet capture, rogue APs, DNS spoofing).   |
| **RAM**      | 512 MB DDR4                                           | Enables concurrent multi-tool sessions (Kismet, Hostapd-Mana, Aircrack-NG). |
| **Storage**  | 256 MB NAND Flash + USB 3.0 External                  | Supports persistent audit toolkit and long packet captures.                 |
| **Wireless** | Dual-band Wi-Fi 6 (AX3000)                            | Primary radios for reconnaissance and injection.                            |
| **Ethernet** | 2.5 G WAN + 1 G LAN                                   | High-speed tethering / data exfil backhaul.                                 |
| **Ports**    | 1 × USB 3.0 Type-A                                    | For external Wi-Fi adapters (Atheros / Realtek).                            |
| **Power**    | USB-C 5 V 2 A                                         | Portable operation with power banks.                                        |

---

## 🧠 Software Stack

### Base System

* **OpenWrt v24+ (Mainline)**
* Linux 6.6+ kernel
* `opkg` package manager with direct access to community repositories
* `LuCI` and `UCI` configuration interfaces


### Defensive Capture Intelligence (Implemented)

The repository now includes a Python parser (`scripts/capture_parser.py`) that supports:

* Parsing JSON, CSV, and `.txt` packet export files (`.txt` treated as CSV-style input)
* Building passive network summaries (AP/client/frame counts)
* Flagging defensive alerts for:
  * open networks
  * possible evil-twin SSID collisions
  * deauth burst activity

This is designed for **authorized monitoring and hardening**, not active attack automation.

### Core Auditing Toolkit

| Tool                 | Purpose                                                          |
| -------------------- | ---------------------------------------------------------------- |
| `aircrack-ng`        | Packet capture, WEP/WPA key cracking (for educational use only). |
| `kismet`             | Passive reconnaissance, network mapping.                         |
| `hostapd-mana`       | Rogue AP emulation and credential harvesting simulations.        |
| `mdk4`               | Stress-testing and wireless fuzzing of target networks.          |
| `dnsmasq-full`       | DHCP + DNS emulation for captive portal attacks.                 |
| `tcpdump` / `tshark` | Raw traffic capture and forensic analysis.                       |

---

## 🧩 Architecture

```
┌───────────────────────────┐
│      OpenWrt Kernel       │
│ (Linux 6.6, MT76 Drivers) │
└────────────┬──────────────┘
             │
┌────────────▼────────────┐
│     Service Layer       │
│ (hostapd-mana, kismet)  │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│  Auditing Interface/UI  │
│ (LuCI + Python Scripts) │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ Data Persistence & Logs │
│  (/mnt/usb/audit_logs)  │
└─────────────────────────┘
```

---

## 🚀 Setup Workflow

1. **Flash Mainline OpenWrt**

   * Download image: [OpenWrt Firmware Selector](https://firmware-selector.openwrt.org/) → *GL-MT3000 (Beryl AX)*
   * Flash via OEM web UI → verify checksum → reboot.

2. **Bootstrap Environment**

   ```bash
   opkg update
   opkg install aircrack-ng kismet hostapd-mana mdk4 dnsmasq-full tcpdump
   ```

3. **Configure Wireless Interfaces**

   * `radio0`: monitoring
   * `radio1`: rogue AP or client simulation
   * Optional USB Wi-Fi dongles for extra channels

4. **Launch Tools**

   * `kismet -c wlan0mon`
   * `hostapd-mana /etc/hostapd/hostapd.conf`
   * `tcpdump -i wlan1 -w capture.pcap`

---

## 🧰 Optional Enhancements

* **UI Layer:** Flask-based web interface for session management and visual metrics.
* **Persistent Storage:** Mount `/mnt/usb` for captures and config profiles.
* **Containerization:** Add Podman for modular tool isolation.
* **Integration:** Optional API endpoints for remote control or dashboard telemetry.

---

## 🧑‍⚖️ Legal & Ethical Use

This platform is **strictly for authorized security assessments**.
Usage outside of explicit, documented authorization constitutes a violation of law and professional ethics.
Every build and deployment must follow:

* [HackerOne Disclosure Guidelines](https://www.hackerone.com/disclosure-guidelines)
* [EC-Council Code of Ethics](https://www.eccouncil.org/code-of-ethics/)
* Applicable **Computer Fraud and Abuse** statutes in your jurisdiction.

---

## 📚 Repository Layout

```
WiFiPineapple-BerylAX/
│
├── firmware/
│   ├── openwrt-image.bin
│   └── sha256sum.txt
│
├── configs/
│   ├── hostapd.conf
│   ├── kismet.conf
│   └── wireless.json
│
├── scripts/
│   ├── setup_openwrt.sh
│   ├── launch_audit.sh
│   └── capture_parser.py
│
├── docs/
│   ├── architecture.md
│   ├── legal_ethics.md
│   └── performance_notes.md
│
├── LICENSE
└── README.md
```

---

## 🧾 License

Released under the **GPLv3 License** to preserve open-source freedom and auditing transparency.

---

## 🚀 Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/WiFiPineapple-BerylAX.git
   cd WiFiPineapple-BerylAX
   ```

2. Flash OpenWrt to your GL-MT3000 device using the firmware in the `firmware/` directory

3. Run the setup script:
   ```bash
   chmod +x scripts/setup_openwrt.sh
   ./scripts/setup_openwrt.sh
   ```

4. Configure your wireless interfaces using the provided config files in `configs/`

5. Launch your first audit session:
   ```bash
   chmod +x scripts/launch_audit.sh
   ./scripts/launch_audit.sh
   ```

For detailed setup instructions, see the documentation in the `docs/` directory.

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and ensure all code follows our ethical standards for security research.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## ⚠️ Disclaimer

This project is intended solely for authorized security testing and educational purposes. Users are responsible for ensuring compliance with all applicable laws and regulations in their jurisdiction. The authors and contributors are not responsible for any misuse of this software.