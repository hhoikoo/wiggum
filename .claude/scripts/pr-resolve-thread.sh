#!/usr/bin/env bash
set -euo pipefail

# Resolve one or more PR review threads by node ID.
# Usage: pr-resolve-thread.sh <thread-id> [<thread-id>...]

if [ $# -eq 0 ]; then
  echo "Usage: pr-resolve-thread.sh <thread-id> [<thread-id>...]" >&2
  exit 1
fi

for thread_id in "$@"; do
  # $threadId is a GraphQL variable reference, not a shell variable
  # shellcheck disable=SC2016
  resolved=$(gh api graphql \
    -F threadId="$thread_id" \
    -f query='
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { isResolved }
  }
}' --jq '.data.resolveReviewThread.thread.isResolved')
  echo "${thread_id} -> resolved=${resolved}"
done
