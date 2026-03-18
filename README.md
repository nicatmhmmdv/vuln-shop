# 🛒 TechMart — Price Manipulation Demo

> **⚠ Bu layihə yalnız təhsil və pentest məqsədləri üçündür.**

---

## 🚀 Quraşdırma

```bash
cd ecommerce
pip install -r requirements.txt
cp .env.example .env          # .env içinə Stripe test açarını əlavə edin
python app.py                  # http://localhost:5000
```

---

## 🎯 Zəiflik: Price Manipulation

### Necə İşləyir?
```
index.html
└── <input type="hidden" name="price" value="1000">
                                          ↑
                               BU DƏYƏRİ BRAUZER DEVTOOLSİ
                               İLƏ DƏYİŞMƏK MÜMKÜNDÜR!
```

### Hücum Addımları (Pentest)
1. `http://localhost:5000` açın
2. **F12** → "Elements" tabına geçin
3. `Ctrl+F` → `name="price"` axtarın
4. `value="1000"` → sağ klik → **Edit as HTML** → `value="1"` yazın
5. "İndi Al" düyməsinə basın
6. Stripe checkout-da **1.00 AZN** görəcəksiniz — ödəyin
7. 1000 AZN-lik iPhone 1 AZN-ə alındı ✅

### Alternativ: `curl` ilə Hücum
```bash
curl -X POST http://localhost:5000/create-checkout-session \
  -d "product_name=iPhone+15+Pro&price=0.01"
```

---

## 🔐 Düzəliş (FIX)

### Zəif Kod (app.py — mövcud)
```python
# ❌ İstifadəçidən gələn qiyməti birbaşa istifadə edir
price_raw = request.form.get("price", "100")
amount_in_qepik = int(float(price_raw) * 100)
```

### Düzgün Kod
```python
# ✅ Qiymət server tərəfindəki bazadan götürülür
PRODUCTS = {
    "iphone_15": {"name": "iPhone 15 Pro", "price": 100000},
    "macbook":   {"name": "MacBook Air M3", "price": 250000},
    "airpods":   {"name": "AirPods Pro 2",  "price":  35000},
}

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    product_id = request.form.get("product_id")      # yalnız ID qəbul et
    product    = PRODUCTS.get(product_id)

    if not product:
        return "Məhsul tapılmadı", 404

    # Qiymət həmişə serverdən götürülür — istifadəçi dəyişə bilməz
    session = stripe.checkout.Session.create(
        line_items=[{
            "price_data": {
                "currency": "azn",
                "product_data": {"name": product["name"]},
                "unit_amount": product["price"],   # ← SERVER QİYMƏTİ
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.host_url + "success",
        cancel_url=request.host_url,
    )
    return redirect(session.url, code=303)
```

---

## 📁 Fayl Strukturu

```
ecommerce/
├── app.py                  # Flask backend (zəiflik burada)
├── requirements.txt
├── .env.example            # Stripe açarı şablonu
└── templates/
    ├── index.html          # Məhsul kartları (hidden input zəifliyi)
    └── success.html        # Uğurlu ödəniş səhifəsi
```

---

## 📚 OWASP Kateqoriyası

| Sahə         | Dəyər                                          |
|--------------|------------------------------------------------|
| **CWE**      | CWE-602: Client-Side Enforcement of Server-Side Security |
| **OWASP**    | A04:2021 – Insecure Design                     |
| **Ciddilik** | Kritik (CVSS 9.1)                              |
| **Səbəb**    | Biznes məntiqinin client-side-da saxlanması    |

---

> Hazırlanıb: Pentest Laboratoriya Məqsədləri üçün
