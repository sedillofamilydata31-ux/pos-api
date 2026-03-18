from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# temporary storage (pwede natin palitan ng DB later)
inventory_data = {}

@app.route("/")
def home():
    return "API RUNNING"

# 👉 SAVE INVENTORY (galing POS mo)
@app.route("/sync_inventory", methods=["POST"])
def sync_inventory():
    global inventory_data
    inventory_data = request.json  # full object na
    print("FULL INVENTORY RECEIVED")
    return jsonify({"status": "saved"})

# 👉 GET INVENTORY (para sa web dashboard mo)
@app.route("/get_inventory", methods=["GET"])
def get_inventory():
    return jsonify(inventory_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))