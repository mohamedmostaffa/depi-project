---
name: fastapi-backend
description: Building asynchronous, Pydantic-validated REST APIs for customer chat, mock order management, and policy verification.
---

# FastAPI Backend Skill

## Purpose
This skill establishes guidelines for building, documenting, and testing the asynchronous REST API service exposing BrandMind's core capabilities.

## When to Activate
- Developing or maintaining endpoints in `src/api/`.
- Defining API request and response contracts using Pydantic.
- Testing HTTP routes with `pytest` and `httpx`.

## Technical Instructions
1. **API Endpoints:**
   - `POST /chat`: Primary conversational endpoint receiving `{brand_id, session_id, message}` and returning `{reply, intent, language, sources, tool_calls, escalated, latency_ms}`.
   - `GET /orders/{order_id}`: Mock order lookup verifying order existence and delivery status.
   - `POST /returns/check`: Direct policy eligibility evaluation endpoint.
   - `POST /returns/request`: Simulated return request creation endpoint.
   - `POST /escalate`: Endpoint to log escalation ticket and hand-off payload.
   - `GET /products/{product_id}`: Product catalog lookup endpoint.
   - `GET /health`: Microservice health check returning service status.
2. **Implementation Standards:**
   - Strict Pydantic input and output validation on all routes.
   - Consistent error responses with structured JSON error details.
   - Asynchronous route handlers (`async def`) for non-blocking I/O.
   - Enforcement of `brand_id` across all operations.

## Testing & Validation Checklist
- [ ] All endpoints return appropriate HTTP status codes (200, 400, 404, 422).
- [ ] API integration tests pass using `TestClient` or `httpx.AsyncClient`.
- [ ] OpenAPI documentation automatically generated and accessible at `/docs`.
