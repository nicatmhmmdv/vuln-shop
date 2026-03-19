# 🛒 TechMart v2 — Təhlükəsiz Flask E-Ticarət

Flask-SQLAlchemy + Flask-Login + Stripe ilə tam funksional, təhlükəsiz e-ticarət tətbiqi.

---

## 🚀 Quraşdırma

```bash
pip install -r requirements.txt
cp .env.example .env        # Stripe və SECRET_KEY əlavə edin
python app.py               # http://localhost:5000
```

---

## 📁 Fayl Strukturu

```
ecommerce_v2/
├── app.py
├── requirements.txt
├── .env.example
└── templates/
    ├── base.html       ← Shared layout + nav (login-aware)
    ├── index.html      ← Məhsul kartları
    ├── login.html      ← Giriş formu
    ├── register.html   ← Qeydiyyat formu
    ├── success.html    ← Stripe-doğrulanmış uğur səhifəsi
    └── orders.html     ← İstifadəçinin ödənilmiş sifarişləri
```

---

## 🗄️ Verilənlər Bazası Modelləri

### User
| Sütun         | Tip          | Qeyd                     |
|---------------|--------------|--------------------------|
| id            | Integer PK   |                          |
| username      | String(80)   | unique                   |
| password_hash | String(256)  | werkzeug PBKDF2 hash     |

### Order
| Sütun             | Tip          | Qeyd                       |
|-------------------|--------------|----------------------------|
| id                | Integer PK   |                            |
| user_id           | FK → User    |                            |
| product_id        | String(50)   | "iphone_15", "macbook" ... |
| stripe_session_id | String(200)  | unique                     |
| status            | String(20)   | "pending" → "paid"         |

---

## 🔐 Təhlükəsizlik Müqayisəsi

| Məsələ                     | v1 (Zəif)                        | v2 (Təhlükəsiz)                        |
|----------------------------|----------------------------------|----------------------------------------|
| Qiymət mənbəyi             | `request.form["price"]`          | `PRODUCTS[product_id]["price"]`        |
| `/success` qorunması       | Yox — URL yazaraq açılır         | `session_id` + Stripe API doğrulaması  |
| İstifadəçi sistemi         | Yox                              | Flask-Login, hashed password           |
| Sifariş izlənməsi          | Yox                              | SQLite → Order modeli                  |
| Auth qoruması              | Yox                              | `@login_required` decorator            |

---

## 🔑 Axın Diaqramı

```
[İstifadəçi] → /register → login_user()
                    ↓
[İstifadəçi] → POST /create-checkout-session
                    │  product_id → PRODUCTS[id]["price"]  ← SERVER QİYMƏTİ
                    │  Order(status="pending") → DB
                    ↓
             [Stripe Checkout]
                    ↓
[İstifadəçi] → /success?session_id=cs_xxx
                    │  stripe.checkout.Session.retrieve(session_id)
                    │  payment_status == "paid" → order.status = "paid"
                    ↓
[İstifadəçi] → /my-orders → yalnız "paid" sifarişlər
```

---

## 🧪 Test Kartı (Stripe)

| Sahə    | Dəyər                |
|---------|----------------------|
| Kart №  | `4242 4242 4242 4242` |
| Tarix   | İstənilən gələcək    |
| CVC     | İstənilən 3 rəqəm    |
