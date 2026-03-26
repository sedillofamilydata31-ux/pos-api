from flask import Flask, request, jsonify
from flask_cors import CORS   # ADD THIS
import os
import json
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)  # ADD THIS
API_KEY = os.environ.get("API_KEY")

# ==============================
# LOAD EXISTING DATA (PERSIST)
# ==============================


def init_db():
    conn = sqlite3.connect("cloud.db")
    cursor = conn.cursor()

    # inventory
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            tenant TEXT PRIMARY KEY,
            data TEXT
        )
    """)

    # sales
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            tenant TEXT PRIMARY KEY,
            data TEXT
        )
    """)

    conn.commit()
    conn.close()


# 🔥 CALL THIS ON START
init_db()

def check_api():
    key = request.headers.get("x-api-key")
    
    if key != API_KEY:
        return False
    
    return True

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
    
    # ✅ ADD THIS LINE
    if not check_api():
        return {"error": "unauthorized"}, 401
    

    req = request.get_json(force=True, silent=True) or {}

    tenant = req.get("tenant")
    data = req.get("data")

    if not tenant:
        return {"error": "no tenant"}, 400

    conn = sqlite3.connect("cloud.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO inventory (tenant, data)
        VALUES (?, ?)
    """, (tenant, json.dumps(data)))

    conn.commit()
    conn.close()
    print("INVENTORY SAVED FOR:", tenant[:10])

    return {"status": "saved"}


# ==============================
# GET INVENTORY
# ==============================

@app.route("/get_inventory", methods=["GET"])
def get_inventory():
    tenant = request.args.get("tenant")

    if not tenant:
        return {"error": "no tenant"}, 400

    conn = sqlite3.connect("cloud.db")
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM inventory WHERE tenant=?", (tenant,))
    row = cursor.fetchone()

    conn.close()

    if row:
        return json.loads(row[0])

    return {}


# ==============================
# INVENTORY SUMMARY
# ==============================

@app.route("/get_summary", methods=["GET"])
def get_summary():
    tenant = request.args.get("tenant")

    if not tenant:
        return []

    conn = sqlite3.connect("cloud.db")
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM inventory WHERE tenant=?", (tenant,))
    row = cursor.fetchone()

    conn.close()

    if row:
        data = json.loads(row[0])
    else:
        data = {}

    summary = {}

    # batch items
    for item in data.get("batch", []):
        name = f"{item['model']} {item['variant']} {item['parts']}"

        if name not in summary:
            summary[name] = {"qty": 0, "price": item["srp"]}

        summary[name]["qty"] += 1

    # non-serial items
    for item in data.get("nonserial", []):
        name = f"{item['model']} {item['variant']} {item['parts']}"

        if name not in summary:
            summary[name] = {"qty": 0, "price": item["srp"]}

        summary[name]["qty"] += int(item.get("qty", 0))

    result = [
        {"name": k, "qty": v["qty"], "price": v["price"]}
        for k, v in summary.items()
    ]

    result.sort(key=lambda x: x["qty"], reverse=True)

    return result


# ==============================
# SALES SYNC
# ==============================

@app.route("/sync_sales", methods=["POST"])
def sync_sales():
    
    if not check_api():
        return {"error": "unauthorized"}, 401

    req = request.get_json(force=True, silent=True) or {}

    tenant = req.get("tenant")
    data = req.get("data")

    if not tenant:
        return {"error": "no tenant"}, 400

    conn = sqlite3.connect("cloud.db")
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM sales WHERE tenant=?", (tenant,))
    row = cursor.fetchone()

    if row:
        existing = json.loads(row[0])
    else:
        existing = {"transactions": [], "items": []}

    # merge transactions
    existing_ids = {t.get("transaction_id") for t in existing["transactions"]}

    for trx in data.get("transactions", []):
        if trx.get("transaction_id") not in existing_ids:
            existing["transactions"].append(trx)

    # merge items
    existing_items = {(i.get("name"), i.get("datetime")) for i in existing["items"]}

    for item in data.get("items", []):
        key = (item.get("name"), item.get("datetime"))
        if key not in existing_items:
            existing["items"].append(item)

    # SAVE TO SQLITE
    cursor.execute("""
        INSERT OR REPLACE INTO sales (tenant, data)
        VALUES (?, ?)
    """, (tenant, json.dumps(existing)))

    conn.commit()
    conn.close()

    print("SALES SAVED FOR:", tenant[:10])

    return {"status": "saved"}


# ==============================
# GET SALES
# ==============================

@app.route("/get_sales", methods=["GET"])
def get_sales():
    tenant = request.args.get("tenant")

    if not tenant:
        return {"error": "no tenant"}, 400

    conn = sqlite3.connect("cloud.db")
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM sales WHERE tenant=?", (tenant,))
    row = cursor.fetchone()

    conn.close()

    if row:
        return json.loads(row[0])

    return {"transactions": [], "items": []}


#===============================
# GET SALES SUMMARY
#===============================

@app.route("/get_sales_summary", methods=["GET"])
def get_sales_summary():
    tenant = request.args.get("tenant")

    if not tenant:
        return {"total_sales": 0, "total_profit": 0, "top_items": []}

    conn = sqlite3.connect("cloud.db")
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM sales WHERE tenant=?", (tenant,))
    row = cursor.fetchone()

    conn.close()

    if row:
        data = json.loads(row[0])
    else:
        data = {}
        
    items = data.get("items", [])

    total_sales = 0
    total_profit = 0
    summary = {}

    for item in items:

        name = item.get("name")

        if not name:
            model = item.get("model", "")
            variant = item.get("variant", "")
            parts = item.get("parts", "")
            name = f"{model} {variant} {parts}".strip()

        if not name:
            name = "Unknown"

        name = name.upper().strip()

        try:
            qty = int(item.get("qty", 1))
            if qty <= 0:
                qty = 1
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

    if not tenant:
        return []

    conn = sqlite3.connect("cloud.db")
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM sales WHERE tenant=?", (tenant,))
    row = cursor.fetchone()

    conn.close()

    if row:
        data = json.loads(row[0])
    else:
        data = {}
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

    def parse_date(x):
        try:
            return datetime.fromisoformat(x["datetime"])
        except:
            return datetime.min

    result.sort(key=parse_date, reverse=True)

    return result

JOB_FILE = "job_orders.json"
LATEST_FILE = "latest_job.json"

job_orders = {}
latest_job_order = {}

# ==============================
# LOAD DATA (PERSIST)
# ==============================

if os.path.exists(JOB_FILE):
    with open(JOB_FILE) as f:
        job_orders = json.load(f)

if os.path.exists(LATEST_FILE):
    with open(LATEST_FILE) as f:
        latest_job_order = json.load(f)


def save_job_data():
    with open(JOB_FILE, "w") as f:
        json.dump(job_orders, f)

    with open(LATEST_FILE, "w") as f:
        json.dump(latest_job_order, f)


# ==============================
# CREATE JOB ORDER
# ==============================
@app.route("/create_job_order", methods=["POST"])
def create_job_order():
    
    if not check_api():
        return {"error": "unauthorized"}, 401
    
    global job_orders, latest_job_order

    req = request.get_json(force=True, silent=True) or {}

    tenant = req.get("tenant")
    data = req.get("data")

    if not tenant:
        return {"error": "no tenant"}, 400

    if not data:
        return {"error": "no data"}, 400

    # 🔥 ensure tenant exists
    job_orders.setdefault(tenant, [])
    latest_job_order.setdefault(tenant, {"status": "none"})

    # 🔥 add metadata
    data["status"] = "done"
    data["timestamp"] = datetime.now().isoformat()
    data["job_id"] = f"JO-{int(datetime.now().timestamp())}"

    # 🔥 save history
    job_orders[tenant].append(data)

    # 🔥 set latest
    latest_job_order[tenant] = data

    # 🔥 persist
    save_job_data()

    print("JOB ORDER SAVED FOR:", tenant[:10])

    return {
        "status": "saved",
        "job_id": data["job_id"]
    }


# ==============================
# GET LATEST JOB ORDER (REAL-TIME)
# ==============================
@app.route("/get_job_order", methods=["GET"])
def get_job_order():
    global latest_job_order

    tenant = request.args.get("tenant")

    if not tenant:
        return {"status": "no tenant"}

    latest_job_order.setdefault(tenant, {"status": "none"})

    data = latest_job_order[tenant]

    # 🔥 one-time fetch (optional toggle)
    if data.get("status") != "none":
        latest_job_order[tenant] = {"status": "none"}
        save_job_data()

    return data


# ==============================
# GET JOB ORDER HISTORY
# ==============================
@app.route("/get_job_orders", methods=["GET"])
def get_job_orders():
    tenant = request.args.get("tenant")

    if not tenant:
        return []

    return job_orders.get(tenant, [])


# ==============================
# DELETE SINGLE JOB ORDER
# ==============================
@app.route("/delete_job_order", methods=["POST"])
def delete_job_order():
    
    if not check_api():
        return {"error": "unauthorized"}, 401
    
    global job_orders

    req = request.get_json(force=True, silent=True) or {}

    tenant = req.get("tenant")
    job_id = req.get("job_id")

    if not tenant or not job_id:
        return {"error": "missing data"}, 400

    if tenant not in job_orders:
        return {"error": "tenant not found"}, 404

    job_orders[tenant] = [
        j for j in job_orders[tenant]
        if j.get("job_id") != job_id
    ]

    save_job_data()

    return {"status": "deleted"}


# ==============================
# CLEAR JOB ORDERS
# ==============================
@app.route("/clear_job_orders", methods=["POST"])
def clear_job_orders():
    
    if not check_api():
        return {"error": "unauthorized"}, 401
    
    global job_orders, latest_job_order

    req = request.get_json(force=True, silent=True) or {}

    tenant = req.get("tenant")

    if not tenant:
        return {"error": "no tenant"}, 400

    job_orders[tenant] = []
    latest_job_order[tenant] = {"status": "none"}

    save_job_data()

    print("JOB ORDERS CLEARED FOR:", tenant[:10])

    return {"status": "cleared"}

# ==============================
# RUN SERVER
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
