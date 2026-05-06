"""LangGraph node attaching free YouTube URLs to ``type="video"`` resources.

Inserted between ``generate_plan`` and ``validate_resources`` (issue #177).
Calls :mod:`app.services.youtube` for HTTP+caching; semantic concerns
(query sanitization, simple gate, cap, dedupe, plan mutation) live here.

Key invariants:
* No LLM in the discovery path (AC-10).
* URL constructed from the regex-validated ``video_id`` only — never from any
  string field of the API response (SR-05 / T-03).
* Empty ``YOUTUBE_API_KEY`` → ``{}`` (feature flag, AC-2).
* Any exception/timeout → ``{}`` so the plan ships unchanged (AC-3, AC-13).
* Per-plan cap + daily-budget breaker + 30 s node timeout (SR-03, SR-04).
* PII / search-operator stripping on outbound query (SR-02 / SR-11).

Quality gate (deliberately minimal — a previous Jaccard-recall + tokenized
relevance check rejected everything in practice). The gate now answers one
question per candidate: "is this obviously trash?" via three cheap rules:

1. Drop live / upcoming broadcasts (the URL would be unstable).
2. Drop YouTube Shorts (duration < 90 s).
3. Drop titles that look like music / lyrics / official-video uploads.

Pick the first candidate that survives. No relevance scoring — we trust
YouTube's own ranking.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re

from app.config import Settings, get_settings
from app.graph.state import AssessmentState, ConceptItem, LearningPlan, Resource
from app.services import youtube

logger = logging.getLogger(__name__)


# ── Module constants ────────────────────────────────────────────────────

MIN_DURATION_SECONDS: int = 90  # filter Shorts

# Title blocklist for obvious garbage. "playlist" is intentionally NOT here —
# legit tutorial channels often label videos "X tutorial — playlist".
TITLE_BLOCKLIST: re.Pattern[str] = re.compile(
    r"(\bmusic\b|\blyrics\b|official video|official audio)", re.IGNORECASE
)

PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b[\w._%+-]+@[\w.-]+\.\w{2,}\b"),  # email
    re.compile(r"\b\+?\d[\d\s().-]{7,}\d\b"),  # phone
    re.compile(r"\b[A-Z][a-zA-Z]+ (?:Inc|LLC|Corp|GmbH)\b"),  # company suffix
)
SEARCH_OPERATORS: re.Pattern[str] = re.compile(r'\b(site:|intitle:|inurl:)|"', re.IGNORECASE)
CONTROL_CHARS: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]")
WHITESPACE_RUN: re.Pattern[str] = re.compile(r"\s+")
TOKEN_SPLIT: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
QUERY_MAX_LENGTH: int = 100
DAILY_QUOTA_BUDGET_SOFT_LIMIT: float = 0.80


# ── Pure helpers ────────────────────────────────────────────────────────


def _hash_concept(concept_name: str) -> str:
    """Stable 8-char hex digest used in INFO logs (SR-08)."""
    return hashlib.sha256(concept_name.encode("utf-8", errors="replace")).hexdigest()[:8]


def _sanitize_query(raw: str) -> str:
    """Strip PII / operators / control chars; collapse whitespace; truncate
    to :data:`QUERY_MAX_LENGTH` (SR-02 / SR-11)."""
    text = raw or ""
    for pat in PII_PATTERNS:
        text = pat.sub(" ", text)
    text = SEARCH_OPERATORS.sub(" ", text)
    text = CONTROL_CHARS.sub(" ", text)
    text = WHITESPACE_RUN.sub(" ", text).strip()
    return text[:QUERY_MAX_LENGTH]


def _build_query(concept_name: str, _concept_description: str, skill_domain: str) -> str:
    """``"<concept_name> tutorial"``, with ``skill_domain`` appended when the
    name has <3 tokens. Description is intentionally not in the query
    (dilutes recall against YouTube titles)."""
    base = f"{concept_name} tutorial"
    tokens = [t for t in TOKEN_SPLIT.split(concept_name.lower()) if t]
    if len(tokens) < 3 and skill_domain:
        base = f"{base} {skill_domain}"
    return _sanitize_query(base)


def _normalize_for_dedupe(query: str) -> str:
    """Cache key for per-plan dedupe — case/whitespace must not double-spend."""
    return WHITESPACE_RUN.sub(" ", query.lower()).strip()


def _passes_filter(candidate: youtube.VideoCandidate, status: youtube.VideoStatus) -> bool:
    """Simple sanity gate: drop live broadcasts, Shorts, and obvious garbage titles."""
    if candidate.live_broadcast_content != "none":
        return False
    if status.duration_seconds < MIN_DURATION_SECONDS:
        return False
    return not TITLE_BLOCKLIST.search(candidate.title or "")


# ── Async node ──────────────────────────────────────────────────────────


async def _bounded_search(raw_query: str, sem: asyncio.Semaphore) -> list[youtube.VideoCandidate]:
    """Run one search.list call under the concurrency semaphore."""
    async with sem:
        return await youtube.search(raw_query)


def _budget_exhausted(settings: Settings) -> bool:
    """SR-03 — circuit breaker fires at 80% of daily quota."""
    used = youtube.quota_used_today()
    soft_limit = int(DAILY_QUOTA_BUDGET_SOFT_LIMIT * settings.youtube_daily_quota_budget)
    return used >= soft_limit


def _attach_url(resource: Resource, video_id: str) -> str:
    """Construct the YouTube URL ourselves from the validated id (SR-05)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    resource.url = url
    return url


