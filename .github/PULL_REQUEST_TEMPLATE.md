<!-- required: Overview -->
## Overview

<!--
Provide a 1-3 sentence summary of what this PR does.
Focus on the "what" - what functionality is added/changed/fixed?
Example: "Adds retry logic to the gRPC client with configurable backoff and jitter."
-->

<!-- required: Problem Statement -->
## Problem Statement

<!--
Briefly explain WHY this change is needed. Reference the ticket requirements.
- What was broken or missing?
- What user/developer pain point does this address?
Keep it concise - 2-4 bullet points max.
-->

## Architecture

<!--
Optional section - include for features that introduce new components or change system design.
Skip for simple bugfixes, small refactors, or documentation changes.

If included:
1. Add a Mermaid diagram showing component relationships or data flow
2. Follow with a brief explanation of key design decisions
3. Call out any trade-offs or alternatives considered
-->

<!--
Add additional sections as needed for your PR, especially if Architecture section is added. Examples:
## Implementation Notes
## Migration Guide
## Breaking Changes
## Testing Notes
-->

---

<!-- required: Checklist (if applicable) -->
## Checklist (if applicable)

<!-- required-checklist -->
* [ ] Mention to the original issue
* [ ] PR name with proper formatting
    * Check `.github/workflows/pr-autofix-title.yml` for more info
* [ ] Tests pass locally (`uv run pytest`)
* [ ] Linting passes (`uv run ruff check src/ tests/`)
* [ ] Type checking passes (`uv run pyright`)
* [ ] Documentation added or modified appropriately
<!-- /required-checklist -->

<!-- Issue linking (auto-added by tooling): -->
