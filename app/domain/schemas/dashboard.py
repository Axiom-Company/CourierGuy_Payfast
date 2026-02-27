from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_orders: int
    total_revenue_zar: float
    paid_orders: int
    pending_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int
    avg_order_value_zar: float
    orders_today: int
    revenue_today_zar: float
    orders_this_week: int
    revenue_this_week_zar: float
    orders_this_month: int
    revenue_this_month_zar: float


class RevenueByDay(BaseModel):
    date: str
    revenue_zar: float
    order_count: int


class StatusBreakdown(BaseModel):
    status: str
    count: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    revenue_by_day: list[RevenueByDay]
    status_breakdown: list[StatusBreakdown]
    recent_orders: list[dict]
