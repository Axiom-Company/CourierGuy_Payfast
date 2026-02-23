from app.repositories.user_repo import UserRepository
from app.domain.models.user import User
from app.domain.enums import UserRole
from app.domain.schemas.auth import RegisterRequest, TokenResponse, UserBriefResponse
from app.utils.security import hash_password, verify_password, create_access_token


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, data: RegisterRequest) -> TokenResponse:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ValueError("Email already registered")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole.CUSTOMER,
        )
        user = await self.user_repo.create(user)
        token = create_access_token(user.id, user.role.value)

        return TokenResponse(
            access_token=token,
            user=UserBriefResponse.model_validate(user),
        )

    async def login(self, email: str, password: str) -> TokenResponse | None:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            return None

        token = create_access_token(user.id, user.role.value)
        return TokenResponse(
            access_token=token,
            user=UserBriefResponse.model_validate(user),
        )
