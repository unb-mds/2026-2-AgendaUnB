---
name: to-prd
description: >-
  Transform the current conversation context, user requirements, project
  knowledge, and available codebase context into a clear, actionable, and
  technically grounded Product Requirements Document (PRD). Use this skill when
  the user asks to create a PRD, generate product requirements, document a
  feature specification, convert a discussion into a structured requirements
  document, or publish requirements to a task/issue management system.
---

# To-PRD

Act as a bridge between product requirements and software implementation.
Transform conversation context, user goals, and codebase knowledge into a
structured, implementation-ready Product Requirements Document (PRD).

When a project management integration is available, publish the PRD directly to
the project's task or issue management system.

---

## Core Objective

1. Analyze the current conversation and extract the user's actual goals and
   requirements.
2. Inspect the available codebase and project context when access is available.
3. Identify existing functionality, architecture, constraints, conventions, and
   relevant implementation details.
4. Convert this information into a structured PRD.
5. Clearly separate confirmed requirements from assumptions or open questions.
6. **Never invent** product requirements, technical details, or business rules.
7. Create an implementation-ready document that developers, designers, testers,
   and stakeholders can understand.
8. Publish the PRD to the project's task/issue management system when an
   appropriate integration is available.

---

## Step 1 — Context Analysis

Before creating the PRD, analyze:

- The entire current conversation.
- User requests and stated goals.
- Existing decisions and constraints.
- Relevant project documentation.
- Relevant source code and configuration files.
- Existing architecture and patterns.
- Existing APIs, database models, services, components, and integrations
  related to the requested feature.
- Existing tests and testing conventions.
- Existing project terminology.

**Do not treat assumptions as facts.** If information is unclear or
contradictory, explicitly identify it instead of silently choosing an
interpretation.

---

## Step 2 — Codebase Analysis

When codebase access is available:

1. Identify the relevant parts of the repository.
2. Determine how the requested feature fits into the existing architecture.
3. Identify existing components or services that can be reused.
4. Identify potential technical constraints.
5. Identify dependencies and integration points.
6. Identify existing behavior that could be affected.
7. Review relevant tests before defining acceptance criteria.
8. Avoid proposing architectural changes that are unnecessary for the requested
   product behavior.

The PRD should describe technical context only when it helps clarify
implementation requirements.

---

## Step 3 — Generate the PRD

