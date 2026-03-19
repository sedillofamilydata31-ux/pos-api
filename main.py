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

@app.route("/get_summary", methods=["GET"])
def get_summary():
    summary = {}

    # batch items
    for item in inventory_data.get("batch", []):
        name = f"{item['model']} {item['variant']} {item['parts']}"

        if name not in summary:
            summary[name] = {"qty": 0, "price": item["srp"]}

        summary[name]["qty"] += 1

    # non-serial items
    for item in inventory_data.get("nonserial", []):
        name = f"{item['model']} {item['variant']} {item['parts']}"

        if name not in summary:
            summary[name] = {"qty": 0, "price": item["srp"]}

        summary[name]["qty"] += int(item["qty"])

    # convert to list
    result = []
    for name, v in summary.items():
        result.append({
            "name": name,
            "qty": v["qty"],
            "price": v["price"]
        })

    # sort by highest qty
    result.sort(key=lambda x: x["qty"], reverse=True)

    return jsonify(result)


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
        name = f"{item['model']} {item['variant']}"

        total_sales += float(item.get("subtotal", 0))
        total_profit += float(item.get("profit", 0))

        if name not in summary:
            summary[name] = {"qty": 0, "sales": 0}

        summary[name]["qty"] += int(item.get("qty", 1))
        summary[name]["sales"] += float(item.get("subtotal", 0))

    # convert to list
    top_items = []
    for name, v in summary.items():
        top_items.append({
            "name": name,
            "qty": v["qty"],
            "sales": v["sales"]
        })

    # sort top items
    top_items.sort(key=lambda x: x["qty"], reverse=True)

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "top_items": top_items[:10]
    }

# ==============================
# RUN SERVER
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))