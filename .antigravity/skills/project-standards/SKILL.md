---
name: project-standards
description: >-
  Ensure that all development work strictly follows the project's documented
  vision, requirements, rules, conventions, and technical standards. Use this
  skill before implementing, modifying, reviewing, or proposing changes to
  verify alignment with project documentation (documento-de-visao.md,
  requisitos.md, padroes.md, index.md) and established codebase conventions.
  Acts as a persistent project governance layer.
---

# Project Standards

Act as a persistent project governance layer. Before implementing, modifying,
reviewing, or proposing changes, consult and respect the available project
documentation and established codebase conventions.

---

## Core Responsibility

Ensure that every technical decision and implementation is aligned with:

1. The project's Vision Document
2. Functional requirements
3. Non-functional requirements
4. Business rules
5. Product requirements and acceptance criteria
6. Architectural standards
7. Coding standards
8. API standards
9. Security requirements
10. Testing standards
11. Existing project conventions
12. Constraints explicitly defined by the project

---

## Project Documentation

The project may contain dedicated documentation files. **Check these exact
files first** when they are available:

| File                       | Purpose                                                        |
| -------------------------- | -------------------------------------------------------------- |
| `documento-de-visao.md`    | Vision, goals, scope, purpose, and intended direction          |
| `requisitos.md`            | Functional/non-functional requirements, business rules, constraints |
| `padroes.md`               | Coding standards, architectural conventions, technical standards |
| `index.md`                 | Documentation index with links to additional documentation     |

**Do not assume the contents of these files.** Read the actual files when they
are available.

### Documentation Discovery

If the standard files above do not exist, search the project for equivalent
files or directories containing:

- Project/product vision
- Requirements (functional, non-functional)
- Business rules
- Standards, conventions, guidelines
- Architecture documentation
- API/security/testing requirements

Possible equivalent filenames:

```
vision.md, project-vision.md, product-vision.md,
requirements.md, functional-requirements.md, non-functional-requirements.md,
standards.md, conventions.md, architecture.md,
technical-guidelines.md
```

Do not assume a similarly named file has the same meaning without inspecting
its contents. If a required document cannot be found, **explicitly state that
it could not be verified** instead of inventing its contents.

### Documentation Priority

1. `documento-de-visao.md` — vision, goals, scope, direction
2. `requisitos.md` — requirements, business rules, constraints
3. `padroes.md` — coding, architectural, technical standards
4. `index.md` — navigation and references to additional documentation

The actual content of the documents takes precedence over these descriptions.
If `index.md` references additional authoritative documentation, inspect the
relevant referenced documents when necessary.

---

## Source of Truth

Treat project documentation as the **primary source of truth** for project
intent.

Do not silently override documented requirements with:

- Personal preferences
- Generic best practices
- Assumptions
- Preferred implementation patterns
- Unrequested architectural changes

**If the documentation explicitly defines a rule, requirement, or constraint,
respect it.**

### Documentation Conflicts

If documentation conflicts with itself:

1. Identify the conflict.
2. Determine whether one document is explicitly more authoritative.
3. Check whether the project provides a documented precedence rule.
4. Do not silently choose an interpretation when the conflict could materially
   affect implementation.
5. Ask for clarification when necessary.

### Documentation and Code Disagreements

If the documentation and the current codebase disagree:

1. Identify the discrepancy.
2. Do not automatically assume the code is correct.
3. Do not automatically assume the documentation is correct.
4. Determine whether the difference is intentional if context allows.
5. If the correct behavior cannot be established, ask for clarification before
   making a potentially breaking change.

---

## Project Vision

Use the vision document to understand:

- Why the project exists
- What problem it is solving
- Who the intended users are
- What the project's goals are
- What is inside and outside the intended scope
- What product direction the project follows

Before implementing significant functionality, determine whether the requested
change is aligned with the documented project vision.

Do not use the vision document to override explicit technical or functional
requirements.

---

## Functional Requirements

Ensure that implementations satisfy documented functional requirements.

Verify, when applicable:

- Expected behavior and user flows
- Business rules
- Inputs, outputs, validations
- Error conditions and permissions
- State transitions
- Acceptance criteria

