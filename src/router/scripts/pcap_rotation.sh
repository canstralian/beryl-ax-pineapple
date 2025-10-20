#!/bin/sh

################################################################################
# PCAP Rotation and Offload Script for GL.iNet Beryl AX (MT-3000)
#
# Captures packets with automatic rotation and SCP transfer to remote host.
# Optimized for USB storage (32GB budget) and low resource usage.
#
# Features:
#   - Rotating packet capture with size/time limits
#   - Automatic SCP offload to remote host
#   - USB storage detection and failover
#   - Cleanup of old captures
#   - Resource-aware (CPU/memory limits)
#
# Requirements:
#   - tcpdump (opkg install tcpdump)
#   - openssh-sftp-server (opkg install openssh-sftp-server)
#   - kmod-usb-storage (opkg install kmod-usb-storage)
#
# Usage:
#   ./pcap_rotation.sh start [interface]
#   ./pcap_rotation.sh stop
#   ./pcap_rotation.sh status
################################################################################

# Configuration
REMOTE_HOST="${BERYL_REMOTE_HOST:-192.168.1.100}"
REMOTE_PORT="${BERYL_REMOTE_PORT:-22}"
REMOTE_USER="${BERYL_REMOTE_USER:-beryl}"
REMOTE_PATH="${BERYL_REMOTE_PATH:-/var/lib/beryl/pcaps}"
SSH_KEY="${BERYL_SSH_KEY:-/root/.ssh/beryl_key}"

# Capture settings
INTERFACE="${2:-wlan0}"
CAPTURE_SIZE_MB="${BERYL_CAPTURE_SIZE_MB:-10}"  # Max size per file
CAPTURE_COUNT="${BERYL_CAPTURE_COUNT:-10}"       # Number of files to keep
CAPTURE_FILTER="${BERYL_CAPTURE_FILTER:-}"      # BPF filter (optional)

# Storage paths (prefer USB if available)
USB_MOUNT="/mnt/usb"
FALLBACK_PATH="/tmp/captures"
STORAGE_PATH=""

# PID file
PID_FILE="/var/run/pcap_rotation.pid"
LOG_FILE="/var/log/pcap_rotation.log"

################################################################################
# Logging
################################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] $level: $message" | tee -a "$LOG_FILE"
}

################################################################################
# USB Storage Detection
################################################################################

detect_storage() {
    # Check if USB is mounted and has space
    if [ -d "$USB_MOUNT" ] && mountpoint -q "$USB_MOUNT"; then
        local avail_mb=$(df -m "$USB_MOUNT" | awk 'NR==2 {print $4}')

        if [ "$avail_mb" -gt 100 ]; then
            STORAGE_PATH="$USB_MOUNT/beryl-captures"
            mkdir -p "$STORAGE_PATH"
            log "INFO" "Using USB storage: $STORAGE_PATH ($avail_mb MB available)"
            return 0
        else
            log "WARN" "USB storage low on space ($avail_mb MB), using fallback"
        fi
    fi

    # Fallback to /tmp (RAM-based)
    STORAGE_PATH="$FALLBACK_PATH"
    mkdir -p "$STORAGE_PATH"
    log "WARN" "Using fallback storage: $STORAGE_PATH (limited to RAM)"
}

################################################################################
# Capture Management
################################################################################

start_capture() {
    log "INFO" "Starting packet capture on $INTERFACE"

    # Detect and configure storage
    detect_storage

    # Check if interface exists
    if ! ip link show "$INTERFACE" >/dev/null 2>&1; then
        log "ERROR" "Interface $INTERFACE not found"
        exit 1
    fi

    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "ERROR" "Capture already running (PID: $pid)"
            exit 1
        else
            log "WARN" "Stale PID file found, removing"
            rm -f "$PID_FILE"
        fi
    fi

    # Build tcpdump command
    local capture_file="$STORAGE_PATH/capture_%Y%m%d_%H%M%S.pcap"
    local filter_arg=""
    [ -n "$CAPTURE_FILTER" ] && filter_arg="$CAPTURE_FILTER"

    # Start tcpdump with rotation
    # -i: interface
    # -C: rotate after N MB
    # -W: keep N files (circular)
    # -w: output file pattern
    # -Z: don't drop privileges (running as root on router)
    tcpdump -i "$INTERFACE" \
            -C "$CAPTURE_SIZE_MB" \
            -W "$CAPTURE_COUNT" \
            -w "$STORAGE_PATH/capture_%s.pcap" \
            -Z root \
            $filter_arg \
            >/dev/null 2>&1 &

    local pid=$!
    echo $pid > "$PID_FILE"

    log "INFO" "Capture started (PID: $pid, storage: $STORAGE_PATH)"

    # Start offload daemon in background
    offload_daemon &
}

