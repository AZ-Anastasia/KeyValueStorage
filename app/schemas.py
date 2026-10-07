from pydantic import BaseModel


class SecretCreateDTO(BaseModel):
    key: str
    value: str


class SecretResponseDTO(BaseModel):
    key: str
    value: str