**Do not invent functionality** not supported by the requirements. Do not
remove required functionality merely because it is not currently implemented.

---

## Non-Functional Requirements

Ensure implementations respect applicable non-functional requirements:

- Performance, security, reliability
- Availability, scalability, maintainability
- Accessibility, usability, observability
- Compatibility, privacy, data integrity

**Do not invent numerical targets** when they are not documented.

---

## Business Rules

Identify and respect business rules defined in project documentation.

- Business rules must not be bypassed because an alternative is technically
  easier.
- When modifying existing behavior, determine whether the change affects
  existing business rules.

---

## Project Standards

Follow standards defined in `padroes.md` and additional technical
documentation, which may include:

- Code structure, naming conventions, architecture
- Dependencies, APIs, database access
- Error handling, logging, security
- Testing, documentation, Git conventions
- Configuration, deployment, file organization

**When the project already has an established convention, follow it instead of
introducing a new pattern.**

---

## Codebase Consistency

The existing codebase is an important source of implementation context.

Before modifying code:

1. Inspect related implementations.
2. Identify existing patterns.
3. Reuse existing abstractions when appropriate.
4. Follow established naming, architecture, error-handling, and testing
   conventions.
5. Avoid introducing unnecessary frameworks or dependencies.
6. Avoid modifying unrelated components.

Do not assume a generic industry best practice is automatically appropriate for
the project.

---

## Implementation Workflow

Before implementing a significant change:

1. Read `index.md` when available.
2. Identify relevant project documentation.
3. Read `documento-de-visao.md` when available and relevant.
4. Read `requisitos.md` when available and relevant.
5. Read `padroes.md` when available and relevant.
6. Inspect additional documentation referenced by `index.md` when relevant.
7. Inspect the relevant codebase.
8. Identify applicable requirements and standards.
9. Identify potential conflicts or missing information.
10. Implement the change according to documented requirements and standards.
11. Add or update tests as required.
12. Verify the implementation against the relevant requirements.
13. Report any requirements that could not be verified.

---

## Implementation Validation

After implementing a change, verify:

- [ ] Implementation satisfies relevant functional requirements
- [ ] Applicable non-functional requirements are respected
- [ ] Change follows the project's documented vision
- [ ] Architecture and coding standards are followed
- [ ] API standards are followed
- [ ] Required existing behavior is preserved
- [ ] Acceptance criteria are satisfied
- [ ] Appropriate tests are present
- [ ] Documentation requirements are satisfied
- [ ] Unrelated parts of the system are unchanged

If a requirement cannot be verified, **explicitly state that it could not be
verified**.

---

## Requirement Traceability

Maintain traceability between:

```
Project Vision
  → Requirements
    → Acceptance Criteria
      → Implementation
        → Tests
          → Verification
```

For each significant change, identify the relevant requirements the
implementation is intended to satisfy.

Do not invent requirement IDs. If the project uses requirement identifiers,
preserve and reference them accurately.

---

## Change Impact Analysis

Before implementing significant changes, identify potentially affected:

- Vision, functional requirements, non-functional requirements
- Business rules, APIs, database models
- Services, components, tests
- Documentation, security controls
- Integrations, existing consumers

Consider whether the requested change could unintentionally violate existing
requirements or standards.

---

## Scope Control

Prevent unnecessary scope expansion.

If a requested change introduces functionality not supported by documented
requirements:

1. Identify it as potential scope expansion.
2. Explain which documented scope or requirement is relevant.
3. Do not automatically implement unrelated functionality.

However, do not reject necessary implementation details simply because they are
not explicitly described in the product vision if they are required to satisfy
an existing requirement.

---

## Conflict Resolution

When a requested implementation conflicts with project documentation:

1. Identify the conflicting requirement or standard.
2. Explain the conflict clearly.
3. Identify the affected document.
4. Determine whether the user is intentionally changing a requirement.
5. If the conflict cannot be resolved, ask for clarification.
6. **Never silently violate an established project requirement.**

When the user explicitly changes a requirement, treat it as a potential project
change and identify which documentation, tests, APIs, or implementation details
may need to be updated.

---

## Assumptions

