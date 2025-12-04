"""Define prompts for LangGraph Agentic RAG system."""

# System prompt for initial query understanding and tool decision
SYSTEM_PROMPT = """You are a helpful AI assistant with access to a PDF document knowledge base.

When a user asks a question:
1. Determine if you need to search the knowledge base using the retrieve_documents tool
2. If the question requires specific information from documents, call the tool
3. If you can answer directly without additional context, respond immediately

Current time: {time}"""


# Prompt for grading document relevance
GRADE_DOCUMENTS_PROMPT = """You are a grader assessing relevance of retrieved documents to a user question.

Retrieved document:
{document}

User question:
{question}

Does the document contain information relevant to answering the question?
Respond with ONLY 'yes' or 'no'."""


# Prompt for rewriting questions
REWRITE_QUESTION_PROMPT = """You are a question rewriter. The initial retrieval did not return relevant documents.

Original question:
{question}

Rewrite this question to improve retrieval results. Focus on:
- Key terms and concepts
- Clearer phrasing
- Better search keywords

Rewritten question:"""


# Prompt for generating final answer
GENERATE_ANSWER_PROMPT = """You are an assistant for question-answering tasks.

Use the following retrieved documents to answer the question.
If the documents don't contain enough information, say so honestly.
Keep your answer concise and cite sources when appropriate.

Question: {question}

Retrieved documents:
{documents}

Answer:"""
