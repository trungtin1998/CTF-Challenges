from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
import pymssql
from threading import Thread
import logging
import time
import traceback
import os
from datetime import datetime, timedelta, timezone


app = Flask(__name__)
app.logger.setLevel(logging.INFO)


app.secret_key = os.getenv("SECRET_KEY")
MSSQL_HOST = os.getenv("MSSQL_HOST")
MSSQL_USER = os.getenv("MSSQL_USER")
MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD")
MSSQL_DB = os.getenv("MSSQL_DB")
MSSQL_PORT = os.getenv("MSSQL_PORT")
next_cleanup_time = None
VN_TZ = timezone(timedelta(hours=7))


def conn_db():
    return pymssql.connect(
        server=MSSQL_HOST,
        user=MSSQL_USER,
        password=MSSQL_PASSWORD,
        database=MSSQL_DB,
        port=MSSQL_PORT,
        as_dict=True
    )

def auto_clean_task():
    global next_cleanup_time
    time.sleep(20)
    while True:
        try:
            with conn_db() as conn:
                conn.autocommit(True)
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT TABLE_NAME
                        FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_TYPE='BASE TABLE'
                    """)
                    tables = [row['TABLE_NAME'] for row in cur.fetchall()]
                    app.logger.info(f"[+] Found tables: {tables}")

                    for tbl in tables:
                        if tbl.lower() != "invoices" and tbl.lower() != "invoice_items":
                            cur.execute(f"DROP TABLE IF EXISTS {tbl}")
                    app.logger.info("[+] Database cleanup done. Waiting 15 minutes...")
        except Exception as e:
            app.logger.error(f"[!] Cleanup error: {repr(e)}")
            app.logger.error(traceback.format_exc())
        next_cleanup_time = datetime.now() + timedelta(minutes=15)
        time.sleep(15 * 60)

def start_background_cleaner():
    app.logger.info("[*] Starting background database cleaner thread...")
    thread = Thread(target=auto_clean_task, daemon=True)
    thread.start()

start_background_cleaner()

@app.route("/next_cleanup")
def get_next_cleanup():
    global next_cleanup_time
    api_key = request.headers.get("X-API")
    if api_key != "T6Cuqo4xfpsZqvhRdRrR":
        abort(404)
    if not next_cleanup_time:
        return jsonify({"status": "not started yet"})
    
    now = datetime.now()
    remaining = next_cleanup_time - now
    seconds_left = int(remaining.total_seconds())
    if seconds_left < 0:
        seconds_left = 0
    
    mins, secs = divmod(seconds_left, 60)
    return jsonify({
        "next_cleanup_at": next_cleanup_time.astimezone(VN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "time_left": f"{mins:02d}:{secs:02d}",
        "seconds_left": seconds_left
    })

@app.route('/')
def index():
    return redirect(url_for('admin'))

@app.route('/admin', methods=['GET'])
def admin():
    query = "SELECT TOP 50 id, invoice_number, customer_name, total_amount, created_at FROM invoices ORDER BY id ASC"

    with conn_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
    return render_template("dashboard.html", invoices=results, result_count=len(results), search='', error=None)


@app.route('/admin', methods=['POST'])
def search_invoices():
    search = request.form.get("search", "")
    if len(search) > 52:
        return render_template("dashboard.html", error="Search too long")
    if search.upper().find("BULK") != -1 or search.upper().find("UNION") != -1:
        return render_template("dashboard.html", error="Invalid search")
    
    # split space to search multiple keywords
    keywords = [k for k in search.split(" ") if k]
    keywords = [k[:20] for k in keywords]

    if not keywords:
        return render_template("dashboard.html", search='')
    
    # build SQL query
    conditions = f" invoice_number LIKE '%{keywords[0]}%'"
    for key in keywords[1:]:
        conditions += f" OR invoice_number LIKE '%{key}%'"
    query1 = f"""
        SELECT TOP 50 id, invoice_number, customer_name, total_amount, created_at
        FROM invoices WHERE {conditions} ORDER BY id ASC
    """


    query2 = f"""SELECT count(id) AS total_count FROM invoices WHERE {conditions}"""
    error = None
    results1 = []
    result_count = 0
    try:
        with conn_db() as conn1, conn_db() as conn2:
            # allow INSERT, UPDATE on conn1
            conn1.autocommit(True)
            with conn1.cursor() as cur1, conn2.cursor() as cur2:
                cur1.execute(query1)
                results1 = cur1.fetchall()

                cur2.execute(query2)
                count_row = cur2.fetchone()
                result_count = count_row["total_count"] if count_row else 0
    except Exception as e:
        error = str(query1)
        app.logger.error(f"Query Error: {e}")
    return render_template("dashboard.html", invoices=results1, result_count=result_count, search=search, error=error)

@app.route('/show_source')
def show_source():
    api_key = request.headers.get("X-API")
    if api_key != "T6Cuqo4xfpsZqvhRdRrR":
        abort(404)
    file_path = os.path.join(os.path.dirname(__file__), 'app.py')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        return jsonify({"source": source_code})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)

