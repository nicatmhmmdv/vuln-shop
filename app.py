from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
from dotenv import load_dotenv

# .env faylını yükləyirik
load_dotenv()

app = Flask(__name__)


app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cox-gizli-bir-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///techmart.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Zəhmət olmasa daxil olun."
login_manager.login_message_category = "warning"


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    orders = db.relationship("Order", backref="owner", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.String(50), nullable=False)
    stripe_session_id = db.Column(db.String(200), unique=True, nullable=True)
    status = db.Column(db.String(20), default="pending")

    # BU HİSSƏNİ ƏLAVƏ ET:
    @property
    def product(self):
        # Bu metod HTML-də {{ order.product.name }} yazmağı mümkün edir
        return PRODUCTS.get(self.product_id, {
            "name": "Məhsul tapılmadı",
            "emoji": "❓",
            "display": 0
        })

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

PRODUCTS = {
    "iphone_15": {"name": "iPhone 15 Pro",  "price": 100000, "emoji": "📱", "label": "Smartfon", "display": 1000},
    "macbook":   {"name": "MacBook Air M3", "price": 250000, "emoji": "💻", "label": "Noutbuk",  "display": 2500},
    "airpods":   {"name": "AirPods Pro 2",  "price":  35000, "emoji": "🎧", "label": "Audio",    "display": 350},
}

@app.route("/")
def index():
    return render_template("index.html", products=PRODUCTS)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if User.query.filter_by(username=username).first():
            flash("Bu istifadəçi artıq mövcuddur.", "danger")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Səhv istifadəçi adı və ya şifrə.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    product_id = request.form.get("product_id")
    product = PRODUCTS.get(product_id)
    
    if not product:
        abort(400)

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "azn",
                "product_data": {"name": product["name"]},
                "unit_amount": product["price"], # Serverdəki qiymət!
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.host_url + "success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.host_url,
    )

    new_order = Order(
        user_id=current_user.id,
        product_id=product_id,
        stripe_session_id=checkout_session.id,
        status="pending"
    )
    db.session.add(new_order)
    db.session.commit()

    return redirect(checkout_session.url, code=303)
    
@app.route("/success")
@login_required
def success():
    # 1. URL-dən gələn ID-ni götürürük (Məsələn, AirPods-un ID-si)
    session_id = request.args.get("session_id")
    if not session_id:
        return redirect(url_for("index"))

    try:
        # 2. Stripe-dan soruşuruq: "Bu ID ilə hər hansı ödəniş edilibmi?"
        # Diqqət: Stripe "Bəli, edilib" deyəcək, çünki AirPods-un pulunu ödəmisən.
        stripe_session = stripe.checkout.Session.retrieve(session_id)
        
        # 3. ⚠️ KRİTİK ZƏİFLİK (Session Replay):
        # Biz bazada 'stripe_session_id=session_id' filtrini işlətmirik!
        # Bunun əvəzinə istifadəçinin hələ ödənilməmiş (pending) EN SON sifarişini tapırıq.
        order = Order.query.filter_by(
            user_id=current_user.id, 
            status="pending"
        ).order_by(Order.id.desc()).first()

        # 4. Əgər hakerdirsə:
        # 'stripe_session.payment_status' -> "paid" (AirPods-a görə)
        # 'order' -> MacBook (Çünki ən son yaradılan pending odur)
        if order and stripe_session.payment_status == "paid":
            order.status = "paid"
            db.session.commit()
            
            product = PRODUCTS.get(order.product_id)
            return render_template("success.html", order=order, product=product)
        
    except Exception as e:
        print(f"Xəta: {e}")
        
    flash("Sifariş təsdiqlənmədi.", "danger")
    return redirect(url_for("index"))

@app.route("/my-orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id, status="paid").all()
    for order in orders:
        order.product_name = PRODUCTS.get(order.product_id, {}).get("name", "Məhsul")
    return render_template("orders.html", orders=orders)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)