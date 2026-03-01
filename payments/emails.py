from django.core.mail import send_mail
from django.conf import settings


def send_customer_order_mail(order):
    subject = f"Order Confirmed – Order #{order.id}"
    message = f"""
Hi {order.user.first_name if order.user else "Customer"},

✅ Your payment was successful!

Order ID: {order.id}
Amount Paid: ₹{order.total_amount}
Status: Confirmed

Thank you for shopping with us 🙏

– Team {settings.EMAIL_HOST_USER}
"""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=False,
    )


def send_admin_order_mail(order):
    subject = f"🔥 New Order Confirmed – #{order.id}"
    message = f"""
New order has been placed.

Order ID: {order.id}
User: {order.user.email if order.user else "Guest"}
Amount: ₹{order.total_amount}
Payment Status: PAID
Order Status: CONFIRMED
"""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        fail_silently=False,
    )
