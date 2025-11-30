import uuid
import pytest
from app.schemas import TeacherProfile, PedagogyConfig, ContentScope
from app.services.profile_service import get_profile_service
from ingest.infra.postgres import PostgresStructureNodeRepository

# We use the real DB connection from the service
# Ensure the schema exists first
@pytest.fixture(scope="module")
def ensure_schema():
    repo = PostgresStructureNodeRepository()
    repo.ensure_schema()

@pytest.fixture
def profile_service(ensure_schema):
    return get_profile_service()

def test_create_and_get_profile(profile_service):
    # Create
    new_profile = TeacherProfile(
        user_id="test_user_1",
        name="Mr. Test",
        grade_level="10",
        pedagogy_config=PedagogyConfig(tone="formal", style="academic")
    )
    created = profile_service.create_profile(new_profile)
    assert created.id is not None
    assert created.name == "Mr. Test"

    # Get
    fetched = profile_service.get_profile(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.pedagogy_config.tone == "formal"

def test_update_profile(profile_service):
    # Setup
    p = TeacherProfile(user_id="u2", name="Original", grade_level="5")
    created = profile_service.create_profile(p)

    # Update
    created.name = "Updated Name"
    created.pedagogy_config.tone = "playful"
    updated = profile_service.update_profile(created.id, created)

    assert updated.name == "Updated Name"
    assert updated.pedagogy_config.tone == "playful"

    # Verify persistence
    fetched = profile_service.get_profile(created.id)
    assert fetched.name == "Updated Name"

def test_list_profiles(profile_service):
    # Create unique user to filter
    uid = f"user_{uuid.uuid4()}"
    p1 = TeacherProfile(user_id=uid, name="P1")
    p2 = TeacherProfile(user_id=uid, name="P2")
    profile_service.create_profile(p1)
    profile_service.create_profile(p2)

    # List
    profiles = profile_service.list_profiles(user_id=uid)
    assert len(profiles) >= 2
    names = [p.name for p in profiles]
    assert "P1" in names
    assert "P2" in names
