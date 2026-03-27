from flask import Flask, request, jsonify
from flask_cors import CORS   # ADD THIS
import os
import json

app = Flask(__name__)
CORS(app)  # ADD THIS

# ==============================
# LOAD EXISTING DATA (PERSIST)
# ==============================

inventory_data = {}
sales_data = {}

if os.path.exists("inventory.json"):
    with open("inventory.json") as f:
        inventory_data = json.load(f)

if os.path.exists("sales.json"):
    with open("sales.json") as f:
        sales_data = json.load(f)


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
    global inventory_data

    tenant = request.json.get("tenant")
    data = request.json.get("data")

    if not tenant:
        return {"error": "no tenant"}, 400

    inventory_data[tenant] = data

    with open("inventory.json", "w") as f:
        json.dump(inventory_data, f)

    print(f"FULL INVENTORY RECEIVED: {tenant}")

    return jsonify({"status": "saved"})


# ==============================
# GET INVENTORY
# ==============================

@app.route("/get_inventory", methods=["GET"])
def get_inventory():
    tenant = request.args.get("tenant")

    if not tenant:
        return {}

    return jsonify(inventory_data.get(tenant, {}))


# ==============================
# INVENTORY SUMMARY
# ==============================

@app.route("/get_summary", methods=["GET"])
def get_summary():
    tenant = request.args.get("tenant")
    data = inventory_data.get(tenant, {})

    summary = {}

    for item in data.get("batch", []):
        name = f"{item['model']} {item['variant']} {item['parts']}"

        if name not in summary:
            summary[name] = {"qty": 0, "price": item["srp"]}

        summary[name]["qty"] += 1

    for item in data.get("nonserial", []):
        name = f"{item['model']} {item['variant']} {item['parts']}"

        if name not in summary:
            summary[name] = {"qty": 0, "price": item["srp"]}

        summary[name]["qty"] += int(item["qty"])

    result = []
    for name, v in summary.items():
        result.append({
            "name": name,
            "qty": v["qty"],
            "price": v["price"]
        })

    result.sort(key=lambda x: x["qty"], reverse=True)

    return jsonify(result)


# ==============================
# SALES SYNC
# ==============================
@app.route("/sync_sales", methods=["POST"])
def sync_sales():
    global sales_data

    tenant = request.json.get("tenant")
    data = request.json.get("data")

    if not tenant:
        return {"error": "no tenant"}, 400

    sales_data[tenant] = data

    with open("sales.json", "w") as f:
        json.dump(sales_data, f)

    print(f"SALES RECEIVED: {tenant}")

    return jsonify({"status": "saved"})


# ==============================
# GET SALES
# ==============================
@app.route("/get_sales", methods=["GET"])
def get_sales():
    tenant = request.args.get("tenant")

    if not tenant:
        return {}

    return jsonify(sales_data.get(tenant, {}))


#===============================
# GET SALES SUMMARY
#===============================
@app.route("/get_sales_summary", methods=["GET"])
def get_sales_summary():
    tenant = request.args.get("tenant")
    data = sales_data.get(tenant, {})

    items = data.get("items", [])

    total_sales = 0
    total_profit = 0
    summary = {}

    for item in items:
        name = item.get("name") or f"{item.get('model','')} {item.get('variant','')} {item.get('parts','')}"
        name = name.upper().strip()

        try:
            qty = int(item.get("qty", 1))
        except:
            qty = 1

        try:
            price = float(item.get("price", 0))
        except:
            price = 0

        try:
            subtotal = float(item.get("subtotal", price * qty))
        except:
            subtotal = price * qty

        try:
            profit = float(item.get("profit", 0))
        except:
            profit = 0

        total_sales += subtotal
        total_profit += profit

        if name not in summary:
            summary[name] = {"qty": 0, "sales": 0}

        summary[name]["qty"] += qty
        summary[name]["sales"] += subtotal

    top_items = [
        {"name": k, "qty": v["qty"], "sales": v["sales"]}
        for k, v in summary.items()
    ]

    top_items.sort(key=lambda x: x["sales"], reverse=True)

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "top_items": top_items[:10]
    }

#===============================
# GET TABLE SUMMARY
#===============================
@app.route("/get_sales_table", methods=["GET"])
def get_sales_table():
    tenant = request.args.get("tenant")
    data = sales_data.get(tenant, {})

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

    result.sort(key=lambda x: x["datetime"], reverse=True)

    return result

# ==============================
# JOB ORDER SYSTEM
# ==============================
job_orders = {}
latest_job_order = {}

@app.route("/create_job_order", methods=["POST"])
def create_job_order():
    tenant = request.json.get("tenant")
    data = request.json.get("data")

    if tenant not in job_orders:
        job_orders[tenant] = []

    data["status"] = "done"

    job_orders[tenant].append(data)
    latest_job_order[tenant] = data

    return jsonify({"status": "saved"})


@app.route("/get_job_order", methods=["GET"])
def get_job_order():
    tenant = request.args.get("tenant")

    data = latest_job_order.get(tenant, {"status": "none"})
    latest_job_order[tenant] = {"status": "none"}

    return jsonify(data)


# ==============================
# RUN SERVER
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
