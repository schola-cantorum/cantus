---
name: fastapi-pydantic-openapi
description: FastAPI auto-generates OpenAPI 3.1 schemas from Pydantic models, and Pydantic Settings provides type-safe environment-driven configuration with SecretStr.
topic: research
sources:
  - url: https://deepwiki.com/fastapi/fastapi/3.1-openapi-schema-generation
    title: FastAPI OpenAPI 3.1 schema generation (deepwiki)
  - url: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    title: Pydantic — Settings management
---

## Overview

FastAPI and Pydantic together form a near-default Python stack for typed HTTP services: route handlers declare Pydantic models for request and response bodies, and FastAPI synthesizes an OpenAPI 3.1 schema from those types without a separate schema file (per FastAPI deepwiki page). Pydantic's `pydantic-settings` package extends the same type-driven philosophy to configuration, loading values from environment variables, `.env` files, and other sources into typed model instances (per pydantic docs page). The combination delivers a single source of truth for both the HTTP wire contract and the runtime configuration surface.

## Key claims

- FastAPI generates OpenAPI 3.1 (not the older 3.0) by default, reflecting Pydantic v2's JSON Schema output (per deepwiki page).
- Pydantic Settings supports environment-variable loading, prefixed env vars, `.env` files, and nested model loading (per pydantic-settings docs page).
- `SecretStr` is a Pydantic field type whose `repr` and default string conversion redact the underlying value, intended to prevent accidental log/exception leakage of credentials (per pydantic docs — the SecretStr section of the settings/types concept pages documents this redaction behavior).
- The recommended way to access a `SecretStr`'s plaintext is the explicit `.get_secret_value()` call, which makes leak sites greppable in code review (unverified — the exact API name is from general Pydantic usage; confirm against the linked settings page before quoting).

## Relevance to cantus

Cantus's planned `cantus-serve-core` change builds its HTTP surface on FastAPI + Pydantic, so OpenAPI generation comes "for free" and is the basis for the wiki's eventual API reference. More importantly, the `ARCH-2` audit checklist requires that secret-bearing configuration fields use `SecretStr` and that no code path stringifies them outside an explicit `.get_secret_value()` call. This entry is the canonical pointer for both the OpenAPI behavior the wiki documents and the `SecretStr` discipline the audit checklist enforces, and it underwrites the two-tier API principle (high-level convenience layer over a typed core) that cantus follows throughout.
