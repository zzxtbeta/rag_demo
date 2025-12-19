# RAG System Specification

## ADDED Requirements

### Requirement: Retrieval Tool Toggle
The system SHALL support enabling and disabling vector retrieval tools via environment configuration and per-request overrides.

#### Scenario: Disable retrieval globally
- **WHEN** `RETRIEVAL_ENABLED=false`
- **THEN** the system SHALL NOT expose `retrieve_context` to the model
- **AND** the system SHALL NOT execute retrieval tool calls

#### Scenario: Enable retrieval globally
- **WHEN** `RETRIEVAL_ENABLED=true`
- **THEN** the system SHALL expose `retrieve_context` to the model by default

#### Scenario: Disable retrieval per request
- **WHEN** `RETRIEVAL_ENABLED=true`
- **AND** a chat request sets `enable_retrieval=false`
- **THEN** the system SHALL NOT expose `retrieve_context` to the model for that request
