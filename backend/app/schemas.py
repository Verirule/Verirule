from pydantic import BaseModel, EmailStr


class AuthPayload(BaseModel):
    email: EmailStr
    password: str
