from django.core.mail import send_mail
from django.conf import settings

def send_order_email(user_email, order):
    subject = f"Order Confirmed - {order.order_number}"

    message = f"""
Hi,

Your order {order.order_number} has been placed successfully.

Total Amount: ₹{order.total_amount}
Status: {order.order_status}

Thank you for shopping with IdealGifting.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )


def send_cancel_email(user_email, order):
    subject = f"Order Cancelled - {order.order_number}"

    message = f"""
Hi,

Your order {order.order_number} has been cancelled.

Refund Amount: ₹{order.total_amount}
Refund Status: REFUNDED

Refund will reflect in 3-5 business days.

Thanks,
IdealGifting Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )
def merge_guest_orders_to_user(old_session_key, user):
    # Guest orders are not supported
    return
