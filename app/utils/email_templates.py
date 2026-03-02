"""
Branded HTML email templates for Elite TCG transactional emails via ZeptoMail.
Brand: Yellow (#FFD700), White (#FFFFFF), Dark text (#1a1a1a), Accent gold (#D4A800)
All currency in ZAR (R).
"""

# ── Base wrapper ──────────────────────────────────────────────────────────────

_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{subject}</title>
<style>
  body {{ margin:0; padding:0; background:#f4f4f4; font-family:Arial,Helvetica,sans-serif; color:#1a1a1a; }}
  .wrapper {{ max-width:600px; margin:0 auto; background:#ffffff; }}
  .header {{ background:#1a1a1a; padding:24px; text-align:center; }}
  .header h1 {{ margin:0; font-size:28px; letter-spacing:2px; }}
  .header h1 span {{ color:#FFD700; }}
  .header h1 .tcg {{ color:#ffffff; }}
  .body {{ padding:32px 24px; }}
  .body h2 {{ color:#1a1a1a; margin-top:0; font-size:22px; }}
  .body p {{ line-height:1.6; margin:12px 0; color:#333; }}
  .btn {{ display:inline-block; padding:14px 28px; background:#FFD700; color:#1a1a1a; text-decoration:none;
           font-weight:bold; border-radius:6px; margin:16px 0; }}
  .btn:hover {{ background:#D4A800; }}
  .divider {{ border:0; border-top:2px solid #FFD700; margin:24px 0; }}
  .order-table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
  .order-table th {{ background:#1a1a1a; color:#FFD700; padding:10px 12px; text-align:left; font-size:13px; }}
  .order-table td {{ padding:10px 12px; border-bottom:1px solid #eee; font-size:14px; }}
  .total-row td {{ font-weight:bold; border-top:2px solid #FFD700; font-size:15px; }}
  .highlight {{ background:#FFF9E0; padding:16px; border-left:4px solid #FFD700; border-radius:4px; margin:16px 0; }}
  .footer {{ background:#1a1a1a; padding:20px 24px; text-align:center; color:#999; font-size:12px; }}
  .footer a {{ color:#FFD700; text-decoration:none; }}
  .tracking-box {{ background:#f9f9f9; border:1px solid #ddd; border-radius:6px; padding:16px; text-align:center; margin:16px 0; }}
  .tracking-box .number {{ font-size:20px; font-weight:bold; color:#1a1a1a; letter-spacing:1px; }}
  @media (max-width:600px) {{
    .body {{ padding:20px 16px; }}
    .header {{ padding:16px; }}
    .header h1 {{ font-size:22px; }}
  }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1><span>ELITE</span> <span class="tcg">TCG</span></h1>
  </div>
  <div class="body">
    {content}
  </div>
  <div class="footer">
    <p>&copy; {year} Elite TCG &mdash; South Africa's Pokemon TCG Store</p>
    <p><a href="https://www.elitetcg.co.za">www.elitetcg.co.za</a></p>
  </div>
</div>
</body>
</html>"""


def _wrap(subject: str, content: str) -> str:
    from datetime import datetime
    return _BASE.format(subject=subject, content=content, year=datetime.now().year)


# ── 1. Welcome ────────────────────────────────────────────────────────────────

def welcome_template(name: str) -> str:
    content = f"""
    <h2>Welcome to Elite TCG! ⚡</h2>
    <p>Hey {name},</p>
    <p>Thanks for joining the Elite TCG community! You now have access to South Africa's premier Pokemon TCG store.</p>
    <div class="highlight">
      <strong>What you can do:</strong>
      <ul style="margin:8px 0;padding-left:20px;">
        <li>Browse our curated collection of sealed products &amp; singles</li>
        <li>List and sell your own cards on the marketplace</li>
        <li>Get notified when new drops land</li>
        <li>Track your orders in real time</li>
      </ul>
    </div>
    <p style="text-align:center;">
      <a href="https://www.elitetcg.co.za/shop" class="btn">Start Shopping</a>
    </p>
    <p>Welcome aboard,<br/><strong>The Elite TCG Team</strong></p>
    """
    return _wrap("Welcome to Elite TCG", content)


# ── 2. Order Confirmation ─────────────────────────────────────────────────────

def order_confirmation_template(
    name: str, order_number: str, order_items: list[dict],
    subtotal: float, shipping_cost: float, total: float,
    shipping_address: str, order_date: str,
) -> str:
    rows = ""
    for item in order_items:
        rows += f"""<tr>
          <td>{item['name']}</td>
          <td style="text-align:center;">{item['quantity']}</td>
          <td style="text-align:right;">R{item['unit_price']:.2f}</td>
          <td style="text-align:right;">R{item['line_total']:.2f}</td>
        </tr>"""

    content = f"""
    <h2>Order Confirmed — {order_number}</h2>
    <p>Hi {name},</p>
    <p>Thank you for your order! Here's your receipt:</p>

    <table class="order-table">
      <thead>
        <tr><th>Item</th><th style="text-align:center;">Qty</th><th style="text-align:right;">Price</th><th style="text-align:right;">Total</th></tr>
      </thead>
      <tbody>
        {rows}
        <tr><td colspan="3" style="text-align:right;">Subtotal</td><td style="text-align:right;">R{subtotal:.2f}</td></tr>
        <tr><td colspan="3" style="text-align:right;">Shipping</td><td style="text-align:right;">R{shipping_cost:.2f}</td></tr>
        <tr class="total-row"><td colspan="3" style="text-align:right;">Total</td><td style="text-align:right;">R{total:.2f}</td></tr>
      </tbody>
    </table>

    <div class="highlight">
      <strong>Shipping to:</strong><br/>{shipping_address}
    </div>

    <p><strong>Order Date:</strong> {order_date}</p>
    <p>We'll send you a tracking number as soon as your order ships.</p>

    <p style="text-align:center;">
      <a href="https://www.elitetcg.co.za/orders" class="btn">View Your Order</a>
    </p>
    """
    return _wrap(f"Order Confirmed — {order_number}", content)


# ── 3. Shipping Notification ──────────────────────────────────────────────────

def shipping_notification_template(
    name: str, order_number: str, tracking_number: str,
    courier: str, tracking_url: str,
) -> str:
    content = f"""
    <h2>Your Order Has Shipped! 📦</h2>
    <p>Hi {name},</p>
    <p>Great news — your order <strong>{order_number}</strong> is on its way!</p>

    <div class="tracking-box">
      <p style="margin:0 0 8px;color:#666;font-size:13px;">TRACKING NUMBER</p>
      <p class="number">{tracking_number}</p>
      <p style="margin:8px 0 0;color:#666;font-size:13px;">via {courier}</p>
    </div>

    <p style="text-align:center;">
      <a href="{tracking_url}" class="btn">Track Your Parcel</a>
    </p>

    <p>You can also track at: <a href="{tracking_url}" style="color:#D4A800;">{tracking_url}</a></p>
    """
    return _wrap(f"Your Order {order_number} Has Shipped!", content)


# ── 4. Delivery Confirmation ─────────────────────────────────────────────────

def delivery_confirmation_template(name: str, order_number: str) -> str:
    content = f"""
    <h2>Your Order Has Arrived! ⚡</h2>
    <p>Hi {name},</p>
    <p>Your order <strong>{order_number}</strong> has been delivered. We hope you love your cards!</p>

    <div class="highlight">
      <p style="margin:0;">If anything doesn't look right, please contact us within 48 hours and we'll sort it out.</p>
    </div>

    <p style="text-align:center;">
      <a href="https://www.elitetcg.co.za/orders" class="btn">View Order Details</a>
    </p>

    <p>Thanks for shopping with Elite TCG!<br/><strong>The Elite TCG Team</strong></p>
    """
    return _wrap(f"Your Order {order_number} Has Arrived!", content)


# ── 5. Payment Failed ─────────────────────────────────────────────────────────

def payment_failed_template(name: str, order_number: str, retry_url: str) -> str:
    content = f"""
    <h2>Payment Issue — {order_number}</h2>
    <p>Hi {name},</p>
    <p>We weren't able to process payment for your order <strong>{order_number}</strong>.</p>

    <div class="highlight">
      <p style="margin:0;">Don't worry — your items are still reserved. Please try again and your order will go through.</p>
    </div>

    <p style="text-align:center;">
      <a href="{retry_url}" class="btn">Retry Payment</a>
    </p>

    <p>If the problem persists, please contact us at <a href="mailto:support@elitetcg.co.za" style="color:#D4A800;">support@elitetcg.co.za</a>.</p>
    """
    return _wrap(f"Payment Issue — {order_number}", content)


# ── 6. Refund Confirmation ────────────────────────────────────────────────────

def refund_confirmation_template(
    name: str, order_number: str, refund_amount: float, refund_method: str,
) -> str:
    content = f"""
    <h2>Refund Processed — {order_number}</h2>
    <p>Hi {name},</p>
    <p>We've processed a refund for your order <strong>{order_number}</strong>.</p>

    <div class="highlight">
      <p style="margin:0;"><strong>Refund Amount:</strong> R{refund_amount:.2f}</p>
      <p style="margin:4px 0 0;"><strong>Method:</strong> {refund_method}</p>
    </div>

    <p>Please allow 3–5 business days for the refund to reflect in your account.</p>
    <p>If you have any questions, email us at <a href="mailto:support@elitetcg.co.za" style="color:#D4A800;">support@elitetcg.co.za</a>.</p>
    """
    return _wrap(f"Refund Processed — {order_number}", content)


# ── 7. Order Cancelled ────────────────────────────────────────────────────────

def order_cancelled_template(name: str, order_number: str, refund_amount: float) -> str:
    refund_text = f"<p>A refund of <strong>R{refund_amount:.2f}</strong> will be processed to your original payment method within 3–5 business days.</p>" if refund_amount > 0 else ""
    content = f"""
    <h2>Order Cancelled — {order_number}</h2>
    <p>Hi {name},</p>
    <p>Your order <strong>{order_number}</strong> has been cancelled.</p>
    {refund_text}
    <p>If this was a mistake or you'd like to place a new order, you can head back to the store:</p>
    <p style="text-align:center;">
      <a href="https://www.elitetcg.co.za/shop" class="btn">Back to Shop</a>
    </p>
    """
    return _wrap(f"Order {order_number} Cancelled", content)


# ── 8. Back in Stock ──────────────────────────────────────────────────────────

def back_in_stock_template(
    name: str, product_name: str, product_price: float, product_url: str,
) -> str:
    content = f"""
    <h2>It's Back! ⚡</h2>
    <p>Hi {name},</p>
    <p>Good news — <strong>{product_name}</strong> is back in stock!</p>

    <div class="highlight">
      <p style="margin:0;font-size:18px;"><strong>{product_name}</strong></p>
      <p style="margin:4px 0 0;font-size:20px;color:#D4A800;font-weight:bold;">R{product_price:.2f}</p>
    </div>

    <p style="text-align:center;">
      <a href="{product_url}" class="btn">Grab It Now</a>
    </p>

    <p style="color:#999;font-size:13px;">Stock is limited — don't miss out!</p>
    """
    return _wrap(f"Back in Stock: {product_name}", content)


# ── 9. Abandoned Cart ─────────────────────────────────────────────────────────

def abandoned_cart_template(name: str, cart_items: list[dict], cart_url: str) -> str:
    rows = ""
    for item in cart_items:
        rows += f"""<tr>
          <td>{item['name']}</td>
          <td style="text-align:center;">{item['quantity']}</td>
          <td style="text-align:right;">R{item['price']:.2f}</td>
        </tr>"""

    content = f"""
    <h2>You Left Something Behind! 👀</h2>
    <p>Hi {name},</p>
    <p>Looks like you left some items in your cart. They're still waiting for you!</p>

    <table class="order-table">
      <thead>
        <tr><th>Item</th><th style="text-align:center;">Qty</th><th style="text-align:right;">Price</th></tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>

    <p style="text-align:center;">
      <a href="{cart_url}" class="btn">Complete Your Order</a>
    </p>

    <p style="color:#999;font-size:13px;">Stock is limited and prices may change. Secure your cards before they're gone!</p>
    """
    return _wrap("You Left Something Behind!", content)


# ── 10. New Drop Alert ────────────────────────────────────────────────────────

def new_drop_alert_template(
    name: str, set_name: str, set_description: str, drop_url: str,
) -> str:
    content = f"""
    <h2>New Drop: {set_name} ⚡</h2>
    <p>Hi {name},</p>
    <p>A new set just landed at Elite TCG!</p>

    <div class="highlight">
      <p style="margin:0;font-size:18px;"><strong>{set_name}</strong></p>
      <p style="margin:8px 0 0;">{set_description}</p>
    </div>

    <p style="text-align:center;">
      <a href="{drop_url}" class="btn">Shop the Drop</a>
    </p>

    <p style="color:#999;font-size:13px;">Be quick — popular products sell out fast!</p>
    """
    return _wrap(f"New Drop: {set_name}", content)


# ── Existing seller/marketplace templates (kept for backward compat) ──────────

SELLER_SALE_NOTIFICATION_TEMPLATE = """
<html>
<body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:600px;margin:0 auto;">
<div style="background:#1a1a1a;padding:20px;text-align:center;">
  <h1 style="margin:0;"><span style="color:#FFD700;">ELITE</span> <span style="color:#fff;">TCG</span></h1>
</div>
<div style="padding:24px;">
<h2>You Have a New Sale!</h2>
<p>Hi {seller_name},</p>
<p>Great news! Someone purchased your listing:</p>
<p><strong>{listing_title}</strong> x {quantity}</p>
<p>Your earnings: <strong>R{seller_amount:.2f}</strong></p>
<p>Order: {order_number}</p>
<p>Please prepare the item for shipping.</p>
</div>
<div style="background:#1a1a1a;padding:16px;text-align:center;color:#999;font-size:12px;">
  <p>&copy; Elite TCG</p>
</div>
</body>
</html>
"""

SELLER_PAYOUT_NOTIFICATION_TEMPLATE = """
<html>
<body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:600px;margin:0 auto;">
<div style="background:#1a1a1a;padding:20px;text-align:center;">
  <h1 style="margin:0;"><span style="color:#FFD700;">ELITE</span> <span style="color:#fff;">TCG</span></h1>
</div>
<div style="padding:24px;">
<h2>Payout Created</h2>
<p>Hi {seller_name},</p>
<p>A payout of <strong>R{payout_amount:.2f}</strong> has been created for order {order_number}.</p>
</div>
<div style="background:#1a1a1a;padding:16px;text-align:center;color:#999;font-size:12px;">
  <p>&copy; Elite TCG</p>
</div>
</body>
</html>
"""

DELIVERY_CONFIRMED_SELLER_TEMPLATE = """
<html>
<body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:600px;margin:0 auto;">
<div style="background:#1a1a1a;padding:20px;text-align:center;">
  <h1 style="margin:0;"><span style="color:#FFD700;">ELITE</span> <span style="color:#fff;">TCG</span></h1>
</div>
<div style="padding:24px;">
<h2>Delivery Confirmed</h2>
<p>Hi {seller_name},</p>
<p>The buyer has confirmed delivery for order <strong>{order_number}</strong>.</p>
</div>
<div style="background:#1a1a1a;padding:16px;text-align:center;color:#999;font-size:12px;">
  <p>&copy; Elite TCG</p>
</div>
</body>
</html>
"""

PROMOTION_CONFIRMATION_TEMPLATE = """
<html>
<body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:600px;margin:0 auto;">
<div style="background:#1a1a1a;padding:20px;text-align:center;">
  <h1 style="margin:0;"><span style="color:#FFD700;">ELITE</span> <span style="color:#fff;">TCG</span></h1>
</div>
<div style="padding:24px;">
<h2>Promotion Activated!</h2>
<p>Hi {seller_name},</p>
<p>Your listing <strong>{listing_title}</strong> is now promoted with the <strong>{tier}</strong> tier.</p>
<p>Promotion expires: {expires_at}</p>
</div>
<div style="background:#1a1a1a;padding:16px;text-align:center;color:#999;font-size:12px;">
  <p>&copy; Elite TCG</p>
</div>
</body>
</html>
"""

# Legacy aliases for backward compatibility with existing service imports
ORDER_CONFIRMATION_TEMPLATE = None  # No longer used — see order_confirmation_template()
SHIPPING_NOTIFICATION_TEMPLATE = None  # No longer used — see shipping_notification_template()