Clearly distinguish between:

| Category                    | Treatment                              |
| --------------------------- | -------------------------------------- |
| Confirmed requirement       | Implement as documented                |
| Documented standard         | Follow as specified                    |
| Existing codebase behavior  | Preserve unless requirement changes it |
| Reasonable assumption       | Make explicit, flag as assumption      |
| Open question               | Ask when necessary                     |

**Never present an assumption as a documented requirement.**

---

## Testing and Verification

Use tests as evidence of requirement compliance. Tests should cover:

- Functional behavior and business rules
- Edge cases and error conditions
- Security requirements
- Testable non-functional requirements
- Regression scenarios

When a requirement cannot be verified through automated tests, identify an
appropriate verification method.

**Never claim that a requirement has been verified without actual evidence.**

---

## Security and Compliance

Ensure changes respect documented security requirements:

- Authentication and authorization
- Input validation and sensitive data handling
- Data access and secrets management
- Logging and API security
- Privacy and access control

**Do not weaken existing security controls** without explicit authorization and
documented justification.

---

## Performance and Non-Functional Compliance

When the project defines measurable non-functional requirements, verify them
against the implementation.

Do not claim compliance based solely on code inspection when actual measurement
is required. If verification was not performed, clearly state that.

---

## Documentation Maintenance

If an implementation changes behavior covered by project documentation,
identify whether relevant documentation should also be updated:

- `documento-de-visao.md`, `requisitos.md`, `padroes.md`, `index.md`
- API, architecture, and technical documentation

**Do not modify documentation unnecessarily.**

---

## Important Rules

- Always inspect relevant project documentation before significant decisions.
- Check `documento-de-visao.md`, `requisitos.md`, `padroes.md`, and `index.md`
  first when available.
- If those files are absent, search for equivalent documentation.
- **Never invent** the contents of missing documentation.
- Project documentation takes precedence over generic preferences.
- Do not silently ignore requirements or violate standards.
- Do not replace documented decisions with personal preferences.
- Do not introduce unnecessary architectural changes.
- Do not expand project scope without justification.
- Preserve existing behavior unless a requirement explicitly changes it.
- Clearly distinguish requirements from assumptions.
- When documentation and code disagree, identify the discrepancy.
- When requirements conflict, surface the conflict.
- **Never claim compliance without verification.**
- **Never fabricate** documentation references, requirement IDs, file paths, or
  implementation details.

---

## Compliance Report

When reviewing a significant implementation or change, provide a concise
compliance report using this structure:

### Project Vision

Relevant vision requirements and whether the change aligns with them.

### Functional Requirements

Relevant functional requirements and their implementation status.

### Non-Functional Requirements

Relevant non-functional requirements and their implementation status.

### Business Rules

Relevant business rules and whether they are respected.

### Project Standards

Relevant standards from `padroes.md` or equivalent and compliance status.

### Codebase Consistency

Whether the implementation follows existing project patterns and architecture.

### Conflicts

Any conflicts between the requested change, project documentation, existing
code, and project standards.

### Assumptions

Assumptions made during implementation.

### Open Questions

Unresolved requirements, decisions, or documentation gaps.

### Verification

Tests, inspections, measurements, or other evidence used to verify compliance.

### Documentation Impact

Whether any project documentation should be updated as a result of the change.

### Final Status

Use one of:

- **COMPLIANT** — all verified requirements and standards are satisfied.
- **PARTIALLY COMPLIANT** — some requirements are satisfied; gaps are
  identified.
- **REQUIRES CLARIFICATION** — conflicts or missing information prevent full
  verification.
- **NON-COMPLIANT** — documented requirements or standards are violated.

Do not assign numerical scores or subjective ratings.

---

## Primary Goal

Ensure that the AI consistently respects the project's:

```
Vision
  → Requirements
    → Business Rules
      → Standards
        → Existing Architecture
          → Implementation
            → Tests
```

Use the project's actual documentation and codebase as the source of truth.
Prevent requirements from being forgotten, prevent undocumented scope
expansion, and ensure implementation decisions remain aligned with the
project's documented vision, requirements, and standards throughout the entire
development lifecycle.

