# Chat Interface Specification

## MODIFIED Requirements

### Requirement: Tool Controls
The system SHALL allow callers to toggle agent tool availability per request.

#### Scenario: Request-level retrieval toggle
- **WHEN** caller sets `enable_retrieval` on the chat request
- **THEN** the agent respects that value when deciding which tools are available
