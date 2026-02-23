from app.repositories.order_repo import OrderRepository
from app.repositories.cart_repo import CartRepository
from app.repositories.product_repo import ProductRepository
from app.domain.models.order import Order, OrderItem
from app.domain.models.user import User
from app.domain.enums import OrderStatus, PaymentStatus
from app.domain.schemas.checkout import CheckoutRequest
from app.utils.pagination import paginate
from app.domain.schemas.order import OrderResponse


class OrderService:
    def __init__(self, order_repo: OrderRepository, cart_repo: CartRepository, product_repo: ProductRepository):
        self.order_repo = order_repo
        self.cart_repo = cart_repo
        self.product_repo = product_repo

    async def create_from_cart(self, user: User | None, data: CheckoutRequest) -> Order:
        """Convert cart to order. Validates stock, snapshots data, clears cart."""
        if not user and not data.email:
            raise ValueError("Email is required for guest checkout")

        user_id = user.id if user else None
        if not user_id:
            raise ValueError("Cart requires a logged-in user")

        # Get cart items
        cart_items = await self.cart_repo.get_user_cart(user_id)
        if not cart_items:
            raise ValueError("Cart is empty")

        # Validate stock and build order items
        order_items = []
        subtotal = 0.0

        for ci in cart_items:
            product = ci.product
            if not product:
                raise ValueError(f"Product no longer exists for cart item")
            if ci.quantity > product.available_quantity:
                raise ValueError(f"Insufficient stock for '{product.name}': {product.available_quantity} available, {ci.quantity} requested")

            line_total = product.sell_price_zar * ci.quantity
            subtotal += line_total

            order_items.append(OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_type=product.product_type.value,
                condition=product.condition.value if product.condition else None,
                quantity=ci.quantity,
                unit_price_zar=product.sell_price_zar,
                line_total_zar=round(line_total, 2),
                photo_url=product.photo_url,
                tcg_image_small=product.tcg_image_small,
            ))

        # Generate order number
        order_number = await self.order_repo.get_next_order_number()

        # Determine customer info
        email = data.email or (user.email if user else None)
        name = data.full_name or (user.full_name if user else None)
        phone = data.phone or (user.phone if user else None)

        total = round(subtotal + data.shipping_cost_zar, 2)

        # Create order
        order = Order(
            order_number=order_number,
            customer_id=user_id,
            guest_email=data.email if not user else None,
            guest_name=data.full_name if not user else None,
            guest_phone=data.phone if not user else None,
            shipping_method=data.shipping_method,
            shipping_cost_zar=data.shipping_cost_zar,
            shipping_address_line1=data.shipping_address_line1,
            shipping_address_line2=data.shipping_address_line2,
            shipping_city=data.shipping_city,
            shipping_province=data.shipping_province,
            shipping_postal_code=data.shipping_postal_code,
            subtotal_zar=round(subtotal, 2),
            total_zar=total,
            order_status=OrderStatus.PENDING_PAYMENT,
            payment_status=PaymentStatus.PENDING,
            items=order_items,
        )
        order = await self.order_repo.create(order)

        # Clear the cart
        await self.cart_repo.clear_user_cart(user_id)

        return order

    async def get_customer_orders(self, customer_id: str, page: int = 1):
        """Returns paginated customer orders."""
        query = await self.order_repo.get_customer_orders(customer_id)
        return query

    async def get_by_order_number(self, order_number: str) -> Order | None:
        return await self.order_repo.get_by_order_number(order_number)

    async def get_all_orders(self, status=None, page: int = 1):
        """Returns query for all orders (seller view)."""
        query = await self.order_repo.get_all_orders(status)
        return query

    async def update_status(self, order_id: str, status: OrderStatus) -> Order | None:
        return await self.order_repo.update_by_id(order_id, {"order_status": status})

    async def add_tracking(self, order_id: str, tracking_number: str) -> Order | None:
        return await self.order_repo.update_by_id(order_id, {
            "courier_tracking_number": tracking_number,
            "order_status": OrderStatus.SHIPPED,
        })
