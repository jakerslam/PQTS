#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Create GitHub issues from docs/ISSUE_BACKLOG.md.

Usage:
  scripts/create_github_issues_from_backlog.sh [--dry-run|--execute] [--limit N] [--repo OWNER/REPO] [--backlog PATH]

Options:
  --dry-run        Parse and print what would be created (default).
  --execute        Actually create issues via `gh issue create`.
  --limit N        Process only the first N backlog entries.
  --repo R         Override repo target (default: current gh repo).
  --backlog PATH   Override backlog file path (default: docs/ISSUE_BACKLOG.md).
  -h, --help       Show this help.

Examples:
  scripts/create_github_issues_from_backlog.sh --dry-run --limit 5
  scripts/create_github_issues_from_backlog.sh --execute
EOF
}

MODE="dry-run"
LIMIT=0
REPO=""
BACKLOG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry-run" ;;
    --execute) MODE="execute" ;;
    --limit)
      shift
      LIMIT="${1:-0}"
      ;;
    --repo)
      shift
      REPO="${1:-}"
      ;;
    --backlog)
      shift
      BACKLOG="${1:-}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
BACKLOG="${BACKLOG:-$ROOT_DIR/docs/ISSUE_BACKLOG.md}"

if [[ ! -f "$BACKLOG" ]]; then
  echo "Error: Backlog file not found: $BACKLOG" >&2
  exit 1
fi

existing_map_file="$(mktemp)"
existing_labels_file="$(mktemp)"
cleanup() {
  rm -f "$existing_map_file"
  rm -f "$existing_labels_file"
}
trap cleanup EXIT

lookup_existing_number() {
  local ticket_id="$1"
  awk -F'\t' -v id="$ticket_id" '$1 == id { print $2; exit }' "$existing_map_file"
}

label_exists() {
  local label="$1"
  grep -Fxq "$label" "$existing_labels_file"
}

if [[ "$MODE" == "execute" ]]; then
  if ! command -v gh >/dev/null 2>&1; then
    echo "Error: GitHub CLI (gh) is required in --execute mode." >&2
    exit 1
  fi

  if [[ -z "$REPO" ]]; then
    REPO="$(gh repo view --json nameWithOwner -q '.nameWithOwner')"
  fi

  if [[ -z "$REPO" ]]; then
    echo "Error: Could not determine target repo. Pass --repo OWNER/REPO." >&2
    exit 1
  fi

  gh label list --repo "$REPO" --limit 1000 --json name -q '.[].name' > "$existing_labels_file" || true

  while IFS=$'\t' read -r number title; do
    if [[ "$title" =~ ^(PQTS-[0-9]{3})[[:space:]] ]]; then
      printf "%s\t%s\n" "${BASH_REMATCH[1]}" "$number" >> "$existing_map_file"
    fi
  done < <(gh issue list --repo "$REPO" --state all --limit 1000 --json number,title -q '.[] | "\(.number)\t\(.title)"')
else
  REPO="${REPO:-dry-run}"
fi

total=0
created=0
skipped=0

