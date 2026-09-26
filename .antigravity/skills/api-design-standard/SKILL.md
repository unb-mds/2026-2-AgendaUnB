---
name: api-design-standard
description: >-
  Standardize the design, creation, modification, and review of API routes and
  endpoints. Use this skill when creating new API endpoints, modifying existing
  routes, reviewing API designs, adding request validation, standardizing error
  responses, or ensuring RESTful conventions across the project.
---

# API Design Standard

Ensure that all API routes and endpoints follow consistent RESTful conventions,
validate incoming data rigorously, use appropriate HTTP status codes, maintain
predictable request and response structures, and return errors in a uniform
format.

---

## Core Responsibilities

1. Follow RESTful API design principles.
2. Maintain consistent naming conventions for routes and resources.
3. Use HTTP methods and status codes correctly.
4. Validate request parameters, query parameters, request bodies, headers, and
   path variables.
5. Use DTOs, schemas, serializers, or equivalent validation mechanisms when
   supported by the project's technology stack.
6. Maintain consistent request and response payload structures.
7. Provide a standardized error response format.
8. Preserve backward compatibility when modifying existing endpoints whenever
   possible.
9. Follow the existing project's API architecture and conventions.
10. Avoid unnecessary changes to unrelated endpoints or services.
11. Identify inconsistencies in existing API designs and recommend improvements
    when relevant.

---

## RESTful Route Design

Use standard HTTP methods according to their intended semantics:

| Method   | Purpose                                          |
| -------- | ------------------------------------------------ |
| `GET`    | Retrieve resources                               |
| `POST`   | Create resources or trigger actions               |
| `PUT`    | Replace an existing resource                      |
| `PATCH`  | Partially update an existing resource             |
| `DELETE` | Remove a resource                                 |

Prefer resource-oriented URLs:

```
GET    /users
GET    /users/{id}
POST   /users
PATCH  /users/{id}
DELETE /users/{id}
```

**Avoid** unnecessary action-oriented routes:

```
POST /createUser    ← wrong
POST /deleteUser    ← wrong
GET  /getUsers      ← wrong
```

When an action-oriented endpoint is genuinely required by the domain, document
the reason and maintain consistency with the existing API.

---

## Route Naming

Routes should:

- Use **nouns** rather than verbs when representing resources.
- Use consistent **pluralization**.
- Use **lowercase** paths.
- Use predictable nesting only when the relationship is meaningful.
- Avoid unnecessary nesting.
- Maintain consistent naming conventions across the entire API.

**Good:**

```
/users
/users/{id}
/users/{id}/orders
```

**Avoid:**

```
/getUsers
/userList
/users-list
/User/{id}
```

---

## HTTP Status Codes

Use status codes according to the actual outcome of the request:

| Code  | Meaning                | When to Use                                        |
| ----- | ---------------------- | -------------------------------------------------- |
| `200` | OK                     | Successful request with a response body            |
| `201` | Created                | Resource successfully created                      |
| `202` | Accepted               | Request accepted for asynchronous processing       |
| `204` | No Content             | Successful operation with no response body         |
| `400` | Bad Request            | Invalid request syntax or malformed input          |
| `401` | Unauthorized           | Authentication is missing or invalid               |
| `403` | Forbidden              | Authenticated client lacks permission              |
| `404` | Not Found              | Requested resource does not exist                  |
| `409` | Conflict               | Request conflicts with current resource state      |
| `422` | Unprocessable Entity   | Syntactically valid but fails semantic validation  |
| `429` | Too Many Requests      | Rate limit exceeded                                |
| `500` | Internal Server Error  | Unexpected server-side failure                     |

**Do not use a generic status code when a more appropriate one exists.**

---

## Request Validation

All externally supplied input must be validated **before** reaching business
logic.

Validate, when applicable:

- Path parameters
- Query parameters
- Request bodies
- Headers
- Authentication data
- Pagination parameters (page, size, cursor)
- Filtering and sorting parameters
- IDs and identifiers
- Dates and timestamps
- Numeric ranges
- Strings and formats
- Enumerated values
- Required and optional fields
- Nested objects
- Arrays

Use the validation mechanism already established by the project:

