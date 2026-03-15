from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import docker, psutil, sqlite3

app = Flask(__name__)
app.secret_key = "vpanel_elite_key"
client = docker.from_env()

# Database Setup
conn = sqlite3.connect('panel.db', check_same_thread=False)
conn.execute('CREATE TABLE IF NOT EXISTS users (user TEXT PRIMARY KEY, pwd TEXT)')
conn.execute('INSERT OR IGNORE INTO users VALUES ("admin", "admin123")')
conn.commit()

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    containers = client.containers.list(all=True)
    return render_template('dashboard.html', containers=containers)

@app.route('/stats')
def stats():
    return jsonify({
        'cpu': psutil.cpu_percent(),
        'ram': psutil.virtual_memory().percent
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['user'] == "admin" and request.form['pwd'] == "admin123":
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/create', methods=['POST'])
def create():
    client.containers.run(
        request.form.get('image'),
        name=request.form.get('name'),
        hostname=request.form.get('hostname'),
        detach=True, tty=True, stdin_open=True
    )
    return redirect(url_for('index'))

@app.route('/action/<id>/<act>')
def action(id, act):
    c = client.containers.get(id)
    if act == "start": c.start()
    elif act == "stop": c.stop()
    elif act == 'remove': c.remove(force=True)
    return redirect(url_for('index'))

# Simple Web Console Logic
@app.route('/terminal/<id>', methods=['POST'])
def terminal(id):
    cmd = request.json.get('cmd')
    container = client.containers.get(id)
    result = container.exec_run(cmd).output.decode('utf-8')
    return jsonify({'output': result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