def _gather_video_resources(plan: LearningPlan) -> list[tuple[ConceptItem, Resource]]:
    """``(concept, resource)`` pairs needing enrichment (type=video, url=None)."""
    return [
        (concept, resource)
        for phase in plan.phases
        for concept in phase.concepts
        for resource in concept.resources
        if resource.type == "video" and not resource.url
    ]


async def _enrich_videos_body(state: AssessmentState) -> dict:
    """Inner body — wrapped by :func:`enrich_videos` in the timeout / try-except."""
    settings = get_settings()
    if not settings.youtube_api_key.get_secret_value():
        logger.debug("video_enricher.disabled")
        return {}

    plan: LearningPlan | None = state.get("learning_plan")
    if not plan or not plan.phases:
        return {}

    pending = _gather_video_resources(plan)
    if not pending:
        return {}

    skill_domain = state.get("skill_domain", "backend_engineering")
    cap = settings.max_video_lookups_per_plan
    sem = asyncio.Semaphore(settings.youtube_max_concurrent_searches)

    if _budget_exhausted(settings):
        logger.warning(
            "video_enricher.budget_reached used=%d budget=%d",
            youtube.quota_used_today(),
            settings.youtube_daily_quota_budget,
        )
        return {"learning_plan": plan}

    selected = pending[:cap]
    if len(pending) > cap:
        logger.info("video_enricher.cap_reached cap=%d", cap)

    # Phase 1 — dedupe pre-fan-out (race-free).
    raw_for_norm: dict[str, str] = {}
    consumers: dict[str, list[tuple[ConceptItem, Resource]]] = {}
    ordered_norms: list[str] = []
    for concept, resource in selected:
        raw = _build_query(concept.name, concept.description, skill_domain)
        norm = _normalize_for_dedupe(raw)
        if norm in consumers:
            logger.debug("video_enricher.dedupe concept_hash=%s", _hash_concept(concept.name))
        else:
            consumers[norm], raw_for_norm[norm] = [], raw
            ordered_norms.append(norm)
        consumers[norm].append((concept, resource))

    search_tasks = [_bounded_search(raw_for_norm[norm], sem) for norm in ordered_norms]
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Hard errors propagate to outer try/except (contract: feature off → {}).
    per_concept_candidates: list[tuple[ConceptItem, Resource, list[youtube.VideoCandidate]]] = []
    for norm, result in zip(ordered_norms, search_results, strict=True):
        if isinstance(result, BaseException):
            raise result
        for concept, resource in consumers[norm]:
            per_concept_candidates.append((concept, resource, result))

    # Phase 2 — one batched status lookup so we know each candidate's duration
    # and live status. Quota: 1 unit / batched call ≤ 50 ids.
    seen: set[str] = set()
    candidate_ids: list[str] = []
    for _, _, cands in per_concept_candidates:
        for c in cands:
            if c.video_id not in seen:
                seen.add(c.video_id)
                candidate_ids.append(c.video_id)
    statuses = await youtube.lookup(candidate_ids) if candidate_ids else {}

    # Phase 3 — pick the first candidate that survives the simple gate.
    for concept, resource, cands in per_concept_candidates:
        picked: youtube.VideoCandidate | None = None
        for cand in cands:
            status = statuses.get(cand.video_id)
            if status is None:
                continue
            if _passes_filter(cand, status):
                picked = cand
                break
        if picked is None:
            logger.debug("video_enricher.no_match concept_hash=%s", _hash_concept(concept.name))
            continue
        _attach_url(resource, picked.video_id)
        logger.info(
            "video_enricher.attached concept_hash=%s video_id=%s",
            _hash_concept(concept.name),
            picked.video_id,
        )

    return {"learning_plan": plan}


async def enrich_videos(state: AssessmentState) -> dict:
    """LangGraph node — attach YouTube URLs to ``type="video"`` resources.
    Wraps the body in the operator-configured node timeout and converts every
    error path to ``{}`` (plan ships unchanged)."""
    settings = get_settings()
    try:
        return await asyncio.wait_for(
            _enrich_videos_body(state),
            timeout=settings.youtube_node_timeout_seconds,
        )
    except TimeoutError:
        logger.warning("video_enricher.timeout")
        return {}
    except youtube.YouTubeAPIError as exc:
        logger.warning(
            "video_enricher.api_error status=%d retry_after=%s",
            exc.status_code,
            exc.retry_after_seconds,
        )
        return {}
    except Exception:
        # Defence in depth — never let an unexpected error reach the SSE stream.
        logger.warning("video_enricher.unexpected")
        return {}
