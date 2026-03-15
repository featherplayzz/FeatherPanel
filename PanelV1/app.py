from flask import Flask, render_template, request, redirect, url_for
import docker

app = Flask(__name__)

# This connects to the Docker engine inside Codespaces
try:
    client = docker.from_env()
except Exception as e:
    print("Error: Could not connect to Docker. Make sure it is running!")
    client = None

@app.route('/')
def index():
    # Get all containers (VPS instances)
    containers = client.containers.list(all=True) if client else []
    return render_template('index.html', containers=containers)

@app.route('/create', methods=['POST'])
def create_vps():
    name = request.form.get('name')
    if client and name:
        # This creates a tiny 'Alpine' Linux instance (uses very little RAM)
        client.containers.run("alpine", name=name, detach=True, command="sleep 3600")
    return redirect(url_for('index'))

@app.route('/action/<id>/<act>')
def action(id, act):
    container = client.containers.get(id)
    if act == "start": container.start()
    elif act == "stop": container.stop()
    elif act == "delete": container.remove(force=True)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # '0.0.0.0' allows GitHub Codespaces to preview the site
    app.run(host='0.0.0.0', port=5000, debug=True)
  