stop_capture() {
    log "INFO" "Stopping packet capture"

    if [ ! -f "$PID_FILE" ]; then
        log "ERROR" "Capture not running (no PID file)"
        exit 1
    fi

    local pid=$(cat "$PID_FILE")

    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        sleep 2

        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid"
            log "WARN" "Forced kill of tcpdump process"
        fi

        log "INFO" "Capture stopped (PID: $pid)"
    else
        log "WARN" "Capture process not found (stale PID?)"
    fi

    rm -f "$PID_FILE"

    # Final offload of any remaining files
    offload_files
}

status_capture() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "INFO" "Capture running (PID: $pid)"

            # Show stats
            local file_count=$(ls -1 "$STORAGE_PATH"/*.pcap 2>/dev/null | wc -l)
            local total_size_mb=$(du -sm "$STORAGE_PATH" 2>/dev/null | awk '{print $1}')

            echo "Files: $file_count"
            echo "Total size: ${total_size_mb}MB"
            echo "Storage: $STORAGE_PATH"
            return 0
        else
            log "WARN" "PID file exists but process not running"
            return 1
        fi
    else
        log "INFO" "Capture not running"
        return 1
    fi
}

################################################################################
# Offload to Remote Host
################################################################################

offload_files() {
    # Check SSH key exists
    if [ ! -f "$SSH_KEY" ]; then
        log "WARN" "SSH key not found: $SSH_KEY (skipping offload)"
        return 1
    fi

    # Find PCAP files to offload
    local files=$(find "$STORAGE_PATH" -name "*.pcap" -type f -mmin +1)

    if [ -z "$files" ]; then
        return 0
    fi

    log "INFO" "Offloading $(echo "$files" | wc -l) PCAP files to remote host"

    # Transfer each file
    echo "$files" | while read -r file; do
        local filename=$(basename "$file")
        local remote_file="${REMOTE_PATH}/${filename}"

        # SCP with compression and error handling
        if scp -i "$SSH_KEY" \
               -P "$REMOTE_PORT" \
               -o StrictHostKeyChecking=no \
               -o ConnectTimeout=10 \
               -C \
               "$file" "${REMOTE_USER}@${REMOTE_HOST}:${remote_file}" 2>/dev/null; then

            log "INFO" "Offloaded: $filename"

            # Delete local file after successful transfer
            rm -f "$file"

            # Notify remote API about new file
            notify_remote_api "$filename"
        else
            log "ERROR" "Failed to offload: $filename"
        fi
    done
}

notify_remote_api() {
    local filename="$1"

    # Call remote API to register PCAP file
    local api_key="${BERYL_API_KEY:-CHANGE_THIS_SECURE_API_KEY}"
    local url="http://${REMOTE_HOST}:8000/api/router/pcap/upload"

    local json="{\"filename\":\"$filename\",\"interface\":\"$INTERFACE\",\"router_id\":\"$(get_router_mac)\"}"

    curl -s -X POST \
         -H "Content-Type: application/json" \
         -H "X-API-Key: $api_key" \
         -d "$json" \
         "$url" >/dev/null 2>&1

    if [ $? -eq 0 ]; then
        log "DEBUG" "Notified API about: $filename"
    else
        log "WARN" "Failed to notify API about: $filename"
    fi
}

get_router_mac() {
    ip link show "$INTERFACE" | grep 'link/ether' | awk '{print $2}' | tr -d '\n'
}

################################################################################
# Background Offload Daemon
################################################################################

offload_daemon() {
    log "INFO" "Starting offload daemon"

    while [ -f "$PID_FILE" ]; do
        sleep 60  # Check every minute
        offload_files

        # Cleanup old log file
        if [ -f "$LOG_FILE" ] && [ $(stat -f '%z' "$LOG_FILE" 2>/dev/null || stat -c '%s' "$LOG_FILE") -gt 1048576 ]; then
            mv "$LOG_FILE" "${LOG_FILE}.old"
        fi
    done

    log "INFO" "Offload daemon stopped"
}

################################################################################
# Main Entry Point
################################################################################

case "${1:-}" in
    start)
        start_capture
        ;;
    stop)
        stop_capture
        ;;
    status)
        status_capture
        ;;
    offload)
        offload_files
        ;;
    *)
        echo "Usage: $0 {start|stop|status|offload} [interface]"
        echo ""
        echo "Environment variables:"
        echo "  BERYL_REMOTE_HOST       Remote host IP (default: 192.168.1.100)"
        echo "  BERYL_REMOTE_PORT       SSH port (default: 22)"
        echo "  BERYL_REMOTE_USER       SSH user (default: beryl)"
        echo "  BERYL_CAPTURE_SIZE_MB   Max file size in MB (default: 10)"
        echo "  BERYL_CAPTURE_COUNT     Number of files to keep (default: 10)"
        echo "  BERYL_CAPTURE_FILTER    BPF filter (default: none)"
        exit 1
        ;;
esac
