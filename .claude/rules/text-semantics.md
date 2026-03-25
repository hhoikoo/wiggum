---
paths:
  - "**/*"
---
# Text Semantics

Rules for written content in code comments, docstrings, commit messages, and documentation.

## Comments

- Comments explain *why*, not *what*. If code needs a comment to explain what it does, make the code more readable instead.
- No change-narration comments ("was X, now Y", "updated to use new approach", "changed from A to B").
- No TODO comments without context -- if a TODO is needed, include what and why.

## Voice and Tone

- Direct and precise. State what something does or why a decision was made.
- No hedging or filler: avoid "basically", "essentially", "in order to" (when "to" suffices), "it's worth noting that", "it's important to note", "note that".
- No meta-commentary in code: avoid "this function handles...", "here we...", "the following code...". The code speaks for itself.
- No superlatives or marketing language: avoid "robust", "elegant", "comprehensive", "seamless", "streamlined", "leverage".
- No AI-style narration: avoid "Let's", "Great", "I'll now", "Here's what I did" in any written artifacts.
- No defensive annotations. When fixing a mistake, just fix it. Do not add comments, docstrings, or instructions that exist solely to prevent the same mistake from recurring. If the correct behavior is already implied by the structure (e.g., a field was removed from a schema), do not add a line restating that the field should not be there.
