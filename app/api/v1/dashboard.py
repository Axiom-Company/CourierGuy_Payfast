from fastapi import APIRouter, Depends
from app.services.dashboard_service import DashboardService
from app.api.deps import get_dashboard_service, require_admin
from app.domain.schemas.dashboard import DashboardResponse
from app.domain.models.user import Profile

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/admin", response_model=DashboardResponse)
async def admin_dashboard(
    admin: Profile = Depends(require_admin),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_dashboard()
