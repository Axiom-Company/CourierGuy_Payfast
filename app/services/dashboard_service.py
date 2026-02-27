from datetime import datetime, timedelta, date, timezone
from sqlalchemy import select, func, case, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.order import Order
from app.domain.enums import OrderStatus, PaymentStatus
from app.domain.schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
    RevenueByDay,
    StatusBreakdown,
)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self) -> DashboardResponse:
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        week_start = today_start - timedelta(days=now.weekday())  # Monday 00:00
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        thirty_days_ago = today_start - timedelta(days=29)  # inclusive of today = 30 days

        stats = await self._build_stats(today_start, week_start, month_start)
        revenue_by_day = await self._revenue_by_day(thirty_days_ago)
        status_breakdown = await self._status_breakdown()
        recent_orders = await self._recent_orders()

        return DashboardResponse(
            stats=stats,
            revenue_by_day=revenue_by_day,
            status_breakdown=status_breakdown,
            recent_orders=recent_orders,
        )

    async def _build_stats(
        self,
        today_start: datetime,
        week_start: datetime,
        month_start: datetime,
    ) -> DashboardStats:
        # -- Aggregate counts and revenue in a single query --
        result = await self.db.execute(
            select(
                func.count(Order.id).label("total_orders"),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.payment_status == PaymentStatus.COMPLETE, Order.total_zar),
                            else_=0.0,
                        )
                    ),
                    0.0,
                ).label("total_revenue"),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.payment_status == PaymentStatus.COMPLETE, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("paid_orders"),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.order_status == OrderStatus.PENDING_PAYMENT, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("pending_orders"),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.order_status == OrderStatus.SHIPPED, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("shipped_orders"),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.order_status == OrderStatus.DELIVERED, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("delivered_orders"),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.order_status == OrderStatus.CANCELLED, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("cancelled_orders"),
            )
        )
        row = result.one()
        total_orders: int = row.total_orders or 0
        total_revenue: float = float(row.total_revenue or 0.0)
        paid_orders: int = row.paid_orders or 0

        avg_order_value = round(total_revenue / paid_orders, 2) if paid_orders > 0 else 0.0

        # -- Time-windowed counts (all orders regardless of payment) --
        orders_today, revenue_today = await self._period_stats(today_start)
        orders_week, revenue_week = await self._period_stats(week_start)
        orders_month, revenue_month = await self._period_stats(month_start)

        return DashboardStats(
            total_orders=total_orders,
            total_revenue_zar=round(total_revenue, 2),
            paid_orders=paid_orders,
            pending_orders=row.pending_orders or 0,
            shipped_orders=row.shipped_orders or 0,
            delivered_orders=row.delivered_orders or 0,
            cancelled_orders=row.cancelled_orders or 0,
            avg_order_value_zar=avg_order_value,
            orders_today=orders_today,
            revenue_today_zar=revenue_today,
            orders_this_week=orders_week,
            revenue_this_week_zar=revenue_week,
            orders_this_month=orders_month,
            revenue_this_month_zar=revenue_month,
        )

    async def _period_stats(self, since: datetime) -> tuple[int, float]:
        """Return (order_count, revenue) for orders created on or after `since`.
        order_count = ALL orders, revenue = only payment_status='complete'."""
        result = await self.db.execute(
            select(
                func.count(Order.id).label("order_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.payment_status == PaymentStatus.COMPLETE, Order.total_zar),
                            else_=0.0,
                        )
                    ),
                    0.0,
                ).label("revenue"),
            ).where(Order.created_at >= since)
        )
        row = result.one()
        return (row.order_count or 0, round(float(row.revenue or 0.0), 2))

    async def _revenue_by_day(self, since: datetime) -> list[RevenueByDay]:
        """Revenue grouped by calendar date for the last 30 days.
        Only orders with payment_status='complete'."""
        order_date = cast(Order.created_at, Date).label("order_date")
        result = await self.db.execute(
            select(
                order_date,
                func.coalesce(func.sum(Order.total_zar), 0.0).label("revenue"),
                func.count(Order.id).label("order_count"),
            )
            .where(
                Order.created_at >= since,
                Order.payment_status == PaymentStatus.COMPLETE,
            )
            .group_by(order_date)
            .order_by(order_date)
        )
        rows = result.all()
        return [
            RevenueByDay(
                date=row.order_date.isoformat() if isinstance(row.order_date, date) else str(row.order_date),
                revenue_zar=round(float(row.revenue), 2),
                order_count=row.order_count,
            )
            for row in rows
        ]

    async def _status_breakdown(self) -> list[StatusBreakdown]:
        """Count of orders per order_status."""
        result = await self.db.execute(
            select(
                Order.order_status,
                func.count(Order.id).label("cnt"),
            )
            .group_by(Order.order_status)
            .order_by(func.count(Order.id).desc())
        )
        rows = result.all()
        return [
            StatusBreakdown(
                status=row.order_status.value if hasattr(row.order_status, "value") else str(row.order_status),
                count=row.cnt,
            )
            for row in rows
        ]

    async def _recent_orders(self, limit: int = 5) -> list[dict]:
        """Most recent 5 orders with key display fields."""
        result = await self.db.execute(
            select(
                Order.order_number,
                Order.guest_name,
                Order.guest_email,
                Order.total_zar,
                Order.order_status,
                Order.payment_status,
                Order.created_at,
            )
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {
                "order_number": row.order_number,
                "guest_name": row.guest_name,
                "guest_email": row.guest_email,
                "total_zar": round(float(row.total_zar), 2),
                "order_status": row.order_status.value if hasattr(row.order_status, "value") else str(row.order_status),
                "payment_status": row.payment_status.value if hasattr(row.payment_status, "value") else str(row.payment_status),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
