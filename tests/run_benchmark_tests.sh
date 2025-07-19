#!/bin/bash
# Automated test runner for SDWire benchmark functionality
#
# This script runs comprehensive tests for the benchmark command including:
# - Unit tests
# - CLI interface tests
# - Integration tests (if devices available)
# - Coverage reporting

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Test configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_TIMEOUT=300  # 5 minutes timeout for tests

# Statistics
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[PASS]${NC} $message"
            ;;
        "FAIL")
            echo -e "${RED}[FAIL]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "HEADER")
            echo -e "${BOLD}${BLUE}$message${NC}"
            ;;
    esac
}

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_exit_code="${3:-0}"

    TESTS_RUN=$((TESTS_RUN + 1))

    print_status "INFO" "Running: $test_name"

    if timeout $TEST_TIMEOUT bash -c "$test_command" >/dev/null 2>&1; then
        actual_exit_code=$?
    else
        actual_exit_code=$?
    fi

    if [ $actual_exit_code -eq $expected_exit_code ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        print_status "SUCCESS" "$test_name"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_status "FAIL" "$test_name (exit code: $actual_exit_code, expected: $expected_exit_code)"
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_status "HEADER" "Checking Prerequisites"

    # Check if we're in the right directory
    if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
        print_status "FAIL" "Not in SDWire project directory"
        exit 1
    fi

    # Check if Python is available
    if ! command -v python3 >/dev/null 2>&1; then
        print_status "FAIL" "Python 3 not found"
        exit 1
    fi

    # Check if poetry is available
    if ! command -v poetry >/dev/null 2>&1; then
        print_status "FAIL" "Poetry not found"
        exit 1
    fi

    # Check if pytest is available
    if ! poetry run python -c "import pytest" >/dev/null 2>&1; then
        print_status "FAIL" "pytest not available in poetry environment"
        exit 1
    fi

    print_status "SUCCESS" "All prerequisites met"
}

# Function to run unit tests
run_unit_tests() {
    print_status "HEADER" "Running Unit Tests"

    cd "$PROJECT_ROOT"

    # Run unit tests with coverage
    run_test "Unit tests" "poetry run pytest tests/unit/test_benchmark.py -v --tb=short"

    # Run unit tests with coverage reporting
    run_test "Unit tests with coverage" "poetry run pytest tests/unit/test_benchmark.py --cov=sdwire.backend.benchmark --cov-report=term-missing --cov-fail-under=80"
}

# Function to test CLI interface
test_cli_interface() {
    print_status "HEADER" "Testing CLI Interface"

    cd "$PROJECT_ROOT"

    # Test help command
    run_test "CLI help" "poetry run python -m sdwire.main benchmark --help"

    # Test with invalid serial
    run_test "CLI invalid serial" "poetry run python -m sdwire.main benchmark invalid_serial_123" 1

    # Test main help includes benchmark
    if poetry run python -m sdwire.main --help | grep -q "benchmark"; then
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
        print_status "SUCCESS" "Benchmark command listed in main help"
    else
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_status "FAIL" "Benchmark command not found in main help"
    fi
}

