from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_admin_order_mail(order):
    """
    Sends premium HTML order notification email to administrator.
    """
    customer_name = (
        f"{order.user.first_name} {order.user.last_name}".strip()
        if order.user and (order.user.first_name or order.user.last_name)
        else ("Customer" if order.user else "Guest")
    )

    context = {
        "order": order,
        "customer_name": customer_name,
        "items": order.items.all(),
        "address": order.address,
    }

    subject = f"New Order Confirmed - {order.order_number}"

    html_content = render_to_string(
        "emails/admin_new_order.html",
        context
    )

    text_content = f"""New order has been placed.
Order ID: {order.order_number}
Customer: {customer_name}
Email: {order.user.email if order.user else "Guest"}
Amount: ₹{order.total_amount}
Payment Status: {order.payment_status}
Order Status: {order.order_status}

Check admin dashboard for order fulfillment details.
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.ADMIN_EMAIL],
    )

    email.attach_alternative(
        html_content,
        "text/html"
    )

    email.send(
        fail_silently=False
    )
