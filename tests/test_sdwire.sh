#!/bin/bash

# SDWire Comprehensive Test Script
# Tests all functionality of the sdwire CLI tool

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

echo "==========================================="
echo "SDWire CLI Comprehensive Test Suite"
echo "==========================================="
echo

# Simple test function
test_command() {
    local test_name="$1"
    local command="$2"
    local expected_exit="$3"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $test_name"

    if [ -z "$expected_exit" ]; then
        expected_exit=0
    fi

    set +e
    eval "$command" >/dev/null 2>&1
    actual_exit=$?
    set -e

    if [ $actual_exit -eq $expected_exit ]; then
        echo -e "${GREEN}[PASS]${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $test_name (exit code: $actual_exit, expected: $expected_exit)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 1: Check if sdwire command exists
echo -e "${BLUE}[INFO]${NC} Checking if sdwire command is available..."
if command -v sdwire >/dev/null 2>&1; then
    echo -e "${GREEN}[PASS]${NC} sdwire command found"
else
    echo -e "${RED}[FAIL]${NC} sdwire command not found in PATH"
    exit 1
fi

# Test 2: Version command
test_command "sdwire --version" "sdwire --version"

# Test 3: Help command
test_command "sdwire --help" "sdwire --help"

# Test 4: List command
test_command "sdwire list" "sdwire list"

# Get device information
echo -e "${BLUE}[INFO]${NC} Gathering device information..."
DEVICE_OUTPUT=$(sdwire list 2>/dev/null | tail -n +2)
DEVICE_COUNT=$(echo "$DEVICE_OUTPUT" | grep -c . || echo "0")

echo -e "${BLUE}[INFO]${NC} Found $DEVICE_COUNT SDWire device(s)"

if [ "$DEVICE_COUNT" -eq 0 ]; then
    echo -e "${RED}[ERROR]${NC} No SDWire devices found. Please connect devices and try again."
    exit 1
fi

# Display found devices
echo -e "${BLUE}[INFO]${NC} Connected devices:"
echo "$DEVICE_OUTPUT" | while read -r line; do
    if [ -n "$line" ]; then
        serial=$(echo "$line" | awk '{print $1}')
        info=$(echo "$line" | awk '{print $2}')
        block_dev=$(echo "$line" | awk '{print $3}')
        echo "  • Serial: $serial, Info: $info, Block: $block_dev"
    fi
done

# Get device serials
DEVICE_SERIALS=($(echo "$DEVICE_OUTPUT" | awk '{print $1}' | grep -v "^$"))

# Test 5: Test switching with multiple devices (should fail without serial)
if [ "$DEVICE_COUNT" -gt 1 ]; then
    test_command "Switch without serial (multiple devices - should fail)" "sdwire switch host" 2
else
    echo -e "${YELLOW}[SKIP]${NC} Multiple device test (only one device connected)"
fi

# Test 6: Test invalid serial
test_command "Switch with invalid serial (should fail)" "sdwire switch -s 'invalid_serial_123' host" 2

# Test switching for each device
for serial in "${DEVICE_SERIALS[@]}"; do
    if [ -n "$serial" ]; then
        echo
        echo -e "${BLUE}[INFO]${NC} Testing device: $serial"
        echo "----------------------------------------"

        # Test switch to host
        test_command "Switch $serial to host" "sdwire switch -s '$serial' host"
        sleep 1

        # Test switch to target
        test_command "Switch $serial to target" "sdwire switch -s '$serial' target"
        sleep 1

        # Test alternative commands
        test_command "Switch $serial using 'ts' command" "sdwire switch -s '$serial' ts"
        sleep 1

        test_command "Switch $serial using 'dut' command" "sdwire switch -s '$serial' dut"
        sleep 1

        # Test switch off (should fail for SDWireC/SDWire3)
        test_command "Switch $serial off (should fail)" "sdwire switch -s '$serial' off" 1

        echo -e "${GREEN}[COMPLETE]${NC} Device $serial testing complete"
    fi
done

# Test single device commands (if only one device)
if [ "$DEVICE_COUNT" -eq 1 ]; then
    echo
    echo -e "${BLUE}[INFO]${NC} Testing single device commands (without serial)..."

    test_command "Single device switch to host" "sdwire switch host"
    sleep 1

    test_command "Single device switch to target" "sdwire switch target"
    sleep 1

    test_command "Single device switch using 'ts'" "sdwire switch ts"
    sleep 1

    test_command "Single device switch using 'dut'" "sdwire switch dut"
    sleep 1
fi

# Test help for switch command
test_command "sdwire switch --help" "sdwire switch --help"

# Final device listing
echo
echo -e "${BLUE}[INFO]${NC} Final device status:"
sdwire list

# Test consistency (run list multiple times)
echo
echo -e "${BLUE}[INFO]${NC} Testing device detection consistency..."
list1=$(sdwire list 2>/dev/null)
sleep 1
list2=$(sdwire list 2>/dev/null)
sleep 1
list3=$(sdwire list 2>/dev/null)

if [ "$list1" = "$list2" ] && [ "$list2" = "$list3" ]; then
    echo -e "${GREEN}[PASS]${NC} Device detection consistency test"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}[FAIL]${NC} Device detection consistency test"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))

# Summary
echo
echo "==========================================="
echo "Test Summary"
echo "==========================================="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo -e "${YELLOW}Note: Some failures may be expected (e.g., 'off' command failures)${NC}"
    exit 1
fi
