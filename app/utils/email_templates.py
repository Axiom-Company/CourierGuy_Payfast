"""
Email HTML templates for transactional emails via ZeptoMail.
"""

ORDER_CONFIRMATION_TEMPLATE = """
<html>
<body>
<h2>Order Confirmed - {order_number}</h2>
<p>Thank you for your order!</p>
<p>Total: R{total_zar:.2f}</p>
<p>We will notify you when your order ships.</p>
</body>
</html>
"""

SHIPPING_NOTIFICATION_TEMPLATE = """
<html>
<body>
<h2>Your Order Has Shipped - {order_number}</h2>
<p>Tracking Number: {tracking_number}</p>
<p>Track your parcel: <a href="{tracking_url}">{tracking_url}</a></p>
</body>
</html>
"""

SELLER_SALE_NOTIFICATION_TEMPLATE = """
<html>
<body>
<h2>You Have a New Sale!</h2>
<p>Hi {seller_name},</p>
<p>Great news! Someone purchased your listing:</p>
<p><strong>{listing_title}</strong> x {quantity}</p>
<p>Your earnings: <strong>R{seller_amount:.2f}</strong></p>
<p>Order: {order_number}</p>
<p>Please prepare the item for shipping. You can manage your orders from the seller dashboard.</p>
</body>
</html>
"""

SELLER_PAYOUT_NOTIFICATION_TEMPLATE = """
<html>
<body>
<h2>Payout Created</h2>
<p>Hi {seller_name},</p>
<p>A payout of <strong>R{payout_amount:.2f}</strong> has been created for order {order_number}.</p>
</body>
</html>
"""

DELIVERY_CONFIRMED_SELLER_TEMPLATE = """
<html>
<body>
<h2>Delivery Confirmed</h2>
<p>Hi {seller_name},</p>
<p>The buyer has confirmed delivery for order <strong>{order_number}</strong>.</p>
</body>
</html>
"""

PROMOTION_CONFIRMATION_TEMPLATE = """
<html>
<body>
<h2>Promotion Activated!</h2>
<p>Hi {seller_name},</p>
<p>Your listing <strong>{listing_title}</strong> is now promoted with the <strong>{tier}</strong> tier.</p>
<p>Promotion expires: {expires_at}</p>
</body>
</html>
"""
