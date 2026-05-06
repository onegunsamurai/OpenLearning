"""LangGraph node attaching free YouTube URLs to ``type="video"`` resources.

Inserted between ``generate_plan`` and ``validate_resources`` (issue #177).
Calls :mod:`app.services.youtube` for HTTP+caching; semantic concerns
(sanitization, relevance, gate, cap, dedupe, plan mutation) live here.
See docs/stories/youtube-video-enrichment/ for the full contract — key
invariants: no LLM in path (AC-10); URL from regex-validated id only (SR-05);
empty key → ``{}`` (AC-2); any exception/timeout → ``{}`` (AC-3, AC-13);
per-plan cap + daily budget + 30 s node timeout (SR-03, SR-04).
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


# ── Module constants (api-contracts.md §2.3) ────────────────────────────

NODE_TIMEOUT_SECONDS: float = 30.0
MAX_CONCURRENT_SEARCHES: int = 5
MIN_JACCARD_RELEVANCE: float = 0.4
MIN_DURATION_SECONDS: int = 90  # excludes Shorts
MAX_DURATION_SECONDS: int = 4 * 3_600  # excludes stream replays

STOP_WORDS: frozenset[str] = frozenset(
    "the a an and or of to in for with on is how intro introduction tutorial guide".split()  # noqa: SIM905
)

TITLE_BLOCKLIST: re.Pattern[str] = re.compile(
    r"(\bmusic\b|official video|lyrics|playlist)", re.IGNORECASE
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


# ── Pure helpers (T3a) ──────────────────────────────────────────────────


def _hash_concept(concept_name: str) -> str:
    """Stable 8-char hex digest used in INFO logs (SR-08)."""
    return hashlib.sha256(concept_name.encode("utf-8", errors="replace")).hexdigest()[:8]


def _tokenize(text: str) -> set[str]:
    """Lowercase, split on non-alphanum, drop stop-words and empties."""
    if not text:
        return set()
    return {tok for tok in TOKEN_SPLIT.split(text.lower()) if tok and tok not in STOP_WORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Recall-style score: ``|a ∩ b| / max(1, |a|)``.

    Despite the name, this is recall of the query bag, not symmetric Jaccard.
    Matches the issue-body formula and deliberately biases toward recall —
    YouTube titles often add noise tokens (channel names, "tutorial",
    episode numbers) that would tank symmetric Jaccard.
    """
    if not a:
        return 0.0
    return len(a & b) / max(1, len(a))


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
    name has <3 tokens.  ``_concept_description`` is in the signature for
    callers but intentionally not in the query (dilutes recall)."""
    base = f"{concept_name} tutorial"
    tokens = [t for t in TOKEN_SPLIT.split(concept_name.lower()) if t]
    if len(tokens) < 3 and skill_domain:
        base = f"{base} {skill_domain}"
    return _sanitize_query(base)


def _normalize_for_dedupe(query: str) -> str:
    """Cache key for per-plan dedupe — case/whitespace must not double-spend."""
    return WHITESPACE_RUN.sub(" ", query.lower()).strip()


def _query_bag(concept: ConceptItem, resource: Resource) -> set[str]:
    """Tokenized query bag — hoisted out of the per-candidate loop (perf)."""
    return _tokenize(f"{concept.name} {concept.description} {resource.title}")


def _passes_relevance(query_bag: set[str], candidate: youtube.VideoCandidate) -> tuple[bool, float]:
    """``(passed, score)`` — threshold :data:`MIN_JACCARD_RELEVANCE`."""
    cand_bag = _tokenize(f"{candidate.title} {candidate.channel_title}")
    score = _jaccard(query_bag, cand_bag)
    return score >= MIN_JACCARD_RELEVANCE, score


def _passes_disqualifiers(candidate: youtube.VideoCandidate, status: youtube.VideoStatus) -> bool:
    """Deterministic binary gate.  Rejects live/upcoming broadcasts, non-processed
    uploads, non-public privacy, non-embeddable, region-blocked, duration outside
    [90 s, 4 h] (Shorts / replays), or titles matching the music/lyrics regex."""
    if (
        candidate.live_broadcast_content != "none"
        or status.upload_status != "processed"
        or status.privacy_status != "public"
        or not status.embeddable
        or status.region_restriction_blocked
        or not (MIN_DURATION_SECONDS <= status.duration_seconds <= MAX_DURATION_SECONDS)
    ):
        return False
    return not TITLE_BLOCKLIST.search(candidate.title or "")


def _select_best(
    candidates: list[tuple[youtube.VideoCandidate, youtube.VideoStatus, float]],
) -> tuple[youtube.VideoCandidate, float] | None:
    """Return the highest-scoring ``(candidate, score)`` pair, or ``None``.
    Ties broken by stable list order."""
    if not candidates:
        return None
    best_cand, _, best_score = max(candidates, key=lambda triple: triple[2])
    return best_cand, best_score


# ── Async node (T3b) ────────────────────────────────────────────────────


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

    # Phase 1 — dedupe pre-fan-out (AC-12, race-free).
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

    # Hard errors propagate to the outer try/except (contract: feature off → {}).
    per_concept_candidates: list[tuple[ConceptItem, Resource, list[youtube.VideoCandidate]]] = []
    for norm, result in zip(ordered_norms, search_results, strict=True):
        if isinstance(result, BaseException):
            raise result
        for concept, resource in consumers[norm]:
            per_concept_candidates.append((concept, resource, result))

    # Phase 2 — one batched status lookup for every unique candidate id.
    seen: set[str] = set()
    candidate_ids: list[str] = []
    for _, _, cands in per_concept_candidates:
        for c in cands:
            if c.video_id not in seen:
                seen.add(c.video_id)
                candidate_ids.append(c.video_id)
    statuses = await youtube.lookup(candidate_ids) if candidate_ids else {}

    # Phase 3 — relevance + disqualifier gate, pick the highest-scoring survivor.
    for concept, resource, cands in per_concept_candidates:
        bag = _query_bag(concept, resource)
        survivors: list[tuple[youtube.VideoCandidate, youtube.VideoStatus, float]] = []
        for cand in cands:
            status = statuses.get(cand.video_id)
            if status is None or not _passes_disqualifiers(cand, status):
                continue
            ok, score = _passes_relevance(bag, cand)
            if ok:
                survivors.append((cand, status, score))
        pick = _select_best(survivors)
        if pick is None:
            logger.debug("video_enricher.no_match concept_hash=%s", _hash_concept(concept.name))
            continue
        best_cand, best_score = pick
        _attach_url(resource, best_cand.video_id)
        logger.info(
            "video_enricher.attached concept_hash=%s video_id=%s jaccard=%.2f",
            _hash_concept(concept.name),
            best_cand.video_id,
            best_score,
        )

    return {"learning_plan": plan}


async def enrich_videos(state: AssessmentState) -> dict:
    """LangGraph node — attach YouTube URLs to ``type="video"`` resources.
    Wraps the body in :data:`NODE_TIMEOUT_SECONDS` and converts every error
    path to ``{}`` (plan ships unchanged)."""
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
