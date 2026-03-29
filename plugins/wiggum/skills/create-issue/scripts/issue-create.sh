#!/usr/bin/env bash
set -euo pipefail

# Create a GitHub issue.
# Usage: create.sh -t <TYPE> -s <SUMMARY> [-b <BODY_FILE>] [-P <PARENT>] [-a <ASSIGNEE>] [-S <POINTS>] [-g <REPO>] [-l <LABEL>]...

type=""
summary=""
body_file=""
parent=""
assignee=""
labels=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t) type="$2"; shift 2 ;;
    -s) summary="$2"; shift 2 ;;
    -b) body_file="$2"; shift 2 ;;
    -P) parent="$2"; shift 2 ;;
    -a) assignee="$2"; shift 2 ;;
    -S) shift 2 ;;  # story points — not applicable
    -g) shift 2 ;;  # github repo — not applicable
    -l) labels+=("$2"); shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

: "${type:?-t TYPE is required}"
: "${summary:?-s SUMMARY is required}"

args=(issue create --title "$summary")

# Map type to a label
type_lower=$(echo "$type" | tr '[:upper:]' '[:lower:]')
args+=(--label "type:$type_lower")

if [[ -n "$body_file" ]]; then
  args+=(--body-file "$body_file")
fi

if [[ -n "$assignee" ]]; then
  args+=(--assignee "$assignee")
fi

for label in "${labels[@]+"${labels[@]}"}"; do
  args+=(--label "$label")
done

# Create the issue and extract the issue number from the URL
url=$(gh "${args[@]}")
child_number=$(echo "$url" | grep -oE '[0-9]+$')

# If parent is specified, add as sub-issue via GraphQL
if [[ -n "$parent" && -n "$child_number" ]]; then
  repo=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
  owner="${repo%%/*}"
  name="${repo##*/}"

  # Resolve parent and child node IDs
  get_issue_id() {
    # shellcheck disable=SC2016
    gh api graphql \
      -H "GraphQL-Features:sub_issues" \
      -f query='
        query($owner: String!, $name: String!, $number: Int!) {
          repository(owner: $owner, name: $name) {
            issue(number: $number) { id }
          }
        }
      ' \
      -f owner="$owner" \
      -f name="$name" \
      -F number="$1" \
      --jq '.data.repository.issue.id'
  }

  parent_id=$(get_issue_id "$parent")
  child_id=$(get_issue_id "$child_number")

  if [[ -n "$parent_id" && "$parent_id" != "null" && -n "$child_id" && "$child_id" != "null" ]]; then
    # shellcheck disable=SC2016
    gh api graphql \
      -H "GraphQL-Features:sub_issues" \
      -f query='
        mutation($parentId: ID!, $childId: ID!) {
          addSubIssue(input: { issueId: $parentId, subIssueId: $childId }) {
            issue { number }
            subIssue { number }
          }
        }
      ' \
      -f parentId="$parent_id" \
      -f childId="$child_id" \
      >/dev/null 2>&1 || echo "Warning: could not add as sub-issue of #${parent}" >&2
  fi
fi

echo "$child_number"
