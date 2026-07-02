from pydantic import BaseModel


class ContactModel(BaseModel):
    contact_type: str
    contact_value: str


class ContactResponse(ContactModel):
    pass
