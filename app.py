import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, app, request, jsonify, redirect, abort, render_template

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    method = db.Column(db.String(10), nullable=False)
    url = db.Column(db.Text, nullable=False)
    payload = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Automatically create the tables
with app.app_context():
    db.create_all()

# Dummy storage for resources
resources = {}

@app.route('/api', methods=['GET'])
def handle_request():
    new_request = Request(
        method=request.method,
        url=request.url,
        payload=request.data.decode('utf-8')
    )
    db.session.add(new_request)
    db.session.commit()
    return jsonify({"message": "Request saved"}), 201

@app.route('/dashboard')
def dashboard():
    requests = Request.query.all()
    return render_template('dashboard.html', requests=requests)


# # Helper function to verify DigitalOcean requests
# def verify_request(auth_header):
#     encoded_credentials = base64.b64encode(f"{app_slug}:{app_password}".encode()).decode()
#     return auth_header == f"Basic {encoded_credentials}"

# # Helper function to verify SSO requests
# def verify_sso_token(resource_uuid, token, timestamp):
#     message = f"{timestamp}:{resource_uuid}".encode()
#     digest = hmac.new(app_salt.encode(), message, hashlib.sha256).hexdigest()
#     return hmac.compare_digest(digest, token)

@app.route('/digitalocean/resources', methods=['POST'])
def provision_resource():

    data = request.json
    resource_id = data['uuid']
    resources[resource_id] = data

    new_request = Request(
        method=request.method,
        url=request.url,
        payload=request.data.decode('utf-8')
    )
    db.session.add(new_request)
    db.session.commit()

    # Responding to the provision request
    return jsonify({
        "id": resource_id,
        "config": {
            "EXAMPLE_ENDPOINT": "https://do-user:password@api.example.com/v1",
            "EXAMPLE_FOO": "BAR"
        },
        "message": "Resource provisioned successfully."
    }), 201

@app.route('/digitalocean/resources/<resource_uuid>', methods=['DELETE'])
def deprovision_resource(resource_uuid):

    if resource_uuid in resources:
        del resources[resource_uuid]
        return '', 204
    else:
        return jsonify({"message": "Resource not found."}), 410

@app.route('/digitalocean/resources/<resource_uuid>', methods=['PUT'])
def change_plan(resource_uuid):

    data = request.json
    if resource_uuid in resources:
        resources[resource_uuid]['plan_slug'] = data['plan_slug']
        return '', 204
    else:
        return jsonify({"message": "Resource not found."}), 404

@app.route('/digitalocean/notifications', methods=['POST'])
def handle_notifications():

    data = request.json
    # Log the notification
    print(f"Notification received: {data}")
    return '', 204

@app.route('/digitalocean/sso', methods=['POST'])
def sso():
    redirect("https://www.example.com/dashboard")