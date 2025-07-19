#!/bin/bash

# SDWire Test Suite Runner
# Simple script to help run SDWire tests

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Banner
echo "═══════════════════════════════════════════════════════════"
echo "                   SDWire Test Suite"
echo "═══════════════════════════════════════════════════════════"
echo

# Check prerequisites
echo -e "${BLUE}[INFO]${NC} Checking prerequisites..."

# Check if sdwire command exists
if ! command -v sdwire >/dev/null 2>&1; then
    echo -e "${RED}[ERROR]${NC} sdwire command not found in PATH"
    echo "Please install the SDWire CLI tool first."
    exit 1
fi

# Check for connected devices
DEVICE_COUNT=$(sdwire list 2>/dev/null | tail -n +2 | grep -c . || echo "0")
if [ "$DEVICE_COUNT" -eq 0 ]; then
    echo -e "${RED}[ERROR]${NC} No SDWire devices found"
    echo "Please connect at least one SDWire device and try again."
    exit 1
fi

echo -e "${GREEN}[✓]${NC} sdwire command found"
echo -e "${GREEN}[✓]${NC} Found $DEVICE_COUNT SDWire device(s)"
echo

# Show connected devices
echo -e "${CYAN}Connected devices:${NC}"
sdwire list | while read -r line; do
    if [[ "$line" == Serial* ]]; then
        echo "  $line"
    elif [ -n "$line" ]; then
        echo "  $line"
    fi
done
echo

# Show test options
echo -e "${YELLOW}Available tests:${NC}"
echo
echo "  1) Comprehensive Test (test_sdwire.sh)"
echo "     • Full automated test suite"
echo "     • Tests all CLI commands and functionality"
echo "     • Automated pass/fail reporting"
echo "     • No user interaction required"
echo "     • Best for CI/automated testing"
echo
echo "  2) Quick Interactive Test (quick_switch_test.sh)"
echo "     • Interactive switching test"
echo "     • User verification at each step"
echo "     • Real-time device status display"
echo "     • Manual verification of SD card accessibility"
echo "     • Best for manual testing and validation"
echo
echo "  3) Show device status only"
echo "     • Just run 'sdwire list' and exit"
echo
echo "  4) Exit"
echo

# Get user choice
while true; do
    echo -n -e "${BLUE}Select test to run [1-4]:${NC} "
    read -r choice

    case $choice in
        1)
            echo
            echo -e "${BLUE}[INFO]${NC} Running comprehensive test suite..."
            echo -e "${YELLOW}This will run all automated tests.${NC}"
            echo
            if [ -x "./test_sdwire.sh" ]; then
                ./test_sdwire.sh
            else
                echo -e "${RED}[ERROR]${NC} test_sdwire.sh not found or not executable"
                exit 1
            fi
            break
            ;;
        2)
            echo
            echo -e "${BLUE}[INFO]${NC} Running quick interactive test..."
            echo -e "${YELLOW}This test requires user interaction.${NC}"
            echo -e "${YELLOW}You will be prompted to verify SD card accessibility.${NC}"
            echo
            if [ -x "./quick_switch_test.sh" ]; then
                ./quick_switch_test.sh
            else
                echo -e "${RED}[ERROR]${NC} quick_switch_test.sh not found or not executable"
                exit 1
            fi
            break
            ;;
        3)
            echo
            echo -e "${BLUE}[INFO]${NC} Current device status:"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            sdwire list
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo
            echo -e "${GREEN}[INFO]${NC} Done."
            break
            ;;
        4)
            echo -e "${BLUE}[INFO]${NC} Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} Invalid choice. Please select 1-4."
            ;;
    esac
done

echo
echo -e "${GREEN}[COMPLETE]${NC} Test execution finished."
echo "═══════════════════════════════════════════════════════════"
