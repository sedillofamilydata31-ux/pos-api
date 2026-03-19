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


# ==============================
# RUN SERVER
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))