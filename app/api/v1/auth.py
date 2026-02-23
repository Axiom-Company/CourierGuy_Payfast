from fastapi import APIRouter, Depends, HTTPException
from app.domain.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth_service import AuthService
from app.api.deps import get_auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    try:
        return await service.register(data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)):
    result = await service.login(data.email, data.password)
    if not result:
        raise HTTPException(401, "Invalid email or password")
    return result
