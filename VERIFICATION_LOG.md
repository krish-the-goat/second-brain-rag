# Verification Log

✓ Step 1.1 — Fix Prompt Injection — ran `test_pipeline_quick.py`, confirmed user input `<` and `>` are escaped as `&lt;` and `&gt;` inside the `<USER_QUERY>` boundary.
✓ Step 1.2 — Fix Cache Leakage — ran `test_pipeline_quick.py`, confirmed changing the global API_KEY produces a completely different SHA256 cache key for the exact same prompt and history.
✓ Step 1.3 — Fix SSRF TOCTOU — ran `test_web_loader_fix.py`, confirmed using `curl --resolve` bypasses DNS rebinding entirely and strictly enforces a 5MB size limit. Tested successfully against `localhost`.
✓ Step 2.1 — Migrate _PARENT_STORE to Redis — ran `test_chunker_quick.py`, confirmed chunks are mapped correctly to parent text and stored sequentially in Redis during ingest.
✓ Step 2.2 — Wrap Blocking I/O — ran `test_graph_async.py`, confirmed `asyncio.to_thread` is correctly applied to synchronous Neo4j database calls (`manager.add_entity`, `manager.add_relationship`, `manager.get_related_context`) to prevent event loop blocking.
✓ Step 3.1 — Concurrent Graph Extraction — visually confirmed `documents.py` implements an `asyncio.gather` bounded by an `asyncio.Semaphore(2)` to limit concurrent Neo4j graph extractions.
✓ Step 3.2 — LLM Fallback Loop — ran `test_llm_fallback.py`, confirmed `llm_manager.py` switches back to the primary provider if the fallback provider also rate limits.
✓ Step 3.3 — Batch Embeddings — ran `test_batch_embed.py`, confirmed arrays of texts are correctly sliced into chunks of 32 prior to passing to `model.encode`.
✓ Step 4.1 — Pipeline Test Coverage — created `test_pipeline_new.py` testing Prompt Injection escaping, Payload generation for multiple providers, Cache key isolation, and Citation generation.
✓ Step 1 — Security: Fix pipeline.py exception logging — ran pipeline test, no syntax errors, regex/replace confirmed visual check.
✓ Step 2 — Architecture: Decouple documents.py — Decoupled into app/rag/ingestion.py and successfully loaded via python interpreter.
✓ Step 3 — Reliability: Fix main.py TOCTOU middleware race condition — Used atomic increment_metric. Checked syntax.
✓ Step 4 — Reliability: Fix metrics.py division edge cases and blocking event loop — verified via python interpreter.
✓ Step 5 — Performance: Rewrite bm25_store.py to SQLite FTS5 — verified via python interpreter.
✓ Step 6 — Performance: Fix ChromaDB get_stats() OOM risk — verified via python interpreter.
✓ Step 7 — Testing: Write E2E test test_chat_stream.py — Executed pytest, endpoint successfully streamed SSE format chunks and passed.
✓ Step 1 — frontend URL upload UI — modified FileUpload.tsx, added useMutation, validated using npx tsc --noEmit. Success.
