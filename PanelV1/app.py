from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import docker
import psutil
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "vpanel_master_2026_key"

# --- DATABASE ENGINE ---
def get_db():
    conn = sqlite3.connect('vpanel.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    # Users: role 1 = Admin, 0 = User
    db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, user TEXT, pwd TEXT, role INTEGER)')
    # Nodes: Real host servers
    db.execute('CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY, name TEXT, ip TEXT, status TEXT)')
    # Instances: Virtual units
    db.execute('CREATE TABLE IF NOT EXISTS instances (id INTEGER PRIMARY KEY, name TEXT, owner TEXT, node_id INTEGER, ram TEXT, cpu TEXT, image TEXT)')
    
    # Default Admin
    db.execute('INSERT OR IGNORE INTO users VALUES (1, "admin", "admin123", 1)')
    # Default Local Node
    db.execute('INSERT OR IGNORE INTO nodes VALUES (1, "Local-Node-01", "127.0.0.1", "Online")')
    db.commit()
    db.close()

init_db()

# --- ROUTES ---
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    client = docker.from_env()
    containers = client.containers.list(all=True)
    
    # Get System Stats for Sidebar
    stats = {
        'cpu': psutil.cpu_percent(),
        'ram': psutil.virtual_memory().percent,
        'disk': psutil.disk_usage('/').percent
    }
    
    return render_template('dashboard.html', containers=containers, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['user'], request.form['pwd']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE user=? AND pwd=?', (u, p)).fetchone()
        db.close()
        if user:
            session['logged_in'] = True
            session['username'] = user['user']
            session['is_admin'] = True if user['role'] == 1 else False
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/create_instance', methods=['POST'])
def create_instance():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    name = request.form.get('name')
    image = request.form.get('image')
    ram = request.form.get('ram') # e.g. 512m
    cpu = float(request.form.get('cpu'))
    
    client = docker.from_env()
    try:
        client.containers.run(
            image,
            name=name,
            detach=True,
            mem_limit=ram,
            nano_cpus=int(cpu * 1e9),
            hostname=request.form.get('hostname'),
            tty=True,
            stdin_open=True
        )
        return redirect(url_for('index'))
    except Exception as e:
        return f"Deployment Error: {str(e)}"

@app.route('/action/<id>/<act>')
def action(id, act):
    client = docker.from_env()
    c = client.containers.get(id)
    if act == "start": c.start()
    elif act == "stop": c.stop()
    elif act == "restart": c.restart()
    elif act == "remove": c.remove(force=True)
    return redirect(url_for('index'))

@app.route('/ssh/<id>')
def ssh_tmate(id):
    client = docker.from_env()
    container = client.containers.get(id)
    # The 'Master' SSH Trigger
    cmd = "sh -c 'apt update && apt install tmate -y && tmate -S /tmp/tmate.sock new-session -d && tmate -S /tmp/tmate.sock wait tmate-ready && tmate -S /tmp/tmate.sock display -p \"#{tmate_ssh}\"'"
    try:
        result = container.exec_run(cmd).output.decode('utf-8').strip()
        return jsonify({'ssh_code': result if result else "Starting session... Try again in 5s."})
    except:
        return jsonify({'ssh_code': "Container must be running and have internet to use SSH."})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("🚀 VPanel Elite Pro is launching on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
        
