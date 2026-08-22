"""Node: Knowledge Retrieval (RAG Service).

Uses a LangChain `InMemoryVectorStore` + `OpenAIEmbeddings` to retrieve
relevant company knowledge for the preprocessed feature. The corpus
(`COMPANY_KNOWLEDGE_SEED` in `app/knowledge_base.py`) holds both the
test-case/ticket standards (naming, coverage, structure, ...) and
problem-domain knowledge (performance, auth, uploads, exports, RBAC, ...)
so a weak ticket - one missing detail about the problem it addresses -
gets grounded in the company knowledge that fills that gap.

Every retrieved chunk is tagged with a human-readable `source_label`
("Company standard" vs "Company knowledge") so downstream prompting can
attribute the extra info.

TODO: Swap `InMemoryVectorStore` + `COMPANY_KNOWLEDGE_SEED` for a real
persistent vector DB backed by an ingestion pipeline (pgvector, Pinecone,
Chroma, ...), and add metadata filtering (product area, tags) plus hybrid
search + reranking, as described in project.md.
"""

from __future__ import annotations

import logging
from collections import Counter

from app.knowledge_base import COMPANY_KNOWLEDGE_SEED
from app.llm_config import build_http_client, embeddings_model_name, llm_configured
from app.nodes.utils import safe_node
from app.state import PipelineState

logger = logging.getLogger(__name__)

_vectorstores: dict[str, object] = {}  # lazily built, keyed by embeddings model

# Knowledge source filename (from chunk metadata) -> human-readable label.
_SOURCE_LABELS = {
    "company_patterns.md": "Company standard",
    "company_knowledge.md": "Company knowledge",
}

TOP_K = 6  # retrieve enough to surface both standards and domain knowledge


def _get_vectorstore():
    """Build (once per embeddings model) and return the in-memory vector store."""
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain_openai import OpenAIEmbeddings

    model = embeddings_model_name()
    vectorstore = _vectorstores.get(model)
    if vectorstore is None:
        vectorstore = InMemoryVectorStore.from_documents(
            COMPANY_KNOWLEDGE_SEED,
            OpenAIEmbeddings(model=model, http_client=build_http_client()),
        )
        _vectorstores[model] = vectorstore
    return vectorstore


def reset_vectorstore_cache() -> None:
    """Drop cached vector stores so an embeddings-model swap takes effect in-process."""
    _vectorstores.clear()


def _source_label(metadata: dict) -> str:
    """Map a chunk's knowledge source to a human-readable label."""
    source = metadata.get("source", "")
    return _SOURCE_LABELS.get(source, source or "Retrieved knowledge")


@safe_node("rag_retrieval")
def rag_retrieval(state: PipelineState) -> dict:
    """Retrieve relevant company knowledge for the feature.

    Args:
        state: Current pipeline state. Requires `feature_markdown` and
            `feature_metadata`.

    Returns:
        Partial state update with `retrieved_context`. Each item carries
        `content`, `metadata`, and a `source_label` ("Company standard" /
        "Company knowledge") for downstream attribution.
    """
    if not llm_configured():
        logger.warning("OPENAI_API_KEY not set - skipping real retrieval, returning empty context.")
        return {"retrieved_context": []}

    query = state.get("feature_markdown", "") or state.get("aha_feature_id", "")
    results = _get_vectorstore().similarity_search(query, k=TOP_K)

    retrieved_context = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "source_label": _source_label(doc.metadata),
        }
        for doc in results
    ]

    sources = Counter(item["source_label"] for item in retrieved_context)
    logger.info(
        "rag_retrieval: retrieved %d chunk(s) for feature '%s' - sources: %s",
        len(retrieved_context),
        state.get("aha_feature_id"),
        dict(sources) or "(none)",
    )
    return {"retrieved_context": retrieved_context}
