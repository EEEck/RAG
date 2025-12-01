from __future__ import annotations

import json
import uuid
from typing import List, Optional

import psycopg
from psycopg.rows import dict_row

from ..schemas import TeacherProfile, PedagogyConfig, ContentScope
# We reuse the connection logic from ingest to avoid duplication
from ingest.infra.connection import get_connection

class ProfileService:
    """
    Service for managing Teacher Profiles.
    """

    def create_profile(self, profile: TeacherProfile) -> TeacherProfile:
        """
        Creates a new teacher profile in the database.
        """
        # If ID is not provided, generate one (though DB default also works,
        # providing it here ensures we return it consistent with model)
        if not profile.id:
            profile.id = str(uuid.uuid4())

        query = """
        INSERT INTO teacher_profiles (
            id, user_id, name, grade_level, pedagogy_config, content_scope, book_list
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, created_at, updated_at;
        """

        with get_connection(db_type="user") as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (
                    profile.id,
                    profile.user_id,
                    profile.name,
                    profile.grade_level,
                    json.dumps(profile.pedagogy_config.model_dump()),
                    json.dumps(profile.content_scope.model_dump()),
                    profile.book_list
                ))
                row = cur.fetchone()
                conn.commit()

        if row:
            # profile.created_at = row['created_at'] # Model doesn't have these yet?
            # Let's check schemas.py. It does not.
            pass

        return profile

    def get_profile(self, profile_id: str) -> Optional[TeacherProfile]:
        """
        Retrieves a profile by ID.
        """
        query = "SELECT * FROM teacher_profiles WHERE id = %s"

        with get_connection(db_type="user") as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (profile_id,))
                row = cur.fetchone()

        if not row:
            return None

        return self._map_row_to_profile(row)

    def list_profiles(self, user_id: Optional[str] = None) -> List[TeacherProfile]:
        """
        Lists profiles, optionally filtered by user_id.
        """
        if user_id:
            query = "SELECT * FROM teacher_profiles WHERE user_id = %s"
            params = (user_id,)
        else:
            query = "SELECT * FROM teacher_profiles"
            params = ()

        with get_connection(db_type="user") as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return [self._map_row_to_profile(row) for row in rows]

    def update_profile(self, profile_id: str, updates: TeacherProfile) -> Optional[TeacherProfile]:
        """
        Updates an existing profile.
        """
        # Note: We overwrite the config/scope completely with the new value
        query = """
        UPDATE teacher_profiles
        SET name = %s,
            grade_level = %s,
            pedagogy_config = %s,
            content_scope = %s,
            book_list = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING *;
        """

        with get_connection(db_type="user") as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (
                    updates.name,
                    updates.grade_level,
                    json.dumps(updates.pedagogy_config.model_dump()),
                    json.dumps(updates.content_scope.model_dump()),
                    updates.book_list,
                    profile_id
                ))
                row = cur.fetchone()
                conn.commit()

        if not row:
            return None

        return self._map_row_to_profile(row)

    def _map_row_to_profile(self, row: dict) -> TeacherProfile:
        """
        Helper to map DB row to Pydantic model.
        """
        pedagogy = row.get('pedagogy_config') or {}
        scope = row.get('content_scope') or {}
        book_list = row.get('book_list') or []

        # Handle case where JSONB comes back as string (depending on driver config)
        if isinstance(pedagogy, str):
            pedagogy = json.loads(pedagogy)
        if isinstance(scope, str):
            scope = json.loads(scope)
        if isinstance(book_list, str):
            book_list = json.loads(book_list)

        return TeacherProfile(
            id=str(row['id']),
            user_id=row['user_id'],
            name=row['name'],
            grade_level=row['grade_level'],
            pedagogy_config=PedagogyConfig(**pedagogy),
            content_scope=ContentScope(**scope),
            book_list=book_list
        )

# Singleton or factory
_profile_service = ProfileService()

def get_profile_service() -> ProfileService:
    return _profile_service
