from flask import Flask, request, jsonify, send_file
import json
import os
import io

app = Flask(__name__)

DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# ── API ENDPOINTS ─────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
def get_users():
    db = load_db()
    users = list(db.values())
    return jsonify(users)

@app.route("/api/stats", methods=["GET"])
def get_stats():
    db = load_db()
    users = list(db.values())
    total = len(users)
    training = sum(1 for u in users if u.get("status") == "training")
    certified = sum(1 for u in users if u.get("status") == "certified")
    failed = sum(1 for u in users if u.get("status") == "failed_entry")
    return jsonify({
        "total": total,
        "training": training,
        "certified": certified,
        "failed": failed,
        "new": sum(1 for u in users if u.get("status") == "new"),
    })

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    db = load_db()
    users = [v for v in db.values() if v.get("status") in ["training", "certified"]]
    users.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    return jsonify(users[:20])

@app.route("/api/user/<user_id>", methods=["GET"])
def get_user(user_id):
    db = load_db()
    user = db.get(str(user_id))
    if not user:
        return jsonify({"error": "Not found"}), 404
    return jsonify(user)

@app.route("/api/user/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    db = load_db()
    if str(user_id) in db:
        del db[str(user_id)]
        save_db(db)
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/user/<user_id>/reset", methods=["POST"])
def reset_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid in db:
        db[uid].update({
            "status": "new",
            "entry_score": 0,
            "current_day": 0,
            "completed_days": [],
            "streak": 0,
            "total_score": 0,
            "frozen": False,
        })
        save_db(db)
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/user/<user_id>/certify", methods=["POST"])
def certify_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid in db:
        db[uid]["status"] = "certified"
        db[uid]["certified_at"] = __import__("datetime").datetime.now().isoformat()
        save_db(db)
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "BITO Academy LMS"})

# ── SERVE WEB APP ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
@app.route("/lms", methods=["GET"])
def serve_lms():
    # Read the HTML file and return it
    lms_path = os.path.join(os.path.dirname(__file__), "lms.html")
    if os.path.exists(lms_path):
        return send_file(lms_path)
    return "<h1>LMS fayli topilmadi</h1>", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
