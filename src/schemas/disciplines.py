from pydantic import BaseModel


class DisciplineModel(BaseModel):
    name: str
    teacher_id: int


class DisciplineResponse(DisciplineModel):
    id: int
