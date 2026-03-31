from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import AuthUser, get_current_user
from app.models.materials import MaterialOut, MaterialsResponse
from app.repositories import material_repo, session_repo

router = APIRouter()


@router.get(
    "/materials/{session_id}",
    response_model=MaterialsResponse,
    response_model_by_alias=True,
)
async def get_materials(
    session_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaterialsResponse:
    """Retrieve generated learning materials for a given assessment session."""
    # Verify session exists and belongs to requesting user
    await session_repo.get_session_with_ownership(db, session_id, user.user_id)

    # Fetch materials
    rows = await material_repo.get_materials_by_session(db, session_id)

    return MaterialsResponse(
        session_id=session_id,
        materials=[
            MaterialOut(
                concept_id=row.concept_id,
                domain=row.domain,
                bloom_score=row.bloom_score,
                quality_score=row.quality_score,
                iteration_count=row.iteration_count,
                quality_flag=row.quality_flag,
                material=row.material,
                generated_at=row.generated_at,
            )
            for row in rows
        ],
    )
