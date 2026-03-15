from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import docker, sqlite3, os

app = Flask(__name__)
app.secret_key = "vpanel_elite_pro_key"

# --- DATABASE ARCHITECTURE ---
def get_db():
    conn = sqlite3.connect('vpanel.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    # Users: role 0 = User, 1 = Admin
    db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, user TEXT, pwd TEXT, role INTEGER)')
    # Nodes: External servers
    db.execute('CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY, name TEXT, ip TEXT, status TEXT)')
    # Instances: Linked to users and nodes
    db.execute('CREATE TABLE IF NOT EXISTS instances (id INTEGER PRIMARY KEY, name TEXT, owner TEXT, node_id INTEGER, ram TEXT, cpu TEXT, disk TEXT, image TEXT)')
    db.execute('INSERT OR IGNORE INTO users VALUES (1, "admin", "admin123", 1)')
    db.commit()

init_db()

# --- ADMIN: USER MANAGEMENT ---
@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if not session.get('is_admin'): return "Access Denied"
    db = get_db()
    if request.method == 'POST':
        db.execute('INSERT INTO users (user, pwd, role) VALUES (?, ?, ?)', 
                   (request.form['user'], request.form['pwd'], request.form['role']))
        db.commit()
    users = db.execute('SELECT * FROM users').fetchall()
    return render_template('users.html', users=users)

# --- INSTANCE CREATION ---
@app.route('/create_instance', methods=['POST'])
def create_instance():
    # Logic to deploy to a specific Node
    # In this version, we deploy to 'Local Node' via Docker
    try:
        client = docker.from_env()
        client.containers.run(
            request.form['image'],
            name=request.form['name'],
            hostname=request.form['hostname'],
            mem_limit=request.form['ram'], # e.g. "512m"
            nano_cpus=int(float(request.form['cpu']) * 1e9),
            detach=True,
            ports={f"{request.form['port']}/tcp": None}
        )
        # Save to DB
        db = get_db()
        db.execute('INSERT INTO instances (name, owner, image, ram) VALUES (?,?,?,?)',
                   (request.form['name'], request.form['owner'], request.form['image'], request.form['ram']))
        db.commit()
    except Exception as e:
        return str(e)
    return redirect(url_for('index'))

# --- SSH TMATE LOGIC ---
@app.route('/ssh/<id>')
def ssh_tmate(id):
    client = docker.from_env()
    container = client.containers.get(id)
    # The "Master" sequence: Install tmate and get the link
    cmd = "sh -c 'apt update && apt install tmate -y && tmate -S /tmp/tmate.sock new-session -d && tmate -S /tmp/tmate.sock wait tmate-ready && tmate -S /tmp/tmate.sock display -p \"#{tmate_ssh}\"'"
    result = container.exec_run(cmd).output.decode('utf-8')
    return jsonify({'ssh_code': result})

# Rest of routes (login, index, etc) follow previous logic...
