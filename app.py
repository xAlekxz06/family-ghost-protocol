import os
import hmac
import psycopg
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

def get_db():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=10
    )

def is_locked():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT locked FROM public.site_state WHERE id = 1"
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("site_state row missing")
            return row[0]

def admin_ok():
    expected = os.environ.get("ADMIN_PASSWORD", "")
    supplied = request.headers.get("X-Admin-Password", "")
    return bool(expected) and hmac.compare_digest(supplied, expected)

@app.get("/")
def home():
    if is_locked():
        return render_template("index.html", site_locked=True), 200
    return render_template("index.html", site_locked=False)

@app.get("/api/status")
def status():
    return jsonify({"locked": is_locked()})

@app.post("/api/lock-after-trailer")
def lock_after_trailer():
    # Bloqueio fict??cio do pr??prio site, persistido no banco.
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.site_state "
                "SET locked = TRUE, updated_at = now() WHERE id = 1"
            )
    return jsonify({"locked": True})


@app.post("/api/lock")
def lock():
    if not admin_ok():
        return jsonify({"error": "Unauthorized"}), 401
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.site_state SET locked = TRUE, updated_at = now() WHERE id = 1"
            )
    return jsonify({"locked": True})

@app.post("/api/unlock")
def unlock():
    if not admin_ok():
        return jsonify({"error": "Unauthorized"}), 401
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.site_state SET locked = FALSE, updated_at = now() WHERE id = 1"
            )
    return jsonify({"locked": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
