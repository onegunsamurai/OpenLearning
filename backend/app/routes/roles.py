from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.knowledge_base.loader import list_domains, load_knowledge_base
from app.knowledge_base.schema import LEVEL_ORDER
from app.models.roles import RoleDetail, RoleLevelSummary, RoleSummary

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
