from flask import Flask, render_template_string, request, redirect
import csv
import os

app = Flask(__name__)

CSV_FILE = "jadwal.csv"

HTML = """
<h2>Dashboard Jadwal Route</h2>

<table border=1>
<tr>
<th>Route</th>
<th>Start</th>
<th>Selesai</th>
</tr>

{% for r in rows %}
<tr>
<td>{{r[0]}}</td>
<td>{{r[1]}}</td>
<td>{{r[2]}}</td>
</tr>
{% endfor %}
</table>

<h3>Tambah Jadwal</h3>

<form method="post">
Route:<br>
<input name="route"><br>
Start:<br>
<input name="start"><br>
Selesai:<br>
<input name="selesai"><br><br>
<button type="submit">Tambah</button>
</form>
"""

@app.route("/", methods=["GET","POST"])
def index():

    if request.method == "POST":
        route = request.form["route"]
        start = request.form["start"]
        selesai = request.form["selesai"]

        with open(CSV_FILE,"a",newline="") as f:
            writer = csv.writer(f)
            writer.writerow([route,start,selesai])

        return redirect("/")

    rows=[]
    with open(CSV_FILE) as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            rows.append(r)

    return render_template_string(HTML,rows=rows)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
