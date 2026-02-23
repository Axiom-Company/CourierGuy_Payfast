from app.repositories.cart_repo import CartRepository
from app.repositories.product_repo import ProductRepository
from app.domain.models.cart import CartItem
from app.domain.schemas.cart import CartItemResponse, CartResponse


class CartService:
    def __init__(self, cart_repo: CartRepository, product_repo: ProductRepository):
        self.cart_repo = cart_repo
        self.product_repo = product_repo

    async def get_cart(self, user_id: str) -> CartResponse:
        """Get full cart with enriched product data."""
        cart_items = await self.cart_repo.get_user_cart(user_id)
        items = []
        subtotal = 0.0
        total_weight = 0

        for ci in cart_items:
            product = ci.product
            if not product:
                continue
            line_total = product.sell_price_zar * ci.quantity
            subtotal += line_total
            total_weight += product.weight_grams * ci.quantity

            items.append(CartItemResponse(
                id=ci.id,
                product_id=product.id,
                product_name=product.name,
                product_type=product.product_type.value,
                condition=product.condition.value if product.condition else None,
                sell_price_zar=product.sell_price_zar,
                quantity=ci.quantity,
                line_total_zar=round(line_total, 2),
                tcg_image_small=product.tcg_image_small,
                photo_url=product.photo_url,
                is_in_stock=product.is_in_stock,
                available_quantity=product.available_quantity,
            ))

        return CartResponse(
            items=items,
            item_count=sum(i.quantity for i in items),
            subtotal_zar=round(subtotal, 2),
            total_weight_grams=total_weight,
        )

    async def add_item(self, user_id: str, product_id: str, quantity: int) -> CartItemResponse:
        """Add item to cart. If already in cart, increment quantity."""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise ValueError("Product not found")
        if not product.is_in_stock:
            raise ValueError(f"'{product.name}' is out of stock")
        if quantity > product.available_quantity:
            raise ValueError(f"Only {product.available_quantity} available for '{product.name}'")

        existing = await self.cart_repo.get_user_cart_item(user_id, product_id)
        if existing:
            new_qty = existing.quantity + quantity
            if new_qty > product.available_quantity:
                raise ValueError(f"Only {product.available_quantity} available for '{product.name}'")
            await self.cart_repo.update_by_id(existing.id, {"quantity": new_qty})
            existing.quantity = new_qty
            ci = existing
        else:
            ci = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
            ci = await self.cart_repo.create(ci)

        line_total = product.sell_price_zar * ci.quantity
        return CartItemResponse(
            id=ci.id,
            product_id=product.id,
            product_name=product.name,
            product_type=product.product_type.value,
            condition=product.condition.value if product.condition else None,
            sell_price_zar=product.sell_price_zar,
            quantity=ci.quantity,
            line_total_zar=round(line_total, 2),
            tcg_image_small=product.tcg_image_small,
            photo_url=product.photo_url,
            is_in_stock=product.is_in_stock,
            available_quantity=product.available_quantity,
        )

    async def update_item(self, item_id: str, quantity: int) -> CartItemResponse | None:
        """Update cart item quantity."""
        ci = await self.cart_repo.get_by_id(item_id)
        if not ci:
            raise ValueError("Cart item not found")
        product = await self.product_repo.get_by_id(ci.product_id)
        if not product:
            raise ValueError("Product not found")
        if quantity > product.available_quantity:
            raise ValueError(f"Only {product.available_quantity} available")

        await self.cart_repo.update_by_id(item_id, {"quantity": quantity})
        line_total = product.sell_price_zar * quantity
        return CartItemResponse(
            id=ci.id,
            product_id=product.id,
            product_name=product.name,
            product_type=product.product_type.value,
            condition=product.condition.value if product.condition else None,
            sell_price_zar=product.sell_price_zar,
            quantity=quantity,
            line_total_zar=round(line_total, 2),
            tcg_image_small=product.tcg_image_small,
            photo_url=product.photo_url,
            is_in_stock=product.is_in_stock,
            available_quantity=product.available_quantity,
        )

    async def remove_item(self, item_id: str) -> None:
        await self.cart_repo.delete_by_id(item_id)

    async def clear_cart(self, user_id: str) -> None:
        await self.cart_repo.clear_user_cart(user_id)
