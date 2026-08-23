#!/usr/bin/env sh
set -eu

STRICT=0

usage() {
  cat <<'EOF'
Usage:
  validate-bootstrap.sh [--strict] [project-root]

Checks whether starter-pack placeholders are still present in long-lived
workflow reference files.

Default mode prints warnings and exits 0. --strict exits 1 when warnings exist.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --strict)
      STRICT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -gt 0 ]; then
  ROOT=$1
else
  SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
  ROOT=$(CDPATH= cd "$SCRIPT_DIR/../.." && pwd)
fi

WARNINGS=0

warn() {
  WARNINGS=$((WARNINGS + 1))
  printf 'warning: %s\n' "$1" >&2
}

check_file() {
  rel=$1
  file=$ROOT/$rel

  if [ ! -f "$file" ]; then
    warn "missing bootstrap reference: $rel"
    return
  fi

  if grep -Eq '待填写|TODO|TBD' "$file"; then
    warn "placeholder remains in $rel"
  fi
}

check_required_line() {
  rel=$1
  pattern=$2
  label=$3
  file=$ROOT/$rel

  if [ ! -f "$file" ]; then
    return
  fi

  if ! grep -Eq "$pattern" "$file"; then
    warn "$label missing in $rel"
  fi
}

check_file ".agents/references/project-conventions.md"
check_file ".agents/references/architecture-notes.md"
check_file ".agents/references/requirements-index.md"
check_file ".agents/references/feature-index.md"
check_file ".agents/references/tooling-map.md"

check_required_line ".agents/references/project-conventions.md" '^Owner: .+' "Owner"
check_required_line ".agents/references/project-conventions.md" '^Source of truth: .+' "Source of truth"
check_required_line ".agents/references/project-conventions.md" '^Refresh when: .+' "Refresh when"
check_required_line ".agents/references/project-conventions.md" 'Main build command: .+' "Main build command"
check_required_line ".agents/references/project-conventions.md" 'Main test command: .+' "Main test command"
check_required_line ".agents/references/requirements-index.md" 'Requirement ID' "Requirement map"
check_required_line ".agents/references/feature-index.md" 'Feature ID' "Feature map"
check_required_line ".agents/references/tooling-map.md" '^Owner: .+' "Owner"
check_required_line ".agents/references/tooling-map.md" '^Source of truth: .+' "Source of truth"
check_required_line ".agents/references/tooling-map.md" '^Refresh when: .+' "Refresh when"
check_required_line ".agents/references/tooling-map.md" '阻断策略' "Blocking policy"

if [ "$WARNINGS" -eq 0 ]; then
  printf 'bootstrap validation passed\n'
  exit 0
fi

printf 'bootstrap validation found %s warning(s)\n' "$WARNINGS" >&2

if [ "$STRICT" -eq 1 ]; then
  exit 1
fi

exit 0
