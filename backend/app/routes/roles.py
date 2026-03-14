from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.knowledge_base.loader import list_domains, load_knowledge_base
from app.knowledge_base.schema import LEVEL_ORDER
from app.models.roles import RoleDetail, RoleLevelSummary, RoleSummary

router = APIRouter()


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
async def get_role(role_id: str) -> RoleDetail:
    try:
        kb = load_knowledge_base(role_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=f"Role not found: {role_id}") from err
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
