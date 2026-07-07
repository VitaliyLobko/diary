import unittest
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from src.database.models import Teacher
from src.repository.teachers import update_teacher
from src.schemas.teachers import TeacherModel


class TestTeacherRepository(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock(spec=Session)

    def test_update_only_touches_provided_fields(self):
        teacher = Teacher(first_name="Old", last_name="Name", is_active=False)
        # is_active is left unset on the body — a partial update must not reset
        # it back to the model default (True).
        body = TeacherModel(first_name="New", last_name="Name", dob="2000-01-01")

        result = update_teacher(body, teacher, self.session)

        self.assertEqual(result.first_name, "New")
        self.assertFalse(result.is_active)
