from fastapi import APIRouter

from app.data.skills_taxonomy import skill_categories, skills_taxonomy
from app.models.skills import SkillsResponse

router = APIRouter()


@router.get("/skills", response_model=SkillsResponse, response_model_by_alias=True)
async def get_skills() -> SkillsResponse:
    return SkillsResponse(skills=skills_taxonomy, categories=skill_categories)
