import unittest
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from src.database.models import Student
from src.repository.students import create_student, get_students
from src.schemas.students import StudentModel


class TestStudentRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = MagicMock(spec=Session)

    async def test_create_student(self):
        body = StudentModel(
            is_active=True,
            first_name="TestName",
            last_name="TestLastName",
            dob="2021-01-01",
            group_id=1,
        )
        result = await create_student(body, self.session)
        self.assertEqual(result.first_name, body.first_name)
        self.assertEqual(result.last_name, body.last_name)
        self.assertEqual(result.dob, body.dob)
        self.assertEqual(result.group_id, body.group_id)
        self.assertTrue(hasattr(result, "is_active"))

    async def test_get_students(self):
        groups = [Student(), Student(), Student()]
        self.session.query().order_by().limit().offset().all.return_value = groups
        result = await get_students("", 10, 0, self.session)
        self.assertEqual(result, groups)
