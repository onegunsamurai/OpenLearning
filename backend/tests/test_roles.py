"""Tests for roles API and knowledge base schema validation."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.data.skills_taxonomy import skills_taxonomy
from app.knowledge_base.loader import clear_cache, list_domains, load_knowledge_base
from app.knowledge_base.schema import LEVEL_ORDER, KnowledgeBaseSchema
from app.main import app


@pytest.fixture(autouse=True)
def _clear_kb_cache():
    clear_cache()
    yield
    clear_cache()


class TestListDomains:
    def test_returns_all_domains(self):
        domains = list_domains()
        assert "backend_engineering" in domains
        assert "frontend_engineering" in domains
        assert "devops_engineering" in domains

    def test_sorted(self):
        domains = list_domains()
        assert domains == sorted(domains)

    def test_no_duplicates(self):
        domains = list_domains()
        assert len(domains) == len(set(domains))


class TestKnowledgeBaseSchema:
    @pytest.mark.parametrize("domain", list_domains())
    def test_loads_without_error(self, domain: str):
        kb = load_knowledge_base(domain)
        assert isinstance(kb, KnowledgeBaseSchema)

    @pytest.mark.parametrize("domain", list_domains())
    def test_has_all_levels(self, domain: str):
        kb = load_knowledge_base(domain)
        for level in LEVEL_ORDER:
            assert level in kb.levels, f"Missing level {level} in {domain}"

    @pytest.mark.parametrize("domain", list_domains())
    def test_has_display_name(self, domain: str):
        kb = load_knowledge_base(domain)
        assert kb.display_name, f"Missing display_name in {domain}"

    @pytest.mark.parametrize("domain", list_domains())
    def test_valid_bloom_targets(self, domain: str):
        valid_blooms = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
        kb = load_knowledge_base(domain)
        for level_name, level_data in kb.levels.items():
            for concept in level_data.concepts:
                assert concept.bloom_target in valid_blooms, (
                    f"Invalid bloom target '{concept.bloom_target}' for "
                    f"{concept.concept} in {domain}/{level_name}"
                )

    @pytest.mark.parametrize("domain", list_domains())
    def test_no_duplicate_concepts(self, domain: str):
        kb = load_knowledge_base(domain)
        all_concepts: list[str] = []
        for level_data in kb.levels.values():
            for concept in level_data.concepts:
                all_concepts.append(concept.concept)
        assert len(all_concepts) == len(set(all_concepts)), (
            f"Duplicate concepts in {domain}: "
            f"{[c for c in all_concepts if all_concepts.count(c) > 1]}"
        )

    @pytest.mark.parametrize("domain", list_domains())
    def test_prerequisites_reference_valid_concepts(self, domain: str):
        kb = load_knowledge_base(domain)
        # Collect concepts in order, so we can check prereqs reference earlier/same level concepts
        seen: set[str] = set()
        for level in LEVEL_ORDER:
            level_data = kb.levels.get(level)
            if not level_data:
                continue
            level_concepts = {c.concept for c in level_data.concepts}
            for concept in level_data.concepts:
                for prereq in concept.prerequisites:
                    assert prereq in seen or prereq in level_concepts, (
                        f"Prerequisite '{prereq}' for '{concept.concept}' in "
                        f"{domain}/{level} not found in same or lower levels"
                    )
            seen.update(level_concepts)


class TestMappedSkillIntegrity:
    @pytest.mark.parametrize("domain", list_domains())
    def test_mapped_skills_exist_in_taxonomy(self, domain: str):
        kb = load_knowledge_base(domain)
        taxonomy_ids = {s.id for s in skills_taxonomy}
        for skill_id in kb.mapped_skill_ids:
            assert skill_id in taxonomy_ids, (
                f"Skill '{skill_id}' in {domain}.mapped_skill_ids not in skills_taxonomy"
            )


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestGetRolesEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/roles")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list(self, client: AsyncClient):
        resp = await client.get("/api/roles")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_camel_case_serialization(self, client: AsyncClient):
        resp = await client.get("/api/roles")
        role = resp.json()[0]
        assert "skillCount" in role
        assert "skill_count" not in role

    @pytest.mark.asyncio
    async def test_all_roles_have_required_fields(self, client: AsyncClient):
        resp = await client.get("/api/roles")
        for role in resp.json():
            assert "id" in role
            assert "name" in role
            assert "description" in role
            assert "skillCount" in role
            assert "levels" in role
            assert role["skillCount"] > 0


class TestGetRoleDetailEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/roles/backend_engineering")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_detail(self, client: AsyncClient):
        resp = await client.get("/api/roles/backend_engineering")
        data = resp.json()
        assert data["id"] == "backend_engineering"
        assert data["name"] == "Backend Engineer"
        assert "mappedSkillIds" in data
        assert len(data["mappedSkillIds"]) > 0

    @pytest.mark.asyncio
    async def test_level_summaries(self, client: AsyncClient):
        resp = await client.get("/api/roles/backend_engineering")
        data = resp.json()
        assert "levels" in data
        assert len(data["levels"]) == 4
        for level in data["levels"]:
            assert "name" in level
            assert "conceptCount" in level
            assert level["conceptCount"] > 0

    @pytest.mark.asyncio
    async def test_404_for_unknown(self, client: AsyncClient):
        resp = await client.get("/api/roles/nonexistent_role")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_path_traversal(self, client: AsyncClient):
        resp = await client.get("/api/roles/../../etc/passwd")
        assert resp.status_code in (404, 422)

    @pytest.mark.asyncio
    async def test_rejects_dot_dot(self, client: AsyncClient):
        resp = await client.get("/api/roles/..")
        assert resp.status_code in (404, 422)