while IFS= read -r -d $'\x1e' record; do
  [[ -z "$record" ]] && continue
  IFS=$'\x1f' read -r id title labels_raw depends_raw scope <<< "$record"
  [[ -z "$id" ]] && continue

  total=$((total + 1))
  if (( LIMIT > 0 && total > LIMIT )); then
    break
  fi

  issue_title="${id} ${title}"

  existing_num="$(lookup_existing_number "$id")"
  if [[ -n "$existing_num" ]]; then
    echo "SKIP ${id}: already exists as #${existing_num}"
    skipped=$((skipped + 1))
    continue
  fi

  labels_clean="${labels_raw//\`/}"
  labels_clean="${labels_clean// /}"
  IFS=',' read -r -a label_list <<< "$labels_clean"

  depends_clean="${depends_raw//\`/}"
  depends_clean="${depends_clean// /}"
  dep_section="- none"
  if [[ -n "$depends_clean" && "$depends_clean" != "none" ]]; then
    IFS=',' read -r -a dep_ids <<< "$depends_clean"
    dep_lines=()
    for dep in "${dep_ids[@]}"; do
      [[ -z "$dep" ]] && continue
      dep_num="$(lookup_existing_number "$dep")"
      if [[ "$MODE" == "execute" && -n "$dep_num" ]]; then
        dep_lines+=("- ${dep} (#${dep_num})")
      else
        dep_lines+=("- ${dep}")
      fi
    done
    if (( ${#dep_lines[@]} > 0 )); then
      dep_section="$(printf "%s\n" "${dep_lines[@]}")"
      dep_section="${dep_section%$'\n'}"
    fi
  fi

  if [[ "$title" == "[Docs]:"* ]]; then
    acceptance=$'- Referenced files are updated with accurate, current behavior.\n- Docs include links to concrete code paths/commands.\n- Docs are consistent with docs/TODO.md and docs/SRS.md.'
  else
    acceptance=$'- Behavior is implemented end-to-end and wired into existing runtime paths.\n- Tests are added/updated for changed behavior (unit/integration; e2e where relevant).\n- Telemetry/error handling and docs are updated for new/changed contracts.'
  fi

  body=$(cat <<EOF
## Scope
${scope}

## Dependencies
${dep_section}

## Acceptance Criteria
${acceptance}
EOF
)

  if [[ "$MODE" == "dry-run" ]]; then
    echo "DRY-RUN ${id}"
    echo "  Title: ${issue_title}"
    echo "  Labels: ${labels_clean}"
    echo "  Depends: ${depends_clean:-none}"
    continue
  fi

  cmd=(gh issue create --repo "$REPO" --title "$issue_title" --body "$body")
  skipped_label_list=()
  for label in "${label_list[@]}"; do
    [[ -z "$label" ]] && continue
    if label_exists "$label"; then
      cmd+=(--label "$label")
    else
      skipped_label_list+=("$label")
    fi
  done
  if (( ${#skipped_label_list[@]} > 0 )); then
    echo "WARN ${id}: skipping unavailable labels: $(IFS=,; echo "${skipped_label_list[*]}")"
  fi

  created_url="$("${cmd[@]}")"
  created_num="${created_url##*/}"
  printf "%s\t%s\n" "$id" "$created_num" >> "$existing_map_file"
  created=$((created + 1))
  echo "CREATED ${id}: #${created_num} (${created_url})"
done < <(
  awk '
    function flush() {
      if (id != "") {
        gsub(/`/, "", labels)
        gsub(/`/, "", depends)
        printf "%s\x1f%s\x1f%s\x1f%s\x1f%s\x1e", id, title, labels, depends, scope
      }
      id=""; title=""; labels=""; depends=""; scope=""
    }
    {
      if ($0 ~ /^### PQTS-[0-9][0-9][0-9] `.*`$/) {
        flush()
        line = $0
        sub(/^### /, "", line)
        id = line
        sub(/ .*/, "", id)
        title = line
        sub(/^[^ ]+ /, "", title)
        sub(/^`/, "", title)
        sub(/`$/, "", title)
        next
      }
      if (id == "") next
      if ($0 ~ /^- Labels: /) {
        labels = $0
        sub(/^- Labels: /, "", labels)
        next
      }
      if ($0 ~ /^- Depends on: /) {
        depends = $0
        sub(/^- Depends on: /, "", depends)
        next
      }
      if ($0 ~ /^- Scope: /) {
        scope = $0
        sub(/^- Scope: /, "", scope)
        next
      }
    }
    END { flush() }
  ' "$BACKLOG"
)

echo
echo "Summary:"
echo "  Mode:    ${MODE}"
echo "  Repo:    ${REPO}"
echo "  Backlog: ${BACKLOG}"
echo "  Parsed:  $(( total < LIMIT || LIMIT == 0 ? total : LIMIT ))"
echo "  Created: ${created}"
echo "  Skipped: ${skipped}"
