from flask import Flask, render_template, request, redirect, url_for, session
import docker, psutil, sqlite3, os

app = Flask(__name__)
app.secret_key = "12345" # Change this for security!
client = docker.from_env()

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('panel.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, user TEXT, pwd TEXT)')
    # Default login: admin / admin123
    conn.execute('INSERT OR IGNORE INTO users (id, user, pwd) VALUES (1, "admin", "admin123")')
    conn.commit()
    conn.close()

init_db()

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['user'], request.form['pwd']
        conn = sqlite3.connect('panel.db')
        user = conn.execute('SELECT * FROM users WHERE user=? AND pwd=?', (u, p)).fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    containers = client.containers.list(all=True)
    stats = {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent
    }
    return render_template('index.html', containers=containers, stats=stats)

@app.route('/create', methods=['POST'])
def create():
    name = request.form.get('name')
    image = request.form.get('image') # e.g., "ubuntu", "alpine", "nginx"
    hostname = request.form.get('hostname')
    
    client.containers.run(
        image, 
        name=name, 
        hostname=hostname, 
        detach=True, 
        command="sleep infinity"
    )
    return redirect(url_for('index'))

@app.route('/action/<id>/<act>')
def action(id, act):
    c = client.containers.get(id)
    if act == "start": c.start()
    elif act == "stop": c.stop()
    elif act == "delete": c.remove(force=True)
    elif act == "ssh":
        # Logic: In a real panel, this would trigger a tmate session
        return f"SSH into {c.name}: Open Terminal and run 'docker exec -it {c.name} sh'"
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
