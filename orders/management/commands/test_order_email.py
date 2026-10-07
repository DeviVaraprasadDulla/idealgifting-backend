from django.core.management.base import BaseCommand
from django.conf import settings
from orders.models import Order
from orders.utils import send_order_email
from payments.emails import send_admin_order_mail
import traceback


class Command(BaseCommand):
    help = "Test customer and admin HTML order confirmation emails"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="Recipient email address for customer test mail",
        )
        parser.add_argument(
            "--order-id",
            type=int,
            help="Order ID to use (defaults to latest order)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=== IdealGifting Email Diagnostics ==="))
        self.stdout.write(f"EMAIL_BACKEND:      {getattr(settings, 'EMAIL_BACKEND', 'Not set')}")
        self.stdout.write(f"EMAIL_HOST:         {getattr(settings, 'EMAIL_HOST', 'Not set')}")
        self.stdout.write(f"EMAIL_PORT:         {getattr(settings, 'EMAIL_PORT', 'Not set')}")
        self.stdout.write(f"EMAIL_USE_TLS:      {getattr(settings, 'EMAIL_USE_TLS', False)}")
        self.stdout.write(f"EMAIL_HOST_USER:    {getattr(settings, 'EMAIL_HOST_USER', 'Not set')}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}")
        self.stdout.write(f"ADMIN_EMAIL:        {getattr(settings, 'ADMIN_EMAIL', 'Not set')}")
        self.stdout.write("=========================================\n")

        order_id = options.get("order_id")
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Order #{order_id} does not exist."))
                return
        else:
            order = Order.objects.last()
            if not order:
                self.stderr.write(
                    self.style.ERROR(
                        "No orders found in database. Place at least one order first or create one."
                    )
                )
                return

        recipient = options.get("email") or (
            order.user.email if order.user and order.user.email else getattr(settings, "ADMIN_EMAIL", None)
        )

        if not recipient:
            self.stderr.write(
                self.style.ERROR("No recipient specified. Use --email your_email@example.com")
            )
            return

        self.stdout.write(f"Using Order: #{order.order_number} (ID: {order.id})")
        self.stdout.write(f"Order Total: Rs. {order.total_amount}")
        self.stdout.write(f"Items Count: {order.items.count()}\n")

        # 1. Customer Email
        self.stdout.write(f"[1/2] Sending customer email to: {recipient}...")
        try:
            send_order_email(recipient, order)
            self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Customer email sent successfully to {recipient}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[FAILED] Customer email failed: {e}"))
            traceback.print_exc()

        # 2. Admin Email
        admin_email = getattr(settings, "ADMIN_EMAIL", None)
        self.stdout.write(f"\n[2/2] Sending admin email to: {admin_email}...")
        try:
            send_admin_order_mail(order)
            self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Admin email sent successfully to {admin_email}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[FAILED] Admin email failed: {e}"))
            traceback.print_exc()

        self.stdout.write("\n=== Done ===")
