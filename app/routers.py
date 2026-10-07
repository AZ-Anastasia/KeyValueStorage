from fastapi import APIRouter, status, HTTPException
from app.database import VaultRepository
from app.schemas import SecretCreateDTO, SecretResponseDTO

router = APIRouter(prefix="/api/v1/secrets", tags=["Secrets Operations"])
repo = VaultRepository()

@router.post("", status_code=status.HTTP_201_CREATED)
async def save_secret(payload: SecretCreateDTO):
    await repo.save_secret(key=payload.key, value=payload.value)
    return {"status": "success", "message": f"Secret '{payload.key}' saved"}

@router.get("/{key}", response_model=SecretResponseDTO)
async def get_secret(key: str):
    value = await repo.get_secret_by_key(key)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret with key '{key}' not found"
        )
    return SecretResponseDTO(key=key,value=value)

@router.get("", response_model=list[str])
async def get_all_keys():
    return await repo.get_all_keys()