# 0003 — pgvector inside PostgreSQL for embeddings

**Context.** RAG and semantic mentor search need vector similarity search over at most
tens of thousands of chunks, combined with relational filters (price, skills, location).

**Decision.** Store embeddings in a `vector(n)` column in PostgreSQL with an HNSW index;
retrieval is one SQL query that combines vector distance with ordinary WHERE clauses.

**Alternatives.** *Qdrant / Weaviate / Pinecone*: purpose-built and faster at very large
scale, but one more system to run, sync and back up, and filters must be duplicated.

**Consequences.** One database, transactional consistency between rows and their vectors,
hybrid queries are trivial. If vector volume grows by orders of magnitude, revisit.
