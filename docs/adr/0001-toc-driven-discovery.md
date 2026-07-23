# Use Microsoft Learn TOCs for discovery and Crawl4AI for extraction

The PlayFab Context Builder uses the official Microsoft Learn `toc.json` manifests as the authority for which Official Guides and REST API References belong to the PlayFab Documentation Library. This includes the root PlayFab and REST manifests plus the product-area manifests linked by the root navigation, because the root guide manifest exposes area hubs without expanding their article trees. Crawl4AI fetches and extracts those discovered pages, but its link-following crawl does not define coverage; this makes discovery deterministic and auditable while avoiding the coverage gaps and scope drift inherent in BFS crawling.

## Considered Options

- **TOC-driven discovery**: selected because Microsoft Learn publishes complete, source-family-specific navigation manifests.
- **BFS deep crawling**: rejected as the primary discovery mechanism because reachability through page links is a weaker and less stable definition of documentation membership.

## Consequences

Links that appear to be in scope but are absent from the corresponding TOC are reported as Coverage Gaps instead of being silently added. Each refresh can reconcile the current manifest with the previous one to identify additions and removals.
