## ADDED Requirements

### Requirement: List My Projects Tool
The system SHALL provide a tool that lists the current user’s projects via the management API endpoint `GET /api/projects/my`.

#### Scenario: User-scoped authorization
- **WHEN** the end-user calls the Agent API with an `Authorization: Bearer <token>` header
- **THEN** the tool uses that bearer token to call `GET /api/projects/my`
- **AND** the tool does not expose the bearer token to the model

#### Scenario: Streaming authorization propagation
- **WHEN** the agent workflow is executed in a background task (streaming endpoint)
- **THEN** the end-user bearer token is propagated into that background execution context
- **AND** the tool call remains user-scoped

#### Scenario: List all projects
- **WHEN** the user asks for their projects without specifying a status
- **THEN** the agent uses the tool without the `status` parameter
- **AND** the tool returns a concise list of projects suitable for LLM reasoning

#### Scenario: List projects filtered by status
- **WHEN** the user asks for projects under a specific status
- **THEN** the agent calls the tool with the `status` query parameter

#### Scenario: Status enumeration
- **WHEN** the tool is called with a status filter
- **THEN** the status value is one of: `received`, `accepted`, `initiated`, `invested`, `tracking`, `archived`, `rejected`

#### Scenario: Response shape
- **WHEN** the management API responds
- **THEN** the tool can parse a list of projects from `{ "projects": [...] }` or `{ "items": [...] }`

## MODIFIED Requirements

### Requirement: Tool Routing for Project Questions
The system SHALL prefer the "list my projects" tool for project listing/status overview questions, and SHALL prefer full-text project search for detailed project content queries.

#### Scenario: Project overview question
- **WHEN** the user asks “我有哪些项目？” or similar overview/status questions
- **THEN** the agent calls the list tool first

#### Scenario: Project detail question
- **WHEN** the user asks for specific project content or keyword-based lookup
- **THEN** the agent calls `search_projects` with extracted keywords

## REMOVED Requirements

### Requirement: Retrieval Tool Availability
The system SHALL temporarily disable the `retrieve_context` tool registration until the frontend embedding workflow is integrated.

#### Scenario: Retrieval tool not offered
- **WHEN** the model requests available tools
- **THEN** `retrieve_context` is not present in the available tool list
