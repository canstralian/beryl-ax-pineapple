#!/usr/bin/lua

--[[
Lightweight Telemetry Collector for GL.iNet Beryl AX (MT-3000)

Collects network events (probe requests, associations, etc.) and forwards
to remote host via HTTP API. Optimized for low memory footprint (~2-6MB).

Requirements:
  - lua (opkg install lua)
  - lua-cjson (opkg install lua-cjson)
  - curl (opkg install curl)

Usage:
  lua telemetry_collector.lua [config_file]
]]

local json = require("cjson")
local socket = require("socket")

-- =============================================================================
-- Configuration
-- =============================================================================

local CONFIG = {
    -- Remote host settings
    remote_host = os.getenv("BERYL_REMOTE_HOST") or "192.168.1.100",
    remote_port = os.getenv("BERYL_REMOTE_PORT") or "8000",
    api_key = os.getenv("BERYL_API_KEY") or "CHANGE_THIS_SECURE_API_KEY",

    -- Router identification
    router_id = nil,  -- Will be populated from MAC address

    -- Collection settings
    monitor_interface = "wlan0",
    scan_interval = 10,  -- seconds
    batch_size = 20,  -- events per batch
    max_queue_size = 100,  -- max events in memory

    -- Paths
    temp_dir = "/tmp/beryl-telemetry",
    log_file = "/tmp/beryl-telemetry.log",

    -- Feature flags
    collect_probe_requests = true,
    collect_associations = true,
    collect_interface_stats = true,
}

-- =============================================================================
-- Logging
-- =============================================================================

local function log(level, message)
    local timestamp = os.date("%Y-%m-%d %H:%M:%S")
    local log_entry = string.format("[%s] %s: %s\n", timestamp, level, message)

    -- Write to stderr for immediate feedback
    io.stderr:write(log_entry)

    -- Also append to log file (size-limited)
    local f = io.open(CONFIG.log_file, "a")
    if f then
        f:write(log_entry)
        f:close()

        -- Rotate log if too large (> 1MB)
        local stat = io.popen("stat -f '%z' " .. CONFIG.log_file .. " 2>/dev/null || stat -c '%s' " .. CONFIG.log_file)
        local size = tonumber(stat:read("*a"))
        stat:close()

        if size and size > 1048576 then
            os.execute("mv " .. CONFIG.log_file .. " " .. CONFIG.log_file .. ".old")
        end
    end
end

-- =============================================================================
-- Router Identification
-- =============================================================================

local function get_router_mac()
    local f = io.popen("ip link show " .. CONFIG.monitor_interface .. " | grep 'link/ether' | awk '{print $2}'")
    local mac = f:read("*a"):gsub("%s+", "")
    f:close()
    return mac
end

-- =============================================================================
-- Event Collection
-- =============================================================================

local event_queue = {}

