"""
Email HTML templates stub.
Extend these when EmailService is wired to SMTP.
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
