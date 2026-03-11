from .base import CamelModel


class Skill(CamelModel):
    id: str
    name: str
    category: str
    icon: str
    description: str
    sub_skills: list[str]


class SkillsResponse(CamelModel):
    skills: list[Skill]
    categories: list[str]
