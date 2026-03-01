# payments/services/phonepe.py

import uuid
from payments.models import Payment
from django.conf import settings


class PhonePePaymentService:

    def initiate_payment(self, order):

        # Generate unique transaction id
        merchant_txn_id = f"TXN-{uuid.uuid4().hex[:10]}"

        # Create payment record as PENDING
        Payment.objects.create(
            user=order.user,
            order=order,
            payment_id=merchant_txn_id,
            payment_method="PHONEPE",
            amount=order.total_amount,
            status="PENDING",
        )

        # Normally here you call PhonePe API
        # For now, simulate redirect URL

        return {
            "payment_status": "PENDING",
            "redirect_url": f"https://api.phonepe.com/pay/{merchant_txn_id}"
        }