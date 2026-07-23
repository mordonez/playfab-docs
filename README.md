# playfab-context-builder

Build a local, source-backed PlayFab Documentation Library for the `playfab-expert` agent skill.

The builder discovers official content from Microsoft Learn's root and product-area PlayFab table-of-contents manifests, extracts clean Markdown with Crawl4AI, and publishes an atomic local snapshot with a searchable JSONL index. The package does not redistribute Microsoft documentation.

## Sources

- Official Guides under `https://learn.microsoft.com/en-us/xbox/playfab/`
- REST API References under `https://learn.microsoft.com/en-us/rest/api/playfab/?view=playfab-rest`

English (`en-us`) pages are canonical. External repositories, community content, authenticated pages, and localized duplicates are outside the first-version scope.

## Quickstart

Requirements: Python 3.10–3.13, [`uv`](https://docs.astral.sh/uv/), and Node/npm for skill installation.

```bash
# One-time browser setup
uvx --from crawl4ai crawl4ai-setup

# Build ~/.playfab-docs
uvx playfab-context-builder

# Inspect docs freshness and skill installation
uvx --from playfab-context-builder playfab-context-builder-doctor
```

For a small live test:

```bash
uvx playfab-context-builder --max-pages 5 --use-cache
```

Use `PLAYFAB_DOCS_DIR` to select a custom location:

```bash
export PLAYFAB_DOCS_DIR="$PWD/.playfab-docs"
uv run playfab-context-builder --max-pages 5 --use-cache
```

## Library layout

```text
~/.playfab-docs/
├── raw/
│   ├── official-guide/{product-area}/*.md
│   ├── rest-api/{api-surface}/*.md
│   └── _retired/{source-type}/.../*.md
└── reports/
    ├── search_index.jsonl
    ├── anomalies.jsonl
    ├── coverage_gaps.jsonl
    ├── external_references.jsonl
    ├── manifest_changes.jsonl
    ├── fetch_failures.jsonl
    └── summary.json
```

Each refresh is built in a sibling staging directory and published atomically. A hard extraction failure never overwrites a valid previous page. Documents removed from a Microsoft Learn TOC are preserved under `_retired/` and excluded from normal search.

## Filters

```bash
uv run playfab-context-builder --source-type official-guide
uv run playfab-context-builder --source-type rest-api --surface admin
uv run playfab-context-builder --area multiplayer
uv run playfab-context-builder --concurrency 2
```

Concurrency is capped at three. Filtered or page-limited builds do not retire documents excluded by the filter.

## Development

```bash
uv sync --dev
uv run ruff check .
uv run pytest
uv build
```

The normal test suite is offline. The opt-in live smoke test requires browsers and network access:

```bash
PLAYFAB_RUN_LIVE_TESTS=1 uv run pytest -m live
```

## Skill

The canonical skill lives at `skills/playfab-expert/SKILL.md`. Install it for a supported agent with the `skills` CLI after publishing or directly from a repository checkout.

## License

The builder and skill are MIT licensed. Content fetched from Microsoft Learn remains subject to Microsoft's terms and is not included in this package.
