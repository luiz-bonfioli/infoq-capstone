# ICAIE Capstone Project Deliverable

## Project

### Title
**AI-Powered Test Case Generation from Aha! Features Using RAG**

### Problem Statement

Quality Assurance engineers spend a significant amount of time manually creating test cases from feature requests stored in Aha!. The process is repetitive, inconsistent, and highly dependent on individual experience, often leading to missing edge cases and delayed feature validation.

The proposed solution is an AI-powered assistant that automatically analyzes feature requirements, retrieves relevant organizational knowledge using Retrieval-Augmented Generation (RAG), and generates high-quality TestRail test cases for human review.

### Objectives

- Reduce manual test design effort by at least **30%**
- Improve consistency and completeness of test cases
- Increase coverage of edge and negative scenarios
- Standardize testing practices across engineering teams

### Success Metrics

| Metric | Target |
|---------|--------|
| Test case creation effort | -30% |
| Test coverage | Increased edge-case coverage |
| Review effort | Reduced rework |
| User adoption | Positive feedback from QA teams |

---

# High-Level Architecture

```text
                    +------------------+
                    |      Aha!        |
                    +------------------+
                              |
                              v
                 Feature Extraction Service
                              |
                              v
                    Document Preprocessing
                 (Markdown + Attachments)
                              |
                              v
                     Knowledge Retrieval
        +-----------------------------------------+
        |               RAG Service               |
        |-----------------------------------------|
        | Company Standards                       |
        | Previous Test Cases                     |
        | Testing Guidelines                      |
        | Product Documentation                   |
        +-----------------------------------------+
                              |
                              v
                            LLM
                              |
                              v
                AI Generated Test Cases
                              |
                              v
                     Human QA Review
                              |
                              v
                         TestRail
```

## High-Level Design

### Components

- **Aha! Extractor** – Retrieves feature descriptions, acceptance criteria, comments, and attachments.
- **Preprocessing** – Converts documents into structured Markdown and extracts metadata.
- **RAG Service** – Retrieves relevant organizational knowledge from a vector database.
- **LLM** – Generates structured test cases using retrieved context.
- **Human Review** – QA engineers validate and adjust generated results.
- **TestRail Integration** – Publishes approved test cases.

### Data Flow

1. Feature is created in Aha!.
2. AI extracts and preprocesses the content.
3. Relevant documents are retrieved from the RAG.
4. The LLM generates proposed test cases.
5. QA reviews the output.
6. Approved test cases are published to TestRail.

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Hallucinated test cases | Human review + RAG grounding |
| Outdated documentation | Regular knowledge ingestion |
| Missing context | Metadata filtering and retrieval optimization |
| Poor retrieval | Hybrid search and reranking |

---

# Article Outline

## Title

**Applying RAG to Accelerate Software Test Design**

## Outline

1. Introduction
2. The Challenge of Manual Test Design
3. Why Traditional AI Is Not Enough
4. Using RAG to Ground Test Generation
5. Proposed Architecture
6. Knowledge Sources
7. Human-in-the-Loop Validation
8. Expected Business Benefits
9. Challenges and Future Improvements
10. Conclusion
