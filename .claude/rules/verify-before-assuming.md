---
paths:
  - "**/*"
---
# Verify Before Assuming

Never rely on memory or training data when a definitive source is available. Look it up. Guessing leads to incompatible code, broken scripts, wrong API calls, and misleading explanations.

## General Principle

If a claim is not trivially obvious, verify it before stating it or acting on it. This applies to code, libraries, external projects, tools, protocols, standards, and any factual assertion.

- **Library APIs and behavior**: Read the actual source or docs. Do not guess function signatures, parameter names, return types, default values, or side effects.
- **External projects and repos**: Use web search, `gh`, or fetch the repo's docs/README before making claims about how another project works, what it supports, or how to integrate with it.
- **Standards and protocols**: Look up the spec or authoritative reference rather than paraphrasing from memory. Details like header names, status codes, encoding rules, and field formats are easy to get slightly wrong.
- **Non-programming facts**: When the user asks about something outside of code, search the web or consult authoritative sources rather than generating an answer from training data alone. Flag uncertainty explicitly if verification is not possible.

## Project-Specific Sources of Truth

| Information needed | Check this file |
|-------------------|-----------------|
| Plugin versions | `.claude-plugin/marketplace.json` |
| CI pipeline | `.github/workflows/*.yml` |

## Rules

- Never hardcode or guess versions in generated code, scripts, or documentation. Read them from the source of truth.
- When referencing a tool's behavior or flags, verify against the version actually in use. Flags and defaults change between versions.
- When referencing any external library, API, or tool not already in the project, look up its current documentation before writing code against it or recommending it.
- When answering questions about how something works (inside or outside this codebase), prefer reading the source or searching the web over generating an answer from recall.
