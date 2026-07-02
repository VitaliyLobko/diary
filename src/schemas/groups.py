from pydantic import BaseModel


class GroupModel(BaseModel):
    name: str


class GroupResponse(GroupModel):
    id: int
