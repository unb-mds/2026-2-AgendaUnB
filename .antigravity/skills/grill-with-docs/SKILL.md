---
name: grill-with-docs
description: >-
  Deeply analyze documents provided by the user through rigorous questioning,
  fact-checking, contradiction detection, and critical analysis. Use this skill
  when the user provides a document (PDF, text, report, paper, proposal, legal
  document, etc.) and asks for a critical review, analysis, fact-check, or
  "grilling" of its content.
---

# Grill with Docs

Perform a deep, rigorous critical analysis of a document provided by the user.
The goal is to **test the document**, not to attack its author. Maintain a
skeptical, objective, and evidence-based tone throughout.

---

## Core Principles

1. **Read first, conclude later.** Read and understand the entire document
   before forming any conclusions.
2. **Accuracy over confidence.** Never fabricate citations, page numbers,
   quotations, or evidence. If you are unsure, say so.
3. **Never invent information.** Every claim you make about the document must
   be traceable to its content.
4. **Quote or reference precisely.** Whenever possible, cite the exact section,
   paragraph, page, heading, or passage you are referring to.
5. **Prioritize impact.** Focus on the most important weaknesses instead of
   listing every minor issue.
6. **Explain why it matters.** For every issue you identify, explain its
   significance.
7. **Credit strength honestly.** If the document is well-supported, say so.
   Do not manufacture criticisms.
8. **Domain adaptation.** If the document contains technical, academic, legal,
   financial, scientific, or professional material, adapt your analysis to the
   relevant domain while remaining cautious about unsupported conclusions.

---

## Analysis Procedure

### Step 1 — Read the Document

Read the entire document carefully. Do not begin analysis until you have a
complete understanding of its structure, purpose, and content.

### Step 2 — Identify the Building Blocks

Identify and categorize the following elements:

- **Facts** explicitly stated in the document
- **Claims** made by the author
- **Assumptions** the document relies on but does not explicitly justify
- **Interpretations** the author applies to data or evidence
- **Conclusions** the author draws
- **Unverifiable information** that cannot be confirmed from the document alone

### Step 3 — Analyze

For each building block, evaluate:

- Is it supported by evidence within the document?
- Is the evidence sufficient, relevant, and conclusive?
- Does it contradict anything else in the document?
- Is it vague, ambiguous, or unclear?
- Are there logical gaps between the evidence and the conclusion?
- Is important information missing?

### Step 4 — Use External Sources (Only When Necessary)

If external sources are available, use them **only** to verify factual claims.
Always clearly distinguish external information from information contained in
the document. Never present external information as if it came from the
document.

### Step 5 — Structure the Response

Use the output format below. Every section must be grounded in the document's
actual content.

---

## Output Format

Structure every analysis using the following sections. If a section has no
findings, include it with a brief note explaining why (e.g., "No contradictions
were detected.").

### DOCUMENT OVERVIEW

- Briefly summarize the document's purpose, scope, and main argument.

### KEY CLAIMS

- List the most important claims made in the document.
- For each claim, note whether it is explicitly supported, partially supported,
  or unsupported within the document.

### GRILL QUESTIONS

- Ask the most challenging questions that could expose weaknesses, unsupported
  assumptions, contradictions, or missing evidence.
- Keep questions **specific** rather than generic.
- Reference the relevant section or passage for each question.

### WEAKNESSES AND GAPS

- Identify specific weaknesses, missing information, logical gaps, or unclear
  statements.
- For each issue, explain **why it matters** and what impact it has on the
  document's overall argument.

### CONTRADICTIONS

- Identify statements that appear inconsistent with each other.
- **Quote or reference the relevant sections** for both sides of each
  contradiction.

### EVIDENCE CHECK

- Separate claims that are supported by evidence from claims that lack
  sufficient support.
- Identify evidence that appears insufficient, irrelevant, or inconclusive.
- Note any evidence that is presented without a source or methodology.

### ASSUMPTIONS

- Identify assumptions the document relies on but does not explicitly justify.
- Evaluate how critical each assumption is to the document's conclusions.

### STRONG POINTS

- Identify arguments, evidence, or sections that are particularly
  well-supported, well-reasoned, or effectively presented.
- Explain **why** they are strong.

### QUESTIONS THE AUTHOR MUST BE READY TO ANSWER

- Provide a concise, numbered list of high-priority questions that someone
  reviewing or defending the document should be prepared to answer.
- These should be the questions most likely to be asked by a skeptical,
  well-informed reviewer.

### FINAL ASSESSMENT

- Give a concise, evidence-based assessment of the document's:
  - Internal consistency
  - Clarity
  - Evidence quality
  - Argumentation strength
- Do not invent facts or make claims that cannot be supported by the document
  or verified sources.

---

## Important Behavioral Rules

- **Do not criticize something merely because it is unconventional.**
- **Do not assume a claim is false simply because the document does not prove
  it.** Absence of proof is not proof of absence — note it as a gap, not as a
  refutation.
- **Clearly state when additional information is required** to reach a
  conclusion.
- **Base all criticism on concrete evidence from the document.**
- **Keep questions specific.** Avoid generic questions like "Can you elaborate?"
  — instead, ask pointed questions tied to specific content.
- **Always prioritize accuracy over confidence.** If you cannot verify
  something, say so explicitly rather than guessing.

