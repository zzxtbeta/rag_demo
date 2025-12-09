# Chat Interface Specification

## MODIFIED Requirements

### Requirement: Message Rendering
The system SHALL render assistant messages with full Markdown support including images, tables, and code blocks.

#### Scenario: Render Markdown images
- **WHEN** assistant message contains Markdown image syntax `![alt](/documents/images/xxx.jpg)`
- **THEN** frontend displays the image inline with text
- **AND** images are responsive (max-width: 100%, auto height)
- **AND** images have rounded corners and proper spacing

#### Scenario: Render Markdown tables
- **WHEN** assistant message contains Markdown table syntax
- **THEN** frontend displays table with borders and padding
- **AND** table is readable and properly formatted

#### Scenario: Render code blocks
- **WHEN** assistant message contains code blocks (triple backticks)
- **THEN** frontend displays code with syntax highlighting background
- **AND** inline code has different styling from block code
- **AND** code is scrollable if it exceeds container width

#### Scenario: Render headings and lists
- **WHEN** assistant message contains Markdown headings and lists
- **THEN** frontend displays with appropriate sizing and spacing
- **AND** heading hierarchy is visually distinct (h1, h2, h3)
- **AND** lists have proper indentation and bullet styling

### Requirement: LLM Image Guidance
The system SHALL guide LLM to include images in responses when relevant.

#### Scenario: LLM includes image references
- **WHEN** LLM generates response about document content with images
- **THEN** LLM includes Markdown image syntax in response
- **AND** LLM does not describe images as "unable to display"
- **AND** image URLs match files in `FRONTEND_IMAGES_DIR`

#### Scenario: Image placement
- **WHEN** LLM includes images in response
- **THEN** images are placed inline with related text (not at end)
- **AND** images have descriptive alt text
- **AND** images are grouped with explanatory content
