from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# ==============================
# API KEY
# ==============================

API_KEY = "MC_POS_APIKEY_2026"

def check_api():
    return request.headers.get("x-api-key") == API_KEY

# ==============================
# MEMORY STORAGE (MULTI-TENANT)
# ==============================

inventory_data = {}
sales_data = {}

# ==============================
# HOME
# ==============================

@app.route("/")
def home():
    return "API RUNNING"

# ==============================
# INVENTORY SYNC
# ==============================

@app.route("/sync_inventory", methods=["POST"])
def sync_inventory():

    if not check_api():
        return {"error": "unauthorized"}, 401

    req = request.json or {}

    tenant = req.get("tenant")
    data = req.get("data")

    if not tenant:
        return {"error": "no tenant"}, 400

    inventory_data[tenant] = data

    print("INVENTORY SAVED FOR:", tenant[:10])

    return jsonify({"status": "saved"})

# ==============================
# GET INVENTORY
# ==============================

@app.route("/get_inventory", methods=["GET"])
def get_inventory():
    tenant = request.args.get("tenant")

    if not tenant:
        return jsonify({})

    return jsonify(inventory_data.get(tenant, {}))

# ==============================
# INVENTORY SUMMARY
# ==============================

@app.route("/get_summary", methods=["GET"])
def get_summary():
    tenant = request.args.get("tenant")

    if not tenant:
        return jsonify([])

    data = inventory_data.get(tenant, {})

    summary = {}

    for item in data.get("batch", []):
        name = f"{item.get('model','')} {item.get('variant','')} {item.get('parts','')}".strip()
        summary.setdefault(name, {"qty": 0, "price": item.get("srp", 0)})
        summary[name]["qty"] += 1

    for item in data.get("nonserial", []):
        name = f"{item.get('model','')} {item.get('variant','')} {item.get('parts','')}".strip()
        summary.setdefault(name, {"qty": 0, "price": item.get("srp", 0)})
        summary[name]["qty"] += int(item.get("qty", 0))

    result = [{"name": k, "qty": v["qty"], "price": v["price"]} for k, v in summary.items()]
    result.sort(key=lambda x: x["qty"], reverse=True)

    return jsonify(result)

# ==============================
# SALES SYNC
# ==============================

@app.route("/sync_sales", methods=["POST"])
def sync_sales():

    if not check_api():
        return {"error": "unauthorized"}, 401

    req = request.json or {}

    tenant = req.get("tenant")
    data = req.get("data")

    if not tenant:
        return {"error": "no tenant"}, 400

    sales_data[tenant] = data

    print("SALES SAVED FOR:", tenant[:10])

    return jsonify({"status": "saved"})

# ==============================
# GET SALES
# ==============================

@app.route("/get_sales", methods=["GET"])
def get_sales():
    tenant = request.args.get("tenant")

    if not tenant:
        return jsonify({"transactions": [], "items": []})

    return jsonify(sales_data.get(tenant, {"transactions": [], "items": []}))

# ==============================
# SALES SUMMARY
# ==============================

@app.route("/get_sales_summary", methods=["GET"])
def get_sales_summary():
    tenant = request.args.get("tenant")

    data = sales_data.get(tenant, {"items": []})
    items = data.get("items", [])

    total_sales = 0
    total_profit = 0
    summary = {}

    for item in items:
        name = item.get("name") or f"{item.get('model','')} {item.get('variant','')} {item.get('parts','')}"
        name = name.upper().strip()

        qty = int(item.get("qty", 1))
        price = float(item.get("price", 0))
        subtotal = float(item.get("subtotal", price * qty))
        profit = float(item.get("profit", 0))

        total_sales += subtotal
        total_profit += profit

        summary.setdefault(name, {"qty": 0, "sales": 0})
        summary[name]["qty"] += qty
        summary[name]["sales"] += subtotal

    top_items = [{"name": k, "qty": v["qty"], "sales": v["sales"]} for k, v in summary.items()]
    top_items.sort(key=lambda x: x["sales"], reverse=True)

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "top_items": top_items[:10]
    }

# ==============================
# SALES TABLE
# ==============================

@app.route("/get_sales_table", methods=["GET"])
def get_sales_table():
    tenant = request.args.get("tenant")

    data = sales_data.get(tenant, {"transactions": []})
    transactions = data.get("transactions", [])

    result = []

    for t in transactions:
        result.append({
            "transaction_id": t.get("transaction_id"),
            "customer": t.get("customer_name"),
            "type": t.get("transaction_type"),
            "cashier": t.get("cashier_name"),
            "datetime": t.get("datetime"),
            "subtotal": t.get("subtotal"),
            "discount": t.get("discount"),
            "tax": t.get("tax"),
            "total": t.get("total_amount"),
            "status": t.get("status"),
            "payment_mode": t.get("payment_mode")
        })

    result.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    return result

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
