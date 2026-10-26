"""Interface texts of online payment: customer pages, the test gateway and the admin."""

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA

PAYMENT_TEXTS: dict[str, dict[str, str]] = {
    # Checkout
    "checkout.pay_online": {FA: "پرداخت آنلاین", EN: "Pay online"},
    "checkout.pay_online_hint": {
        FA: "با درگاه پرداخت؛ در این نسخه‌ی نمایشی درگاه آزمایشی است.",
        EN: "Through the payment gateway; a test gateway in this demo.",
    },
    "checkout.error.online_unavailable": {
        FA: "پرداخت آنلاین در حال حاضر در دسترس نیست.",
        EN: "Online payment is not available right now.",
    },
    # Order page
    "order.status.awaiting_payment": {FA: "در انتظار پرداخت", EN: "Waiting for payment"},
    "order.payment_state.paid_online": {FA: "پرداخت آنلاین انجام شد", EN: "Paid online"},
    "order.payment_state.awaiting_online": {
        FA: "پرداخت آنلاین هنوز انجام نشده",
        EN: "Online payment not completed yet",
    },
    "order.payment_state.cash_paid": {FA: "پرداخت در محل (دریافت شد)", EN: "Paid on arrival"},
    "order.payment_state.cash_due": {FA: "پرداخت در محل", EN: "Pay on arrival"},
    "order.payment_state.cancelled": {FA: "سفارش لغو شد", EN: "Order cancelled"},
    "order.pay.kicker": {
        FA: "سفارش شما ثبت شد؛ فقط پرداخت مانده است.",
        EN: "Your order is saved; only the payment is left.",
    },
    "order.pay.title": {FA: "پرداخت شما کامل نشده است", EN: "Your payment is not complete"},
    "order.pay.hint": {
        FA: (
            "سفارش تا پرداخت موفق وارد آشپزخانه نمی‌شود. "
            "می‌توانید دوباره پرداخت کنید یا پرداخت را به زمان تحویل بسپارید."
        ),
        EN: (
            "The kitchen only sees the order after a successful payment. "
            "Try again, or pay when you receive it."
        ),
    },
    "order.pay.retry": {FA: "پرداخت آنلاین دوباره", EN: "Pay online again"},
    "order.pay.switch_to_cash": {FA: "پرداخت در محل", EN: "Pay on arrival instead"},
    # Messages after paying
    "pay.flash.paid": {
        FA: "پرداخت با موفقیت انجام شد. سفارش شما ثبت شد.",
        EN: "Payment received. Your order is placed.",
    },
    "pay.flash.failed": {
        FA: "پرداخت ناموفق بود. می‌توانید دوباره تلاش کنید.",
        EN: "The payment failed. You can try again.",
    },
    "pay.flash.cancelled": {
        FA: "پرداخت لغو شد. می‌توانید دوباره تلاش کنید.",
        EN: "The payment was cancelled. You can try again.",
    },
    "pay.flash.unavailable": {
        FA: "درگاه پرداخت در دسترس نیست. کمی بعد دوباره تلاش کنید یا در محل پرداخت کنید.",
        EN: "The payment gateway is not available. Try again shortly, or pay on arrival.",
    },
    "pay.flash.unknown": {FA: "این پرداخت پیدا نشد.", EN: "That payment could not be found."},
    "pay.flash.not_payable": {
        FA: "این سفارش در حال حاضر قابل پرداخت نیست.",
        EN: "This order cannot be paid right now.",
    },
    "pay.flash.switched_to_cash": {
        FA: "پرداخت در محل ثبت شد و سفارش شما به آشپزخانه رسید.",
        EN: "You will pay on arrival, and your order has gone to the kitchen.",
    },
    # The test gateway page
    "pay.mock.badge": {FA: "آزمایشی", EN: "Test"},
    "pay.mock.title": {FA: "درگاه پرداخت آزمایشی", EN: "Test payment gateway"},
    "pay.mock.notice": {
        FA: "این یک درگاه آزمایشی است. هیچ مبلغی کسر نمی‌شود و نیازی به کارت نیست.",
        EN: "This is a test gateway. No money is charged and no card is needed.",
    },
    "pay.mock.shop": {FA: "پذیرنده", EN: "Merchant"},
    "pay.mock.order": {FA: "شماره‌ی سفارش", EN: "Order number"},
    "pay.mock.amount": {FA: "مبلغ", EN: "Amount"},
    "pay.mock.reference": {FA: "کد پیگیری درگاه", EN: "Gateway reference"},
    "pay.mock.success": {FA: "پرداخت موفق", EN: "Successful payment"},
    "pay.mock.failure": {FA: "پرداخت ناموفق", EN: "Failed payment"},
    "pay.mock.cancel": {FA: "انصراف و بازگشت", EN: "Cancel and go back"},
    "pay.mock.footnote": {
        FA: "با هر دکمه به فروشگاه برمی‌گردید و فروشگاه نتیجه را از درگاه می‌پرسد.",
        EN: "Each button returns you to the shop, which then asks the gateway what happened.",
    },
    # Admin: payments on an order
    "admin.orders.payments": {FA: "پرداخت‌ها", EN: "Payments"},
    "admin.orders.payments_empty": {FA: "پرداختی ثبت نشده است.", EN: "No payment recorded."},
    "admin.orders.payment_status.pending": {FA: "در انتظار", EN: "Pending"},
    "admin.orders.payment_status.paid": {FA: "پرداخت‌شده", EN: "Paid"},
    "admin.orders.payment_status.failed": {FA: "ناموفق", EN: "Failed"},
    "admin.orders.payment_status.cancelled": {FA: "لغو شده", EN: "Cancelled"},
    "admin.orders.test_badge": {FA: "آزمایشی", EN: "Test"},
    "admin.orders.transaction": {FA: "شناسه‌ی تراکنش", EN: "Transaction"},
    "admin.orders.paid_at": {FA: "زمان پرداخت", EN: "Paid at"},
    "admin.orders.mark_paid": {FA: "دریافت وجه شد", EN: "Mark cash received"},
    "admin.orders.mark_paid_confirm": {
        FA: "دریافت وجه این سفارش ثبت شود؟",
        EN: "Record that the money for this order was received?",
    },
    "admin.orders.marked_paid": {FA: "دریافت وجه ثبت شد.", EN: "Cash received recorded."},
    "admin.orders.error.not_cash": {
        FA: "برای این سفارش دریافت وجه در محل قابل ثبت نیست.",
        EN: "A cash payment cannot be recorded for this order.",
    },
    "admin.orders.pay_chip.paid": {FA: "پرداخت‌شده", EN: "Paid"},
    "admin.orders.pay_chip.cash_due": {FA: "وجه در محل", EN: "Cash due"},
    "admin.orders.pay_chip.online_waiting": {
        FA: "منتظر پرداخت آنلاین",
        EN: "Awaiting online payment",
    },
}
