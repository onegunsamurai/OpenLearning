from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AssessmentSession, MaterialResult, get_db
from app.deps import AuthUser, get_current_user
from app.models.materials import MaterialOut, MaterialsResponse

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
    session_result = await db.execute(
        select(AssessmentSession).where(AssessmentSession.session_id == session_id)
    )
    session_row = session_result.scalar_one_or_none()
    if not session_row:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_row.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch materials
    result = await db.execute(select(MaterialResult).where(MaterialResult.session_id == session_id))
    rows = result.scalars().all()

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
