#!/usr/bin/env bash
set -euo pipefail

# View a GitHub issue and return JSON matching the issue-tracker contract.
# Usage: view.sh <ISSUE_NUMBER>

issue_number="${1:?Usage: view.sh <ISSUE_NUMBER>}"

gh issue view "$issue_number" --json number,title,body,labels,state | jq '{
  key: .number,
  summary: .title,
  description: .body,
  type: (
    [.labels[].name] |
    if any(. == "type:epic") then "Epic"
    elif any(. == "type:story") then "Story"
    elif any(. == "type:bug") then "Bug"
    elif any(. == "type:task") then "Task"
    else "Task"
    end
  ),
  status: .state,
  parent: ""
}'
