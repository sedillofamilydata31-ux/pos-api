from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "API RUNNING"

@app.route("/sync", methods=["POST"])
def sync():
    data = request.json
    print("RECEIVED:", data)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))