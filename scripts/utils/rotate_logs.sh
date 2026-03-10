#!/bin/bash
#
# Log Rotation Utility for Protheus Trading System
#
# Description:
#   Rotates log files to prevent disk space exhaustion while
#   preserving recent operational history for debugging.
#
# Usage:
#   ./rotate_logs.sh [--max-age-days N] [--dry-run]
#
# Author: Rohan Kapoor
# Last Updated: March 10, 2026
#

set -euo pipefail

# Configuration
LOG_DIR="${PROTHEUS_LOG_DIR:-logs}"
DEFAULT_MAX_AGE_DAYS=30
DRY_RUN=false
MAX_AGE_DAYS=$DEFAULT_MAX_AGE_DAYS

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --max-age-days)
            MAX_AGE_DAYS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate log directory exists
if [[ ! -d "$LOG_DIR" ]]; then
    echo "Error: Log directory not found: $LOG_DIR"
    exit 1
fi

# Create archive directory
ARCHIVE_DIR="$LOG_DIR/archive/$(date +%Y/%m)"
if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "$ARCHIVE_DIR"
fi

# Statistics
TOTAL_ROTATED=0
TOTAL_BYTES=0

# Find and rotate old log files
# TODO: Consider adding compression option for archived logs
# TODO: Add S3/cloud storage upload for long-term retention

find "$LOG_DIR" -type f -name "*.log" -mtime +7 | while read -r logfile; do
    filename=$(basename "$logfile")
    archive_name="${filename%.log}_$(date +%Y%m%d_%H%M%S).log.gz"
    archive_path="$ARCHIVE_DIR/$archive_name"
    
    filesize=$(stat -f%z "$logfile" 2>/dev/null || stat -c%s "$logfile" 2>/dev/null || echo "0")
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] Would archive: $filename ($filesize bytes)"
    else
        # Compress and move to archive
        gzip -c "$logfile" > "$archive_path"
        rm "$logfile"
        # Create new empty log file
        touch "$logfile"
        echo "Archived: $filename -> $archive_name"
    fi
    
    TOTAL_ROTATED=$((TOTAL_ROTATED + 1))
    TOTAL_BYTES=$((TOTAL_BYTES + filesize))
done

# Remove old archives beyond retention policy
if [[ "$DRY_RUN" == false ]]; then
    find "$LOG_DIR/archive" -type f -name "*.gz" -mtime +$MAX_AGE_DAYS -delete
fi

# Summary
if [[ "$DRY_RUN" == true ]]; then
    echo ""
    echo "[DRY RUN MODE] No changes were made"
    echo "Run without --dry-run to execute rotation"
else
    echo ""
    echo "Log rotation complete."
    echo "Archive location: $ARCHIVE_DIR"
fi