Use the structure defined below. Omit sections that are not applicable, but
include a brief note explaining why (e.g., "Not applicable — no API changes
required.").

---

## PRD Structure

```
# Product Requirements Document

## 1. Overview
Concise description of the product, feature, or change being requested.
Explain the purpose and the problem it solves.

## 2. Problem Statement
- What problem exists today.
- Who experiences the problem.
- Why the problem matters.
- What limitations or pain points currently exist.

## 3. Goals
Measurable or clearly observable goals of the feature.

## 4. Non-Goals
What is explicitly outside the scope of this request.
Prevents unnecessary feature expansion.

## 5. User Stories
Format: "As a [user type], I want [action], so that [benefit]."
Include only stories supported by available context.

## 6. Functional Requirements
Precise, testable behavioral requirements.
Use identifiers: FR-001, FR-002, FR-003, etc.

## 7. User Flow
Step-by-step expected user experience:
- Entry point
- User actions
- System responses
- Success states
- Error states
- Relevant edge cases

## 8. Acceptance Criteria
Objective criteria for feature completion.
Use Given / When / Then format when appropriate:
  Given [initial condition]
  When [user action]
  Then [expected result]
Must be specific enough for automated tests or QA test cases.

## 9. Technical Context
Relevant technical considerations from the codebase:
- Existing architecture and relevant modules
- APIs, database models, services, components
- External integrations
- Authentication / authorization requirements
- Existing testing infrastructure
- Important dependencies
Do not turn this into an implementation plan.

## 10. Data Requirements
When relevant:
- Required data and data structures
- Inputs, outputs, validation rules
- Persistence and migration requirements
- Data relationships

## 11. API Requirements
When applicable:
- Endpoints, HTTP methods
- Request / response structure
- Authentication, validation, error responses
- Relevant status codes
Do not invent API contracts when requirements do not define them.

## 12. Error Handling and Edge Cases
Important failure scenarios and edge cases.
Expected system behavior for each case.

## 13. Security and Permissions
- Authentication and authorization requirements
- User permissions
- Sensitive data considerations
- Input validation and security constraints

## 14. Performance and Scalability
Relevant performance requirements or constraints.
Do not invent numerical targets when none exist.

## 15. Observability
When applicable: logging, metrics, monitoring, error tracking, auditing.

## 16. Testing Requirements
- Unit, integration, end-to-end, regression tests
- Edge cases
Align with the project's existing testing strategy.

## 17. Dependencies
- Internal dependencies
- External services, APIs, libraries
- Infrastructure
- Other features or issues

## 18. Open Questions
Unresolved questions that must be answered before or during implementation.
Do not hide uncertainty.

## 19. Definition of Done
Clear conditions indicating the feature is complete:
- Requirements implemented
- Acceptance criteria satisfied
- Tests passing
- Documentation updated
- Code reviewed (when applicable)
- Deployment / migration completed (when applicable)

## 20. Implementation Notes
Concise implementation guidance derived from the existing codebase.
Do not prescribe implementation details unnecessarily.
```

---

## Requirement Quality

Every requirement must be:

- **Clear** — unambiguous language
- **Specific** — concrete and precise
- **Testable** — verifiable through tests or inspection
- **Relevant** — connected to the user's request
- **Traceable** — linked to the user's request or project context

Avoid vague statements such as:

- "Make the system better."
- "Improve performance."
- "Make it user-friendly."

Instead, express concrete and verifiable behavior.

---

## Traceability

Maintain traceability between:

```
User request
  → Product requirement
    → User story
      → Acceptance criterion
        → Relevant codebase component
          → Test requirement
```

Do not fabricate references or file paths. If a requirement cannot be traced to
available information, mark it as an **assumption** or **open question**.

---

## Issue / Task Manager Publication

When a task management integration is available:

1. Generate the PRD first.
2. Validate that the PRD is complete and internally consistent.
3. Identify the appropriate project, workspace, repository, or issue tracker.
4. Create a new task, issue, or project item using the appropriate integration.
5. Use the PRD as the issue/task description.
6. Preserve the PRD structure and formatting.
7. Add an appropriate title.
8. Add relevant labels, tags, or metadata only when supported by project
   context.
9. **Do not invent** project IDs, issue IDs, labels, milestones, assignees, or
   other metadata.
10. After publication, report the created item's identifier and link when the
    integration provides them.

If the integration does not support creating issues or tasks, provide the
finalized PRD in a format that can be manually copied into the project's task
manager.

### Publication Safety

**Never publish a PRD automatically if:**

- The target project is ambiguous.
- The requested feature is fundamentally unclear.
- Required information is missing and cannot reasonably be inferred.
- The integration would modify the wrong project.
- The user has not provided enough information to identify the intended
  destination.

In these cases, ask only the minimum necessary clarification questions.

---

## Important Behavioral Rules

- Use the current conversation as the **primary source of product intent**.
- Use the codebase as the **primary source of technical context** when
  available.
- **Do not invent requirements.**
- Do not assume existing code behaves differently from what inspection shows.
- Clearly distinguish **facts**, **assumptions**, **decisions**, and **open
  questions**.
- Preserve the user's terminology unless there is a strong reason to clarify
  it.
- Keep the PRD concise enough to be actionable but detailed enough for
  implementation.
- Do not turn every technical observation into a product requirement.
- Do not unnecessarily redesign the existing architecture.
- Do not create duplicate requirements.
- Prefer incremental changes that fit the existing codebase.
- If the requested feature conflicts with existing architecture or behavior,
  identify the conflict explicitly.
- If relevant information cannot be verified, state that it could not be
  verified.
- **Never claim that an issue was created or published** unless the
  task-management integration actually confirms the operation.

---

## Final Output

**When no publication is requested** or no task-management integration is
available:

- Return the complete PRD.

**When publication is requested and successfully completed**, provide:

1. A brief summary of the generated PRD.
2. The project/task/issue where it was published.
3. The created issue or task identifier.
4. The direct link when available.
5. Any unresolved questions that remain relevant to implementation.

The final PRD should be written for real-world collaboration between product
managers, developers, designers, QA engineers, and other project stakeholders.

