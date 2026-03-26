from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.knowledge_base.loader import build_topic_agenda, list_domains, load_knowledge_base
from app.knowledge_base.schema import LEVEL_ORDER
from app.models.roles import (
    ConceptSummary,
    RoleConceptsResponse,
    RoleDetail,
    RoleLevelSummary,
    RoleSummary,
)

router = APIRouter()


async def valid_role_id(
    role_id: str = Path(...),
) -> str:
    """Validate that role_id matches a known knowledge base domain."""
    if role_id not in list_domains():
        raise HTTPException(status_code=404, detail=f"Role not found: {role_id}")
    return role_id


ValidRoleId = Annotated[str, Depends(valid_role_id)]


@router.get("/roles", response_model=list[RoleSummary], response_model_by_alias=True)
async def get_roles() -> list[RoleSummary]:
    summaries: list[RoleSummary] = []
    for domain in list_domains():
        kb = load_knowledge_base(domain)
        summaries.append(
            RoleSummary(
                id=kb.domain,
                name=kb.display_name,
                description=kb.description,
                skill_count=len(kb.mapped_skill_ids),
                levels=[lvl for lvl in LEVEL_ORDER if lvl in kb.levels],
            )
        )
    return summaries


@router.get("/roles/{role_id}", response_model=RoleDetail, response_model_by_alias=True)
async def get_role(role_id: ValidRoleId) -> RoleDetail:
    kb = load_knowledge_base(role_id)
    return RoleDetail(
        id=kb.domain,
        name=kb.display_name,
        description=kb.description,
        mapped_skill_ids=kb.mapped_skill_ids,
        levels=[
            RoleLevelSummary(name=lvl, concept_count=len(kb.levels[lvl].concepts))
            for lvl in LEVEL_ORDER
            if lvl in kb.levels
        ],
    )


@router.get(
    "/roles/{role_id}/concepts",
    response_model=RoleConceptsResponse,
    response_model_by_alias=True,
)
async def get_role_concepts(
    role_id: ValidRoleId,
    level: str = "mid",
) -> RoleConceptsResponse:
    """Return concepts for a role up to the given level, topologically sorted."""
    if level not in LEVEL_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid level: {level}")

    kb = load_knowledge_base(role_id)
    agenda = build_topic_agenda(role_id, level)

    # Build a lookup for display names from the KB schema
    display_names: dict[str, str] = {}
    for lvl in LEVEL_ORDER:
        level_data = kb.levels.get(lvl)
        if level_data:
            for c in level_data.concepts:
                display_names[c.concept] = c.display_name or c.concept.replace("_", " ").title()

    return RoleConceptsResponse(
        concepts=[
            ConceptSummary(
                id=item.concept,
                display_name=display_names.get(
                    item.concept, item.concept.replace("_", " ").title()
                ),
                level=item.level,
                prerequisites=item.prerequisites,
            )
            for item in agenda
        ]
    )
