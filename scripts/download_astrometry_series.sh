#!/usr/bin/env bash
# download_astrometry_series.sh (safe-to-run version)
# NOTE: RUN this script (./download_astrometry_series.sh), do NOT "source" it.
# It will refuse to run if you accidentally source it into your interactive shell.

# If the script is sourced, BASH_SOURCE[0] != $0. Detect that and bail out.
if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  cat >&2 <<'EOF'
ERROR: This script must be executed, not sourced.
If you ran ". download_astrometry_series.sh" or "source download_astrometry_series.sh",
your interactive shell will inherit errexit/nounset and might exit on error.
Run it instead like one of these:
  ./download_astrometry_series.sh
  bash download_astrometry_series.sh
EOF
  # If sourced, "return" works; if executed, return will fail and the '|| exit 1' will run.
  return 1 2>/dev/null || exit 1
fi

set -euo pipefail
trap 'rc=$?; echo "ERROR: script failed at line ${LINENO} (exit code ${rc})." >&2; exit ${rc}' ERR

# --- defaults (can be overridden by args) ---
SERIES="${1:-4100}"
DIR="./${SERIES}"
JOBS=4
FLAT=false

# parse optional flags (after series arg)
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --flat) FLAT=true; shift ;;
    --dir) DIR="$2"; shift 2 ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --help|-h) echo "Usage: $0 [series] [--flat] [--dir DIR] [--jobs N]"; exit 0 ;;
    *) echo "Unknown option: $1"; echo "Usage: $0 [series] [--flat] [--dir DIR] [--jobs N]"; exit 1 ;;
  esac
done

BASE_URL="https://data.astrometry.net/${SERIES}/"
if [[ "$FLAT" = true ]]; then
  DOWNLOAD_DIR="."
else
  DOWNLOAD_DIR="${DIR}"
fi

# Ensure required commands exist (fail early but only exit the script)
for cmd in curl wget; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: required command '$cmd' is not installed. Please install it and re-run." >&2
    exit 2
  fi
done

mkdir -p "${DOWNLOAD_DIR}"

echo "Fetching listing from ${BASE_URL} ..."
LISTING=$(curl -fsSL "${BASE_URL}") || { echo "Failed to fetch ${BASE_URL}" >&2; exit 3; }

# extract .fits hrefs (robust-ish)
URLS=$(printf "%s\n" "${LISTING}" \
  | sed -n 's/.*href="\([^"]*\.fits\)".*/\1/p' \
  | sort -u)

if [[ -z "${URLS}" ]]; then
  echo "No .fits links found at ${BASE_URL}. Exiting." >&2
  exit 4
fi

# build absolute URLs array
ABS_URLS=()
while IFS= read -r u; do
  [[ -z "$u" ]] && continue
  if [[ "$u" =~ ^https?:// ]]; then
    ABS_URLS+=("$u")
  else
    u="${u#./}"
    u="${u#/}"
    ABS_URLS+=("${BASE_URL}${u}")
  fi
done <<< "$URLS"

echo "Found ${#ABS_URLS[@]} .fits files. Download dir: ${DOWNLOAD_DIR}"
pushd "${DOWNLOAD_DIR}" >/dev/null

if command -v aria2c >/dev/null 2>&1; then
  echo "Using aria2c for parallel downloads..."
  TMPURLS="$(mktemp)"
  printf "%s\n" "${ABS_URLS[@]}" > "${TMPURLS}"
  aria2c --file-allocation=none -x16 -s16 -j"${JOBS}" -i "${TMPURLS}" || echo "aria2c reported errors (check output)."
  rm -f "${TMPURLS}"
else
  echo "aria2c not found — falling back to wget + xargs (parallel=${JOBS})..."
  printf "%s\n" "${ABS_URLS[@]}" \
    | xargs -n1 -P"${JOBS}" -I{} bash -c 'echo "-> downloading: {}"; wget -c --no-verbose --show-progress "{}" || echo "WARNING: wget failed for {}"'
fi

popd >/dev/null
echo "Done. Files saved under: ${DOWNLOAD_DIR}"
