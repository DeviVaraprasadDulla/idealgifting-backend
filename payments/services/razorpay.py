import razorpay

from django.conf import settings


class RazorpayService:

    @staticmethod
    def get_client():

        return razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

    @staticmethod
    def create_order(order):

        client = RazorpayService.get_client()

        razorpay_order = client.order.create(
            {
                "amount": int(order.total_amount * 100),
                "currency": "INR",
                "payment_capture": 1
            }
        )

        return razorpay_order

    @staticmethod
    def verify_signature(data):

        client = RazorpayService.get_client()

        client.utility.verify_payment_signature(data)

        return True