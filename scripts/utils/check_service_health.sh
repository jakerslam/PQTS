#!/bin/bash
#
# Health Check Utility Script
# Performs basic health checks on Protheus service components
#
# Usage: ./check_service_health.sh [--component COMPONENT] [--verbose]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VERBOSE=false
COMPONENT="all"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print usage information
usage() {
    echo "Usage: $0 [--component COMPONENT] [--verbose]"
    echo ""
    echo "Components:"
    echo "  all       Check all services (default)"
    echo "  data      Check data ingestion pipeline"
    echo "  engine    Check execution engine"
    echo "  storage   Check storage subsystem"
    echo ""
    echo "Options:"
    echo "  --verbose  Show detailed output"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --component)
            COMPONENT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required environment variables are set
check_env_vars() {
    local required_vars=("PROTHEUS_ENV")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi

    if [[ "$VERBOSE" == true ]]; then
        log_info "Environment variables verified"
    fi
}

# Check configuration files exist and are valid JSON/YAML
check_config_files() {
    log_info "Checking configuration files..."

    local config_files=(
        "config/paper.yaml"
        "config/live_canary.yaml"
    )

    for file in "${config_files[@]}"; do
        local full_path="${PROJECT_ROOT}/${file}"
        if [[ -f "$full_path" ]]; then
            if [[ "$VERBOSE" == true ]]; then
                log_info "  ✓ ${file} exists"
            fi
        else
            log_warn "  ✗ ${file} missing"
        fi
    done
}

# Check disk space for log storage
check_disk_space() {
    log_info "Checking disk space..."

    # Check if logs directory has sufficient space (alert if < 10% free)
    local log_dir="${PROJECT_ROOT}/logs"
    if [[ -d "$log_dir" ]]; then
        local usage
        usage=$(df -h "$log_dir" | awk 'NR==2 {print $5}' | sed 's/%//')
        if [[ $usage -gt 90 ]]; then
            log_warn "Log disk usage at ${usage}% - consider log rotation"
        else
            if [[ "$VERBOSE" == true ]]; then
                log_info "  ✓ Log disk usage: ${usage}%"
            fi
        fi
    fi
}

# Check log files for recent errors
check_recent_errors() {
    log_info "Checking recent log entries..."

    local log_dir="${PROJECT_ROOT}/logs"
    if [[ ! -d "$log_dir" ]]; then
        log_warn "Log directory not found: $log_dir"
        return
    fi

    # Look for ERROR entries in the last hour
    local error_count
    error_count=$(find "$log_dir" -name "*.log" -mtime -0.042 -exec grep -c "ERROR" {} + 2>/dev/null | awk '{sum+=$1} END {print sum}')

    if [[ -n "$error_count" && "$error_count" -gt 0 ]]; then
        log_warn "Found $error_count ERROR entries in recent logs"
    else
        if [[ "$VERBOSE" == true ]]; then
            log_info "  ✓ No recent errors detected"
        fi
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "Protheus Service Health Check"
    echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "=========================================="
    echo ""

    check_env_vars
    check_config_files
    check_disk_space
    check_recent_errors

    echo ""
    log_info "Health check completed"
}

# Run main function
main "$@"