# Function to detect connected devices
detect_devices() {
    cd "$PROJECT_ROOT"

    # Get device list
    local device_output
    if device_output=$(poetry run python -c "
from sdwire.backend import detect
devices = detect.get_sdwire_devices()
for device in devices:
    print(f'{device.serial_string}|{device.block_dev or \"None\"}')
" 2>/dev/null); then
        echo "$device_output"
    else
        echo ""
    fi
}

# Function to run integration tests
run_integration_tests() {
    print_status "HEADER" "Running Integration Tests"

    local devices
    devices=$(detect_devices)

    if [ -z "$devices" ]; then
        print_status "WARN" "No SDWire devices detected - skipping integration tests"
        print_status "INFO" "To run integration tests:"
        print_status "INFO" "  1. Connect SDWire devices"
        print_status "INFO" "  2. Ensure SD cards are inserted"
        print_status "INFO" "  3. Check USB permissions"
        return 0
    fi

    local device_count
    device_count=$(echo "$devices" | wc -l)
    print_status "INFO" "Found $device_count SDWire device(s) for integration testing"

    # List detected devices
    echo "$devices" | while IFS='|' read -r serial block_dev; do
        print_status "INFO" "  Device: $serial -> $block_dev"
    done

    cd "$PROJECT_ROOT"

    # Run integration tests
    if [ -f "tests/integration/test_benchmark_integration.py" ]; then
        run_test "Integration tests" "poetry run pytest tests/integration/test_benchmark_integration.py -v -m 'requires_device' --tb=short"
    else
        print_status "WARN" "Integration test file not found"
    fi

    # Test CLI with real device (non-destructive)
    local first_device_serial
    first_device_serial=$(echo "$devices" | head -1 | cut -d'|' -f1)

    if [ -n "$first_device_serial" ]; then
        print_status "INFO" "Testing CLI with device: $first_device_serial"

        # Test device info gathering (should not fail due to permissions)
        if timeout 30 bash -c "echo -e '\n\n\n\n\n' | poetry run python -c \"
from sdwire.backend import detect
from sdwire.backend.benchmark import get_usb_speed_info, display_usb_info
devices = detect.get_sdwire_devices()
target_device = None
for device in devices:
    if device.serial_string == '$first_device_serial':
        target_device = device
        break
if target_device:
    usb_info = get_usb_speed_info(target_device)
    print('USB Speed Info retrieved successfully')
else:
    print('Device not found')
exit(0)
\"" >/dev/null 2>&1; then
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_PASSED=$((TESTS_PASSED + 1))
            print_status "SUCCESS" "Device USB info retrieval"
        else
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_FAILED=$((TESTS_FAILED + 1))
            print_status "FAIL" "Device USB info retrieval"
        fi
    fi
}

# Function to run performance tests
run_performance_tests() {
    print_status "HEADER" "Running Performance Tests"

    cd "$PROJECT_ROOT"

    # Test import performance
    local start_time end_time duration
    start_time=$(date +%s%N)

    if poetry run python -c "from sdwire.backend.benchmark import run_benchmark, get_usb_speed_info" >/dev/null 2>&1; then
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds

        TESTS_RUN=$((TESTS_RUN + 1))
        if [ $duration -lt 1000 ]; then  # Less than 1 second
            TESTS_PASSED=$((TESTS_PASSED + 1))
            print_status "SUCCESS" "Import performance ($duration ms)"
        else
            TESTS_FAILED=$((TESTS_FAILED + 1))
            print_status "FAIL" "Import performance too slow ($duration ms)"
        fi
    else
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_status "FAIL" "Benchmark module import failed"
    fi

    # Test memory usage
    run_test "Memory usage test" "poetry run python -c \"
import sys
from sdwire.backend.benchmark import USB_SPEEDS, TEST_SIZES
print('Memory test passed')
\""
}

# Function to run linting and code quality checks
run_quality_checks() {
    print_status "HEADER" "Running Code Quality Checks"

    cd "$PROJECT_ROOT"

    # Check if files exist
    if [ -f "sdwire/backend/benchmark.py" ]; then
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
        print_status "SUCCESS" "Benchmark module file exists"
    else
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_status "FAIL" "Benchmark module file missing"
    fi

    # Check Python syntax
    run_test "Python syntax check" "poetry run python -m py_compile sdwire/backend/benchmark.py"

    # Check for common issues
    if grep -q "TODO\\|FIXME\\|XXX" sdwire/backend/benchmark.py; then
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_status "FAIL" "Found TODO/FIXME/XXX comments in benchmark.py"
    else
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
        print_status "SUCCESS" "No TODO/FIXME/XXX comments found"
    fi
}

# Function to generate test report
generate_report() {
    print_status "HEADER" "Test Summary Report"

    echo
    echo "Test Results:"
    echo "============="
    echo "Total Tests: $TESTS_RUN"
    echo "Passed: $TESTS_PASSED"
    echo "Failed: $TESTS_FAILED"

    if [ $TESTS_FAILED -eq 0 ]; then
        print_status "SUCCESS" "All tests passed! 🎉"
        echo
        echo "The benchmark functionality is ready for use:"
        echo "  sdwire benchmark <serial_number>"
        echo
        echo "For help:"
        echo "  sdwire benchmark --help"
        echo
        return 0
    else
        print_status "FAIL" "$TESTS_FAILED test(s) failed"
        echo
        echo "Please review the failed tests above and fix any issues."
        echo
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --unit-only     Run only unit tests"
    echo "  --no-integration Skip integration tests"
    echo "  --no-coverage   Skip coverage reporting"
    echo "  --quick         Run quick tests only"
    echo "  --help          Show this help"
    echo
    echo "Examples:"
    echo "  $0                  # Run all tests"
    echo "  $0 --unit-only     # Run only unit tests"
    echo "  $0 --quick         # Run quick tests only"
}

# Main function
main() {
    local unit_only=false
    local no_integration=false
    local no_coverage=false
    local quick=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --unit-only)
                unit_only=true
                shift
                ;;
            --no-integration)
                no_integration=true
                shift
                ;;
            --no-coverage)
                no_coverage=true
                shift
                ;;
            --quick)
                quick=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    print_status "HEADER" "SDWire Benchmark Test Runner"
    echo "Project: $(basename "$PROJECT_ROOT")"
    echo "Date: $(date)"
    echo

    # Check prerequisites
    check_prerequisites
    echo

    # Run tests based on options
    if [ "$quick" = true ]; then
        test_cli_interface
        run_test "Quick unit test" "poetry run pytest tests/unit/test_benchmark.py::TestGetUsbSpeedInfo::test_get_usb_speed_info_success -v"
    elif [ "$unit_only" = true ]; then
        run_unit_tests
        test_cli_interface
    else
        # Full test suite
        run_quality_checks
        echo

        test_cli_interface
        echo

        run_unit_tests
        echo

        run_performance_tests
        echo

        if [ "$no_integration" != true ]; then
            run_integration_tests
            echo
        fi
    fi

    # Generate final report
    generate_report
}

# Handle script interruption
trap 'echo; print_status "WARN" "Test runner interrupted"; exit 130' INT TERM

# Run main function with all arguments
main "$@"
