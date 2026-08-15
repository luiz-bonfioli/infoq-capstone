"""Node: Knowledge Retrieval (RAG Service).

Uses a LangChain `InMemoryVectorStore` + `OpenAIEmbeddings` to retrieve
relevant organizational knowledge (company standards, previous test cases,
testing guidelines, product documentation) for the preprocessed feature.

TODO: Swap `InMemoryVectorStore` + `COMPANY_KNOWLEDGE_SEED` for a real
persistent vector DB backed by an ingestion pipeline (pgvector, Pinecone,
Chroma, ...), and add metadata filtering (product area, tags) plus hybrid
search + reranking, as described in project.md.
"""

from __future__ import annotations

import logging

from app.knowledge_base import COMPANY_KNOWLEDGE_SEED
from app.llm_config import build_http_client, llm_configured
from app.nodes.utils import safe_node
from app.state import PipelineState

logger = logging.getLogger(__name__)

_vectorstore = None  # lazily built, module-level cache


def _get_vectorstore():
    """Build (once) and return the in-memory vector store over seed knowledge."""
    global _vectorstore
    if _vectorstore is None:
        from langchain_core.vectorstores import InMemoryVectorStore
        from langchain_openai import OpenAIEmbeddings

        _vectorstore = InMemoryVectorStore.from_documents(
            COMPANY_KNOWLEDGE_SEED,
            OpenAIEmbeddings(model="text-embedding-3-small", http_client=build_http_client()),
        )
    return _vectorstore


@safe_node("rag_retrieval")
def rag_retrieval(state: PipelineState) -> dict:
    """Retrieve relevant organizational knowledge for the feature.

    Args:
        state: Current pipeline state. Requires `feature_markdown` and
            `feature_metadata`.

    Returns:
        Partial state update with `retrieved_context`.
    """
    if not llm_configured():
        logger.warning("OPENAI_API_KEY not set - skipping real retrieval, returning empty context.")
        return {"retrieved_context": []}

    query = state.get("feature_markdown", "") or state.get("aha_feature_id", "")
    results = _get_vectorstore().similarity_search(query, k=4)

    retrieved_context = [
        {"content": doc.page_content, "metadata": doc.metadata} for doc in results
    ]
    return {"retrieved_context": retrieved_context}
