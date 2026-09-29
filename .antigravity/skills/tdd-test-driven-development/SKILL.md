---
name: tdd-test-driven-development
description: >-
  Guide software development using Test-Driven Development (TDD) principles.
  Use this skill when the user asks to write tests first, follow TDD, implement
  a feature using RED-GREEN-REFACTOR, debug failing tests, add test coverage,
  or apply test-driven design to new or existing code.
---

# TDD (Test-Driven Development)

Guide software development using the classic TDD cycle: **RED → GREEN →
REFACTOR**. The goal is to design, write, run, debug, and improve automated
tests *before* implementing production code.

---

## Core Cycle

### 1. RED

- Write a test that describes the desired behavior.
- Run the test and confirm that it fails **for the expected reason**.

### 2. GREEN

- Implement the **minimum** amount of production code necessary to make the
  test pass.
- Do not add unnecessary functionality.

### 3. REFACTOR

- Improve the implementation and test quality while keeping **all tests
  passing**.
- Remove duplication, improve naming, simplify logic, and maintain clean
  architecture.

---

## General Behavior

When helping with a development task:

1. Understand the requested behavior and requirements before writing code.
2. Identify the smallest testable behavior to implement first.
3. Write the test before writing the production implementation whenever
   practical.
4. Explain what the test is expected to prove.
5. Run or reason about the test result when execution tools are available.
6. Implement only enough code to satisfy the current failing test.
7. Refactor after the test passes.
8. Repeat the cycle incrementally until the requested behavior is complete.
9. Preserve existing behavior and avoid unnecessary changes.
10. Prefer small, focused tests over large tests that verify multiple unrelated
    behaviors.

---

## Test Design

Tests should:

- Have clear and descriptive names.
- Follow the **Arrange–Act–Assert** structure when appropriate.
- Test observable behavior rather than implementation details.
- Cover normal cases, edge cases, and expected failure cases.
- Be deterministic and isolated.
- Avoid unnecessary dependencies on external systems.
- Use mocks, stubs, or fakes only when they provide a clear testing benefit.
- Avoid excessive mocking.
- Be easy to understand and maintain.

---

## Workflow: Starting a New Feature

### Step 1 — Requirements

- Identify the expected behavior.
- Identify inputs, outputs, constraints, and edge cases.
- Clarify ambiguous requirements when necessary.

### Step 2 — Test Plan

- Define the smallest meaningful test case.
- Explain what behavior the test represents.

### Step 3 — RED

- Write the failing test.
- Explain why it should fail before the implementation exists.

### Step 4 — GREEN

- Implement the simplest solution that makes the test pass.
- Do not prematurely optimize or implement unrelated functionality.

### Step 5 — REFACTOR

- Review the implementation and tests.
- Improve structure, naming, duplication, readability, and maintainability.
- Ensure all tests continue to pass.

### Step 6 — REPEAT

- Add the next test case.
- Repeat the RED → GREEN → REFACTOR cycle until the feature is complete.

---

## Debugging Failing Tests

When an existing test fails:

1. Identify whether the failure is caused by:
   - Incorrect production code
   - Incorrect test expectations
   - A broken test setup
   - An environment or dependency issue
   - An unrelated regression
2. **Do not modify a test simply to make it pass** unless the test itself is
   incorrect.
3. Explain the root cause before proposing a fix.
4. Make the smallest appropriate change.
5. Re-run relevant tests after the change.

---

## Working with Existing Codebases

- Inspect the existing architecture and testing conventions first.
- Follow the project's established language, framework, naming, and test
  structure.
- Avoid rewriting unrelated code.
- Add **characterization tests** when necessary to capture existing behavior
  before making risky changes.
- Introduce new behavior through incremental tests whenever possible.

---

## Language and Framework Adaptation

Adapt to the project's technology stack. Supported languages include (but are
not limited to):

- Python, JavaScript, TypeScript, Java, C#, Go, Rust, Ruby, PHP, Kotlin, Swift

Use the testing framework already established in the project, such as:

- pytest, unittest, Jest, Vitest, Mocha, JUnit, NUnit, xUnit, Go testing,
  RSpec, PHPUnit, XCTest

**Do not introduce a new testing framework** when the project already has one,
unless there is a clear and justified reason.

---

## Code Quality Guidelines

### Encourage

- Small functions
- Clear interfaces
- Low coupling and high cohesion
- Explicit dependencies
- Meaningful names
- Simple implementations
- Maintainable tests
- Separation of concerns

### Avoid

- Overengineering
- Premature abstraction
- Excessive mocking
- Testing private implementation details
- Large test cases
- Unnecessary dependencies
- Writing production code before defining expected behavior

---

## Output Format

When guiding a TDD implementation, structure the response as follows:

### 1. REQUIREMENT

Briefly describe the behavior being implemented.

### 2. TEST CASE

Explain what behavior should be tested.

### 3. RED

Provide the test and explain why it should initially fail.

### 4. GREEN

Provide the minimum implementation required to make the test pass.

### 5. REFACTOR

Show improvements to the implementation and tests while preserving behavior.

### 6. NEXT TEST

Identify the next behavior or edge case to test.

### 7. FINAL TEST SUITE

Summarize the tests created and the behaviors they cover.

---

## Important Rules

- **Follow RED → GREEN → REFACTOR.** Do not skip phases.
- **Prefer incremental development.** One test at a time.
- **Never claim tests pass unless they were actually executed** or the result is
  otherwise explicitly known.
- **Never fabricate test results.**
- Do not skip tests simply because the implementation appears obvious.
- Do not add unnecessary production code.
- Do not change tests merely to accommodate incorrect production behavior.
- Explain failures clearly and focus on root causes.
- Respect the existing project's conventions.
- Keep the development process **practical rather than dogmatic**.
- When execution tools are available, use them to run the relevant tests and
  report actual results.
- When execution tools are unavailable, clearly distinguish **expected results**
  from **verified results**.

