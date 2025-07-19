#!/bin/bash

# Quick SDWire Switch Test Script
# Simple script to quickly test switching functionality

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WAIT]${NC} $1"
}

# Function to show current device status
show_devices() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Current device status:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    sdwire list
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
}

# Function to wait with countdown
wait_with_countdown() {
    local seconds=$1
    local message="${2:-Waiting}"

    for i in $(seq $seconds -1 1); do
        echo -ne "\r$message... ${i}s"
        sleep 1
    done
    echo -ne "\r$message... Done!\n"
}

echo "==============================="
echo "Quick SDWire Switch Test"
echo "==============================="
echo

# Show initial device status
log_info "Initial device status:"
show_devices

# Get device serials
DEVICE_SERIALS=($(sdwire list | tail -n +2 | awk '{print $1}' | grep -v "^$"))
DEVICE_COUNT=${#DEVICE_SERIALS[@]}

if [ $DEVICE_COUNT -eq 0 ]; then
    echo "No SDWire devices found!"
    exit 1
fi

log_info "Found $DEVICE_COUNT device(s): ${DEVICE_SERIALS[*]}"
echo

# Test each device
for serial in "${DEVICE_SERIALS[@]}"; do
    # Get device info from sdwire list
    DEVICE_INFO=$(sdwire list | grep "$serial" | awk '{print $2}')

    echo "Testing device: $serial"
    echo "Device info: $DEVICE_INFO"
    echo "------------------------"

    # Switch to host mode
    log_info "Switching device [$serial] to HOST mode..."
    sdwire switch -s "$serial" host
    log_success "Device [$serial] switched to HOST mode"
    wait_with_countdown 3 "Waiting for switch to complete"
    show_devices

    log_warning "Verify SD card is accessible on HOST system for device [$serial]"
    read -p "Press Enter when verified..."
    echo

    # Switch to target mode
    log_info "Switching device [$serial] to TARGET mode..."
    sdwire switch -s "$serial" target
    log_success "Device [$serial] switched to TARGET mode"
    wait_with_countdown 3 "Waiting for switch to complete"
    show_devices

    log_warning "Verify SD card is accessible on TARGET device for [$serial]"
    read -p "Press Enter when verified..."
    echo

    # Test alternative commands
    log_info "Testing 'ts' command on device [$serial] (should switch to host)..."
    sdwire switch -s "$serial" ts
    log_success "Device [$serial] switched using 'ts' command"
    wait_with_countdown 2

    log_info "Testing 'dut' command on device [$serial] (should switch to target)..."
    sdwire switch -s "$serial" dut
    log_success "Device [$serial] switched using 'dut' command"
    wait_with_countdown 2

    echo "✅ Device $serial test complete!"
    echo
done

# If single device, test without serial specification
if [ $DEVICE_COUNT -eq 1 ]; then
    log_info "Testing single device commands without serial..."

    sdwire switch host
    log_success "Switch to host without serial: OK"
    wait_with_countdown 2

    sdwire switch target
    log_success "Switch to target without serial: OK"
    wait_with_countdown 2
fi

# If single device, test without serial specification
if [ $DEVICE_COUNT -eq 1 ]; then
    log_info "Testing single device commands without serial..."

    sdwire switch host
    log_success "Switch to host without serial: OK"
    wait_with_countdown 2

    sdwire switch target
    log_success "Switch to target without serial: OK"
    wait_with_countdown 2
fi

log_info "Final device status:"
show_devices

echo "═════════════════════════════════════════════════════════"
log_success "Quick switch test completed!"
echo "✅ All $DEVICE_COUNT device(s) tested successfully:"
for serial in "${DEVICE_SERIALS[@]}"; do
    echo "   • $serial"
done
echo "═════════════════════════════════════════════════════════"
