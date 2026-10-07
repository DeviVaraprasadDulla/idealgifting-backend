from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_order_email(user_email, order):

    customer_name = (
        order.user.first_name
        if order.user and order.user.first_name
        else "Customer"
    )

    subject = f"Order Confirmed - {order.order_number}"

    context = {
        "order": order,
        "customer_name": customer_name,
        "items": order.items.all(),
        "address": order.address,
    }

    html_content = render_to_string(
        "emails/order_confirmed.html",
        context
    )

    text_content = f"""
Hi {customer_name},

Your order {order.order_number} has been confirmed.

Total Amount: ₹{order.total_amount}
Payment Status: {order.payment_status}
Order Status: {order.order_status}

Thank you for shopping with IdealGifting.

IdealGifting Team
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )

    email.attach_alternative(
        html_content,
        "text/html"
    )

    email.send(
        fail_silently=False
    )


def send_cancel_email(user_email, order):

    customer_name = (
        order.user.first_name
        if order.user and order.user.first_name
        else "Customer"
    )

    subject = f"Order Cancelled - {order.order_number}"

    context = {
        "order": order,
        "customer_name": customer_name,
        "address": order.address,
    }

    html_content = render_to_string(
        "emails/order_cancelled.html",
        context
    )

    text_content = f"""
Hi {customer_name},

Your order {order.order_number} has been cancelled.

Refund Amount: ₹{order.total_amount}
Refund Status: {order.payment_status}

Your refund will reflect in your original payment method
within 3-5 business days.

Thank you,
IdealGifting Team
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )

    email.attach_alternative(
        html_content,
        "text/html"
    )

    email.send(
        fail_silently=False
    )


def merge_guest_orders_to_user(old_session_key, user):
    # Guest orders are not supported
    return