- DTOs, JSON Schema, Pydantic, Zod, Joi, Yup, class-validator, Marshmallow,
  Bean Validation, or framework-native schemas.

**Do not duplicate validation logic unnecessarily.**

---

## Payload Design

Request and response payloads should be:

- Predictable
- Consistent
- Explicit
- Easy to consume
- Backward-compatible when possible

Maintain consistent naming conventions for fields.

**Never expose:**

- Internal database fields
- Passwords or secrets
- Internal stack traces
- Sensitive infrastructure information
- Private implementation details

Use explicit response schemas when supported by the project.

---

## Error Response Standard

All API errors must follow a **consistent structure** across endpoints.

Standard format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid fields.",
    "details": [
      {
        "field": "email",
        "message": "Invalid email address."
      }
    ]
  }
}
```

The exact structure must follow the existing project's conventions when they
already exist.

Error responses should:

- Use the correct HTTP status code.
- Provide a stable machine-readable error code when appropriate.
- Provide a clear human-readable message.
- Include field-level validation details when useful.
- Avoid exposing sensitive internal information.
- Avoid returning raw exception messages that may expose implementation details.
- Maintain the same structure across all endpoints.

### Error Codes

When the project uses error codes:

- Keep them **stable** — do not rename without a migration strategy.
- Use **descriptive** names.
- Avoid exposing implementation-specific exception names.
- Do not create duplicate codes for the same semantic error.
- Reuse existing error codes when applicable.

---

## API Versioning

When the project uses API versioning:

- Follow the existing versioning strategy.
- Do not introduce a new versioning mechanism without a clear requirement.
- Preserve compatibility between versions where required.
- Clearly identify breaking changes.

If the project does not use versioning, **do not introduce it unnecessarily**.

---

## Pagination

For collection endpoints, follow the project's existing pagination strategy.

If pagination is required, ensure consistency for:

- Page size
- Page number or cursor
- Sorting
- Metadata (total count, next/previous page)
- Navigation information

**Do not introduce multiple pagination formats without a clear reason.**

---

## Filtering and Sorting

Filtering and sorting parameters should:

- Use consistent names.
- Be explicitly validated.
- Reject unsupported fields when appropriate.
- Avoid arbitrary database expressions.
- Prevent injection vulnerabilities.
- Follow the conventions already used by the project.

---

## Authentication and Authorization

When an endpoint requires authentication:

- Apply the project's established authentication mechanism.
- Validate authentication **before** processing protected operations.
- Enforce authorization at the appropriate layer.
- Return `401` for missing or invalid authentication.
- Return `403` when authentication succeeds but access is not permitted.

**Do not expose authorization details that could create unnecessary security
risks.**

---

## Backward Compatibility

When modifying an existing endpoint:

1. Identify the current contract.
2. Identify existing consumers when the information is available.
3. Determine whether the change is backward-compatible.
4. Avoid breaking existing clients unnecessarily.
5. Clearly identify breaking changes when they are unavoidable.
6. Update relevant documentation and tests.

**Do not rename, remove, or change the meaning of existing fields without
considering compatibility.**

---

## Codebase Integration

Before creating or modifying an endpoint, inspect the existing codebase when
available. Look for:

- Existing routes and route patterns
- Controllers and handlers
- Services and business logic layers
- DTOs, schemas, and validation layers
- Middleware (auth, rate limiting, logging)
- Error handling middleware or utilities
- Existing tests for related endpoints

Follow the project's established patterns. Do not introduce new architectural
patterns when the existing ones are adequate.

---

## Checklist

When creating or reviewing an API endpoint, verify:

- [ ] HTTP method matches the operation semantics
- [ ] Route follows resource-oriented naming conventions
- [ ] All input is validated before reaching business logic
- [ ] Correct HTTP status codes are used for all outcomes
- [ ] Response payload is consistent with the project's conventions
- [ ] Error responses follow the standardized format
- [ ] Sensitive data is not exposed in responses
- [ ] Authentication and authorization are enforced where required
- [ ] Backward compatibility is preserved (or breaking changes are documented)
- [ ] Pagination, filtering, and sorting follow existing conventions
- [ ] Relevant tests are created or updated
- [ ] Changes are consistent with the existing codebase architecture

