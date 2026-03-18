from flask import Flask, render_template, request, redirect, url_for
import stripe
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Stripe API açarı .env-dən oxunur
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ─── PRODUCTS (Server-side, lakin yoxlanmır — bu, zəiflikdir!) ───
PRODUCTS = {
    "iphone_15": {"name": "iPhone 15 Pro", "real_price": 100000},   # 1000.00 AZN
    "macbook":   {"name": "MacBook Air M3", "real_price": 250000},  # 2500.00 AZN
    "airpods":   {"name": "AirPods Pro 2",  "real_price":  35000},  #  350.00 AZN
}


@app.route("/")
def index():
    return render_template("index.html")


# ──────────────────────────────────────────────────────────────────
# ⚠️  VULNERABLE ENDPOINT — Price Manipulation
#     Qiymət (price) birbaşa istifadəçidən qəbul edilir,
#     server bazasından heç bir yoxlama aparılmır!
# ──────────────────────────────────────────────────────────────────
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    product_name = request.form.get("product_name", "Məhsul")
    price_raw     = request.form.get("price", "100")       # ← İSTİFADƏÇİDƏN GƏLİR!

    # Məbləği qəpik/sent formatına çeviririk (AZN → qəpik)
    try:
        amount_in_qepik = int(float(price_raw) * 100)
    except ValueError:
        return "Yanlış qiymət formatı", 400

    # ⚠️  Zəiflik: amount_in_qepik server tərəfindən doğrulanmır
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "azn",
                "product_data": {"name": product_name},
                "unit_amount": amount_in_qepik,  # ← MANİPULYASİYA BURADA!
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.host_url + "success",
        cancel_url=request.host_url,
    )

    return redirect(session.url, code=303)


@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
