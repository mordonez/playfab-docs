# PlayFab Documentation Expertise

This context defines the language for building and consuming a local, source-backed knowledge base of Microsoft PlayFab documentation.

## Language

**PlayFab Context Builder**:
The product that creates and maintains a source-backed PlayFab Documentation Library for local use.
_Avoid_: PlayFab scraper, Liferay fork

**PlayFab Expert**:
The agent skill that answers PlayFab questions using evidence from the PlayFab Documentation Library.
_Avoid_: PlayFab bot, generic PlayFab assistant

**PlayFab Documentation Library**:
The locally available collection of PlayFab documentation used as grounding material by PlayFab Expert.
_Avoid_: Corpus, docs dump, mirror

**Official Guide**:
An editorial PlayFab document that explains a product concept, workflow, SDK, or operational practice.
_Avoid_: API page, generic article

**REST API Reference**:
An official PlayFab reference document that defines a REST service, operation, request, response, authentication requirement, or error contract.
_Avoid_: Guide, tutorial

**Content Status**:
The lifecycle state explicitly communicated by a source page: Current, Preview, Maintenance, or Legacy.
_Avoid_: Freshness, publication date

**Current**:
Content describing a generally available approach that the source does not mark as preview, maintenance, or legacy.

**Preview**:
Content the source explicitly identifies as not yet generally available.

**Maintenance**:
Content for a supported capability that receives fixes but no new features, as explicitly stated by the source.

**Legacy**:
Content the source explicitly identifies as superseded, obsolete, or intended only for older integrations.
_Avoid_: Old

**Canonical Source**:
The English (`en-us`) Microsoft Learn page retained as the single local representation of a PlayFab document.
_Avoid_: English translation, localized copy

**Documentation Manifest**:
An official Microsoft Learn table-of-contents document that defines the discoverable membership and hierarchy of a PlayFab source family.
_Avoid_: Sitemap, crawl result

**Discovered Document**:
A Canonical Source listed by a Documentation Manifest and therefore eligible for the PlayFab Documentation Library.
_Avoid_: Any internal link, crawled page

**Coverage Gap**:
An in-scope-looking PlayFab link found in official content but absent from the corresponding Documentation Manifest.
_Avoid_: Missing page, crawl failure

**Document Metadata**:
Source-provided facts that identify and qualify a Discovered Document, including its canonical URL, source family, hierarchy, lifecycle state, update date, service, and API version when available.
_Avoid_: Page chrome, generated summary

**Extraction Anomaly**:
Evidence that a Discovered Document could not be faithfully represented, such as missing content, restricted access, or an unexpected page structure.
_Avoid_: Documentation error, Coverage Gap

**Source Type**:
The kind of official evidence represented by a document: Official Guide or REST API Reference.
_Avoid_: Category, area

**TOC Path**:
The complete hierarchy assigned to a Discovered Document by its Documentation Manifest.
_Avoid_: File path, breadcrumb

**Product Area**:
The top-level PlayFab functional area to which an Official Guide belongs, as derived from its TOC Path.
_Avoid_: Source type, API surface, capability

**API Surface**:
The PlayFab service boundary under which a REST API Reference is published, such as Admin, Client, Server, Authentication, Economy, or Multiplayer.
_Avoid_: Product area, endpoint

**External Official Reference**:
A link from a Canonical Source to official material outside the Documentation Manifests, retained as a pointer but not represented as local content.
_Avoid_: Coverage Gap, Discovered Document

**Retired Document**:
A previously Discovered Document no longer listed by its Documentation Manifest and therefore excluded from normal retrieval while its last local representation is preserved.
_Avoid_: Deleted page, Legacy