local function add_event(event_type, data)
    local event = {
        event_type = event_type,
        router_id = CONFIG.router_id,
        data = data,
        event_timestamp = os.date("!%Y-%m-%dT%H:%M:%S"),
    }

    table.insert(event_queue, event)

    -- Prevent memory overflow
    while #event_queue > CONFIG.max_queue_size do
        table.remove(event_queue, 1)
        log("WARN", "Event queue overflow, dropping oldest event")
    end

    log("DEBUG", string.format("Added %s event (queue: %d)", event_type, #event_queue))
end

-- Collect probe requests (using iw scan results)
local function collect_probe_requests()
    if not CONFIG.collect_probe_requests then
        return
    end

    -- Parse iw scan results for probe requests
    -- This is a simplified version; full implementation would monitor hostapd logs
    local f = io.popen("iw " .. CONFIG.monitor_interface .. " scan 2>/dev/null | grep -E 'SSID|signal|BSS'")
    local output = f:read("*a")
    f:close()

    if output and output ~= "" then
        -- Simple parsing (production would use more robust parsing)
        for bss, ssid, signal in output:gmatch("BSS ([%x:]+).-SSID: ([^\n]*).-signal: ([%-]?%d+)") do
            add_event("probe_request", {
                client_mac = bss,
                ssid = ssid,
                signal = tonumber(signal),
            })
        end
    end
end

-- Collect interface statistics
local function collect_interface_stats()
    if not CONFIG.collect_interface_stats then
        return
    end

    local stats = {}

    -- Get interface stats via /proc
    local f = io.open("/proc/net/dev", "r")
    if f then
        for line in f:lines() do
            if line:match(CONFIG.monitor_interface .. ":") then
                local iface, rx_bytes, rx_packets, tx_bytes, tx_packets =
                    line:match("(%w+):%s*(%d+)%s+(%d+)%s+%d+%s+%d+%s+%d+%s+%d+%s+%d+%s+%d+%s+(%d+)%s+(%d+)")

                if iface then
                    stats.interface = iface
                    stats.rx_bytes = tonumber(rx_bytes)
                    stats.rx_packets = tonumber(rx_packets)
                    stats.tx_bytes = tonumber(tx_bytes)
                    stats.tx_packets = tonumber(tx_packets)
                end
                break
            end
        end
        f:close()
    end

    -- Get connected clients (via hostapd)
    local client_count = 0
    local clients_f = io.popen("hostapd_cli all_sta 2>/dev/null | grep -c '^[0-9a-f][0-9a-f]:'")
    if clients_f then
        client_count = tonumber(clients_f:read("*a")) or 0
        clients_f:close()
    end
    stats.client_count = client_count

    if next(stats) ~= nil then
        add_event("interface_stats", stats)
    end
end

-- =============================================================================
-- Remote Communication
-- =============================================================================

local function send_events_to_remote()
    if #event_queue == 0 then
        return
    end

    -- Take batch from queue
    local batch = {}
    for i = 1, math.min(CONFIG.batch_size, #event_queue) do
        table.insert(batch, table.remove(event_queue, 1))
    end

    -- Send each event individually (HTTP API expects one event per request)
    local success_count = 0
    for _, event in ipairs(batch) do
        local json_data = json.encode(event)
        local url = string.format("http://%s:%s/api/router/telemetry", CONFIG.remote_host, CONFIG.remote_port)

        -- Use curl for HTTP POST
        local cmd = string.format(
            "curl -s -X POST -H 'Content-Type: application/json' -H 'X-API-Key: %s' -d '%s' %s",
            CONFIG.api_key,
            json_data:gsub("'", "'\\''"),  -- Escape single quotes
            url
        )

        local result = os.execute(cmd .. " >/dev/null 2>&1")
        if result == 0 then
            success_count = success_count + 1
        else
            -- Put event back in queue
            table.insert(event_queue, 1, event)
            log("ERROR", "Failed to send event to remote host")
        end
    end

    if success_count > 0 then
        log("INFO", string.format("Sent %d events to remote host", success_count))
    end
end

-- =============================================================================
-- Main Loop
-- =============================================================================

local function main()
    log("INFO", "Starting Beryl AX telemetry collector")

    -- Initialize router ID
    CONFIG.router_id = get_router_mac()
    log("INFO", "Router ID: " .. CONFIG.router_id)

    -- Create temp directory
    os.execute("mkdir -p " .. CONFIG.temp_dir)

    -- Main collection loop
    local iteration = 0
    while true do
        iteration = iteration + 1

        -- Collect events
        local start_time = socket.gettime()

        collect_probe_requests()
        collect_interface_stats()

        -- Send events to remote host
        if #event_queue > 0 then
            send_events_to_remote()
        end

        local elapsed = socket.gettime() - start_time
        log("DEBUG", string.format("Iteration %d completed in %.2fs (queue: %d)", iteration, elapsed, #event_queue))

        -- Sleep until next interval
        local sleep_time = math.max(0, CONFIG.scan_interval - elapsed)
        socket.sleep(sleep_time)
    end
end

-- =============================================================================
-- Entry Point
-- =============================================================================

-- Load config file if provided
if arg[1] then
    log("INFO", "Loading config from: " .. arg[1])
    -- TODO: Implement config file loading
end

-- Run main loop with error handling
local status, err = pcall(main)
if not status then
    log("ERROR", "Fatal error: " .. tostring(err))
    os.exit(1)
end
