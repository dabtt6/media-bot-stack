from flask import Flask, request, redirect, render_template_string, session, jsonify
import sqlite3
import datetime
import requests

DB_PATH = "/crawler-db/crawler.db"

QBIT_URL = "http://qbittorrent:8080"
QBIT_USER = "admin"
QBIT_PASS = "111111"

USERNAME = "admin"
PASSWORD = "123456"

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ================= DB =================
def get_db():
    return sqlite3.connect(DB_PATH)

# ================= QBIT =================
def get_qbit_stats():
    try:
        s = requests.Session()
        s.post(f"{QBIT_URL}/api/v2/auth/login",
               data={"username":QBIT_USER,"password":QBIT_PASS})
        torrents = s.get(f"{QBIT_URL}/api/v2/torrents/info").json()

        stats = {
            "downloading":0,
            "queued":0,
            "uploading":0,
            "seeding":0,
            "paused":0,
            "total":len(torrents)
        }

        for t in torrents:
            state = t.get("state","")
            if state in ["downloading","stalledDL"]:
                stats["downloading"] += 1
            elif state in ["queuedDL","queuedUP"]:
                stats["queued"] += 1
            elif state == "uploading":
                stats["uploading"] += 1
            elif state == "seeding":
                stats["seeding"] += 1
            elif state in ["pausedDL","pausedUP"]:
                stats["paused"] += 1

        return stats
    except:
        return {"downloading":0,"queued":0,"uploading":0,"seeding":0,"paused":0,"total":0}

# ================= AUTH =================
@app.before_request
def auth():
    if request.endpoint not in ['login','api_dashboard','api_add_actor'] and 'user' not in session:
        return redirect('/login')

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["username"]==USERNAME and request.form["password"]==PASSWORD:
            session["user"]=USERNAME
            return redirect("/")
    return """
    <h2>Login</h2>
    <form method="POST">
    <input name="username"><br>
    <input name="password" type="password"><br>
    <button>Login</button>
    </form>
    """

# ================= DASHBOARD =================
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Media Control Center</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body { background:#0f172a; color:white; font-family:Arial; margin:0; padding:20px;}
.container { display:flex; gap:20px;}
.left, .right { flex:1; }
.card { background:#1e293b; padding:20px; border-radius:12px; margin-bottom:20px;}
table { width:100%; border-collapse:collapse;}
td,th { padding:8px; border-bottom:1px solid #334155;}
input { padding:8px; width:70%; }
button { padding:8px 12px; background:#3b82f6; border:none; color:white; cursor:pointer;}
</style>
</head>
<body>

<h2>🎬 Media Control Center</h2>

<div class="container">

<div class="left">
<div class="card">
<canvas id="statsChart" style="height:300px;"></canvas>
</div>
<div class="card" id="statsNumbers"></div>
</div>

<div class="right">

<div class="card">
<h3>⬇ qBittorrent Status</h3>
<table id="qbitTable"></table>
</div>

<div class="card">
<h3>➕ Add Actor</h3>
<form id="actorForm">
<input name="url" placeholder="Actress URL" required>
<button>Add</button>
</form>
</div>

<div class="card">
<h3>📋 Actor List</h3>
<table id="actorTable"></table>
</div>

</div>
</div>

<script>
const ctx = document.getElementById('statsChart').getContext('2d');
const chart = new Chart(ctx,{
    type:'doughnut',
    data:{
        labels:['New','Added','Exists'],
        datasets:[{
            data:[0,0,0],
            backgroundColor:['#facc15','#22c55e','#ef4444']
        }]
    },
    options:{ responsive:true, maintainAspectRatio:false }
});

async function loadDashboard(){
    const res = await fetch('/api/dashboard');
    const data = await res.json();

    chart.data.datasets[0].data=[
        data.stats.new,
        data.stats.added,
        data.stats.exists
    ];
    chart.update();

    document.getElementById("statsNumbers").innerHTML =
    `Actors: ${data.stats.actors} |
     Total: ${data.stats.total} |
     New: ${data.stats.new} |
     Added: ${data.stats.added} |
     Exists: ${data.stats.exists}`;

    document.getElementById("qbitTable").innerHTML = `
    <tr><td>Downloading</td><td>${data.qbit.downloading}</td></tr>
    <tr><td>Queued</td><td>${data.qbit.queued}</td></tr>
    <tr><td>Uploading</td><td>${data.qbit.uploading}</td></tr>
    <tr><td>Seeding</td><td>${data.qbit.seeding}</td></tr>
    <tr><td>Paused</td><td>${data.qbit.paused}</td></tr>
    <tr><td>Total</td><td>${data.qbit.total}</td></tr>
    `;

    document.getElementById("actorTable").innerHTML =
        data.actors.map(a=>`
        <tr>
        <td>${a.name}</td>
        <td>${a.count}</td>
        </tr>`).join("");
}

document.getElementById("actorForm").onsubmit = async (e)=>{
    e.preventDefault();
    const formData = new FormData(e.target);
    await fetch('/api/add_actor',{method:'POST',body:formData});
    e.target.reset();
    loadDashboard();
};

setInterval(loadDashboard,5000);
loadDashboard();
</script>

</body>
</html>
""")

# ================= API =================
@app.route("/api/dashboard")
def api_dashboard():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM actors")
    actors_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM downloads")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM downloads WHERE status='new'")
    new = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM downloads WHERE status='added'")
    added = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM downloads WHERE status='exists'")
    exists = c.fetchone()[0]

    c.execute("""
    SELECT a.name,
    (SELECT COUNT(*) FROM downloads d WHERE d.actor_name=a.name)
    FROM actors a
    ORDER BY a.id DESC
    """)
    actors = [{"name":r[0],"count":r[1]} for r in c.fetchall()]

    conn.close()

    return jsonify({
        "stats":{
            "actors":actors_count,
            "total":total,
            "new":new,
            "added":added,
            "exists":exists
        },
        "qbit":get_qbit_stats(),
        "actors":actors
    })

@app.route("/api/add_actor", methods=["POST"])
def api_add_actor():
    url = request.form["url"]
    name = url.rstrip("/").split("/")[-1].replace("-", " ").title()

    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""
        INSERT INTO actors (name,url,created_at)
        VALUES (?,?,?)
        """,(name,url,datetime.datetime.now().isoformat()))
        conn.commit()
    except:
        pass
    conn.close()
    return jsonify({"status":"ok"})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5050)
