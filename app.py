from flask import Flask, request, render_template_string
import pdfplumber
import os
import sqlite3

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("invoices.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT,
            date TEXT,
            vendor TEXT,
            item TEXT,
            total TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- PDF ----------------
def extract_data(pdf_path):
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"

    data = {
        "invoice_no": "",
        "date": "",
        "vendor": "",
        "item": "",
        "total": ""
    }

    for line in text.split("\n"):
        if "Invoice No" in line:
            data["invoice_no"] = line.split(":")[-1].strip()
        elif "Date" in line:
            data["date"] = line.split(":")[-1].strip()
        elif "Vendor" in line:
            data["vendor"] = line.split(":")[-1].strip()
        elif "Item" in line:
            data["item"] = line.split(":")[-1].strip()
        elif "Total" in line:
            data["total"] = line.split(":")[-1].strip()

    return data

# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def upload_file():
    result = None

    if request.method == "POST":
        file = request.files["file"]
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        result = extract_data(path)

        conn = sqlite3.connect("invoices.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO invoices (invoice_no, date, vendor, item, total)
            VALUES (?, ?, ?, ?, ?)
        """, (
            result["invoice_no"],
            result["date"],
            result["vendor"],
            result["item"],
            result["total"]
        ))
        conn.commit()
        conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Invoice AI</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>

<body class="bg-light">

<div class="container mt-5">

    <div class="card shadow p-4">
        <h2 class="text-center">📄 Invoice Extractor</h2>

        <form method="POST" enctype="multipart/form-data" class="mt-4">
            <input class="form-control" type="file" name="file" required>
            <button class="btn btn-primary w-100 mt-3">Upload & Extract</button>
        </form>

        {% if result %}
        <div class="alert alert-success mt-4">
            <h5>Extracted Data</h5>
            <pre>{{ result }}</pre>
        </div>
        {% endif %}

        <a href="/invoices" class="btn btn-dark w-100 mt-2">View Dashboard</a>
    </div>

</div>

</body>
</html>
""", result=result)

# ---------------- DASHBOARD ----------------
@app.route("/invoices")
def show_invoices():
    conn = sqlite3.connect("invoices.db")
    c = conn.cursor()
    c.execute("SELECT * FROM invoices")
    rows = c.fetchall()
    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>

<body class="bg-light">

<div class="container mt-5">

    <h2 class="mb-4">📊 Invoice Dashboard</h2>

    <table class="table table-striped table-hover shadow bg-white">
        <thead class="table-dark">
            <tr>
                <th>ID</th>
                <th>Invoice No</th>
                <th>Date</th>
                <th>Vendor</th>
                <th>Item</th>
                <th>Total</th>
                <th>Actions</th>
            </tr>
        </thead>

        <tbody>
        {% for row in rows %}
            <tr>
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
                <td>₹{{ row[5] }}</td>
                <td>
                    <a class="btn btn-sm btn-warning" href="/edit/{{ row[0] }}">Edit</a>
                    <a class="btn btn-sm btn-danger" href="/delete/{{ row[0] }}">Delete</a>
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>

    <a href="/" class="btn btn-secondary">⬅ Back</a>
</div>

</body>
</html>
""", rows=rows)

# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete_invoice(id):
    conn = sqlite3.connect("invoices.db")
    c = conn.cursor()
    c.execute("DELETE FROM invoices WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return "<script>window.location.href='/invoices'</script>"

# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_invoice(id):
    conn = sqlite3.connect("invoices.db")
    c = conn.cursor()

    if request.method == "POST":
        c.execute("""
            UPDATE invoices
            SET invoice_no=?, date=?, vendor=?, item=?, total=?
            WHERE id=?
        """, (
            request.form["invoice_no"],
            request.form["date"],
            request.form["vendor"],
            request.form["item"],
            request.form["total"],
            id
        ))
        conn.commit()
        conn.close()
        return "<script>window.location.href='/invoices'</script>"

    c.execute("SELECT * FROM invoices WHERE id=?", (id,))
    row = c.fetchone()
    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Edit Invoice</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>

<body class="bg-light">

<div class="container mt-5">

    <div class="card p-4 shadow">
        <h3>Edit Invoice</h3>

        <form method="POST">
            <input class="form-control mt-2" name="invoice_no" value="{{ row[1] }}">
            <input class="form-control mt-2" name="date" value="{{ row[2] }}">
            <input class="form-control mt-2" name="vendor" value="{{ row[3] }}">
            <input class="form-control mt-2" name="item" value="{{ row[4] }}">
            <input class="form-control mt-2" name="total" value="{{ row[5] }}">

            <button class="btn btn-success mt-3 w-100">Update</button>
        </form>

        <a href="/invoices" class="btn btn-secondary mt-2 w-100">Back</a>
    </div>

</div>

</body>
</html>
""", row=row)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)