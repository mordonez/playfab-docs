---
name: playfab-expert
description: Answer Microsoft PlayFab technical questions by searching and reading the local source-backed PlayFab Documentation Library. Use for PlayFab concepts, configuration, SDKs, LiveOps, Economy, Multiplayer, identity, player data, troubleshooting, and exact REST API contracts.
---

# PlayFab Expert

Ground PlayFab answers in the local documentation library. Do not answer from memory alone when this skill applies.

## 1. Resolve the library

Use `$PLAYFAB_DOCS_DIR` when set; otherwise use `~/.playfab-docs`. Call it `$DOCS_DIR` below.

If `$DOCS_DIR/reports/search_index.jsonl` is absent or empty, tell the user to run:

```bash
uvx --from crawl4ai crawl4ai-setup
uvx playfab-context-builder
```

Do not start a full build during an ordinary question. It can take significant time and the user should decide when to wait.

If the latest `reports/summary.json` is older than seven days, mention that the library may be stale and continue answering from it. The refresh command is `uvx playfab-context-builder`.

## 2. Discover, read, answer

1. Search `reports/search_index.jsonl` with `rg -i` or `grep -i`, trying two or three exact and conceptual keyword variants.
2. Use `source_type`, `toc_path`, `product_area`, `api_surface`, `content_status`, title, headings, service, and API version to shortlist results.
3. Read the best matching Markdown files in full using their `path` fields.
4. If metadata search is insufficient, search bodies under `$DOCS_DIR/raw/official-guide/` and `$DOCS_DIR/raw/rest-api/` directly.
5. Do not use normal results from `$DOCS_DIR/raw/_retired/`. Use a retired page only as a last resort and clearly say it is no longer in the current Microsoft Learn TOC.
6. Cite each source's `url` frontmatter near the claims it supports.

## 3. Evidence precedence

- For concepts, recommendations, setup, tutorials, and operational procedures, prefer a current `official-guide`.
- For endpoints, HTTP methods, authentication, request fields, response models, API versions, and error contracts, prefer `rest-api`.
- Prefer `current` over `preview`, `maintenance`, and `legacy` when multiple sources answer the same question.
- Use preview, maintenance, or legacy sources when the user explicitly asks about them or their technical context requires them. State the status before recommending the approach.
- If an Official Guide and REST API Reference disagree, expose the conflict. Include their statuses and update dates when available; use the REST reference for the exact wire contract and the current guide for recommended workflow.
- Never infer lifecycle status only from age. Trust the stored `content_status`, which is based on explicit source language.

## 4. Answering rules

- Answer in the user's language.
- Preserve official product, API, type, field, and endpoint names exactly.
- Distinguish PlayFab product generations explicitly, such as Economy v1/v2, Leaderboards v1/v2, standalone SDKs, and Unified SDK.
- Do not silently combine code or steps from incompatible generations.
- If evidence is incomplete, say what was found and what is missing. Do not fill the gap with an uncited guess.
- Links listed in `reports/external_references.jsonl` are pointers only. Do not claim their content was read locally.
- `reports/anomalies.jsonl` is informational. If a cited page has an anomaly, mention that the local extraction may need verification.
- `reports/coverage_gaps.jsonl` contains PlayFab-looking links absent from the official manifests. Treat them as missing coverage, not normal sources.

## 5. Useful diagnostics

```bash
uvx --from playfab-context-builder playfab-context-builder-doctor
```

The doctor checks library presence, freshness, index size, abandoned staging directories, and skill installation. It does not crawl or install anything.

