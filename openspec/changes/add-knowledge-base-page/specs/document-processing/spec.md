# Document Processing Specification

## ADDED Requirements

### Requirement: Knowledge Base Ingestion UI
The system SHALL provide a dedicated Knowledge Base user interface to ingest documents into the vector store without requiring chat interaction.

#### Scenario: User embeds uploaded documents via UI
- **WHEN** user opens the Knowledge Base page and selects the Embed Upload tab
- **AND** user uploads up to 4 supported files
- **THEN** frontend calls `POST /agent/documents/embed`
- **AND** UI shows per-file results including embedded/skipped/error and chunks created

#### Scenario: User imports MinerU output via UI
- **WHEN** user opens the Knowledge Base page and selects the MinerU Import tab
- **AND** user provides a valid MinerU `source_path`
- **THEN** frontend calls `POST /agent/documents/process-mineru`
- **AND** UI shows processing summary including chunks_created and embedded flag

#### Scenario: Collection selection
- **WHEN** user specifies a `collection_name`
- **THEN** ingestion requests target that collection
- **AND** if omitted, backend default collection is used
