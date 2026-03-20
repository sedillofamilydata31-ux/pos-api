from flask import Flask, request, jsonify
import os
import json

app = Flask(__name__)

# ==============================
# LOAD EXISTING DATA (PERSIST)
# ==============================

inventory_data = {}
sales_data = {"transactions": [], "items": []}

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
    inventory_data = request.json

    with open("inventory.json", "w") as f:
        json.dump(inventory_data, f)

    print("FULL INVENTORY RECEIVED")
    return jsonify({"status": "saved"})


# ==============================
# GET INVENTORY
# ==============================

@app.route("/get_inventory", methods=["GET"])
def get_inventory():
    return jsonify(inventory_data)


# ==============================
# INVENTORY SUMMARY
# ==============================

@app.route("/get_sales_summary", methods=["GET"])
def get_sales_summary():
    try:
        with open("sales.json") as f:
            data = json.load(f)
    except:
        return {"total_sales": 0, "total_profit": 0, "top_items": []}

    transactions = data.get("transactions", [])

    total_sales = 0
    total_profit = 0
    summary = {}

    for trx in transactions:

        # total per transaction
        try:
            total_sales += float(trx.get("total_amount") or 0)
        except:
            pass

        # 🔥 loop items inside each transaction
        for item in trx.get("items", []):

            # 🔥 HANDLE BOTH SERIAL + NON-SERIAL
            name = item.get("name")

            if not name:
                model = item.get("model", "")
                variant = item.get("variant", "")
                parts = item.get("parts", "")
                name = f"{model} {variant} {parts}".strip()

            # qty
            try:
                qty = int(item.get("qty") or 1)
            except:
                qty = 1

            # sales
            try:
                subtotal = float(item.get("subtotal") or 0)
            except:
                subtotal = 0

            # profit
            try:
                profit = float(item.get("profit") or 0)
            except:
                profit = 0

            total_profit += profit

            if name not in summary:
                summary[name] = {"qty": 0, "sales": 0}

            summary[name]["qty"] += qty
            summary[name]["sales"] += subtotal

    # convert to list
    top_items = []
    for name, v in summary.items():
        top_items.append({
            "name": name,
            "qty": v["qty"],
            "sales": v["sales"]
        })

    # sort top selling
    top_items.sort(key=lambda x: x["qty"], reverse=True)

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "top_items": top_items[:10]
    }


# ==============================
# SALES SYNC
# ==============================

@app.route("/sync_sales", methods=["POST"])
def sync_sales():
    global sales_data
    sales_data = request.json

    with open("sales.json", "w") as f:
        json.dump(sales_data, f)

    print("SALES RECEIVED")
    return jsonify({"status": "saved"})


# ==============================
# GET SALES
# ==============================

@app.route("/get_sales", methods=["GET"])
def get_sales():
    return jsonify(sales_data)


#===============================
# GET SALES SUMMARY
#===============================

@app.route("/get_sales_summary", methods=["GET"])
def get_sales_summary():
    try:
        with open("sales.json") as f:
            data = json.load(f)
    except:
        return {"total_sales": 0, "total_profit": 0, "top_items": []}

    items = data.get("items", [])

    total_sales = 0
    total_profit = 0
    summary = {}

    for item in items:
        name = f"{item.get('model', 'N/A')} {item.get('variant', '')}"

        try:
            subtotal = float(item.get("subtotal") or 0)
        except:
            subtotal = 0

        try:
            profit = float(item.get("profit") or 0)
        except:
            profit = 0

        try:
            qty = int(item.get("qty") or 1)
        except:
            qty = 1

        total_sales += subtotal
        total_profit += profit

        if name not in summary:
            summary[name] = {"qty": 0, "sales": 0}

        summary[name]["qty"] += qty
        summary[name]["sales"] += subtotal

    top_items = []
    for name, v in summary.items():
        top_items.append({
            "name": name,
            "qty": v["qty"],
            "sales": v["sales"]
        })

    top_items.sort(key=lambda x: x["qty"], reverse=True)

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
    try:
        with open("sales.json") as f:
            data = json.load(f)
    except:
        return []

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

    # optional sort (latest first)
    result.sort(key=lambda x: x["datetime"], reverse=True)

    return result

# ==============================
# RUN SERVER
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))