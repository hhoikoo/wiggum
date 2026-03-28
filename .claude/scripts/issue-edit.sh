#!/usr/bin/env bash
set -euo pipefail

# Edit a GitHub issue's title and/or body.
# Usage: edit.sh <ISSUE_NUMBER> [-s <SUMMARY>] [-b <BODY_FILE>]

issue_number="${1:?Usage: edit.sh <ISSUE_NUMBER> [-s <SUMMARY>] [-b <BODY_FILE>]}"
shift

summary=""
body_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s) summary="$2"; shift 2 ;;
    -b) body_file="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

args=(issue edit "$issue_number")

if [[ -n "$summary" ]]; then
  args+=(--title "$summary")
fi

if [[ -n "$body_file" ]]; then
  args+=(--body-file "$body_file")
fi

gh "${args[@]}"
