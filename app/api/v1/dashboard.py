from fastapi import APIRouter, Depends
from app.services.dashboard_service import DashboardService
from app.api.deps import get_dashboard_service, require_admin_api_key
from app.domain.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/admin", response_model=DashboardResponse)
async def admin_dashboard(
    _=Depends(require_admin_api_key),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_dashboard()
