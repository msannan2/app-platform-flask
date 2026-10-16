import hashlib
import hmac
import os
import time
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, app, request, jsonify, redirect, abort, render_template, url_for

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

# The request log grows without bound. Rendering every row makes a multi-megabyte
# page that browsers never finish painting.
DASHBOARD_REQUEST_LIMIT = 100


@app.route('/dashboard')
def dashboard():
    requests = (
        Request.query.order_by(Request.id.desc())
        .limit(DASHBOARD_REQUEST_LIMIT)
        .all()
    )
    return render_template('dashboard.html', requests=requests)


# Reject SSO tokens older than this. DigitalOcean recommends a minute or two.
SSO_MAX_AGE_SECONDS = 120


def verify_sso_token(resource_uuid, auth_token, timestamp, user_id, user_email, salt):
    """Validate DigitalOcean's auth_token.

    The token is hex(HMAC-SHA256(salt, "timestamp:resource_uuid:user_id:user_email")).
    See https://marketplace.digitalocean.com/vendors/saas-api-docs
    """
    if not auth_token or timestamp is None:
        return False
    try:
        issued_at = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - issued_at) > SSO_MAX_AGE_SECONDS:
        return False

    message = f"{timestamp}:{resource_uuid}:{user_id}:{user_email}".encode()
    digest = hmac.new(salt.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, auth_token)


def _sso_form():
    if request.method == "POST":
        return request.form
    return request.args

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

    new_request = Request(
        method=request.method,
        url=request.url,
        payload=request.data.decode('utf-8')
    )
    db.session.add(new_request)
    db.session.commit()

    if resource_uuid in resources:
        del resources[resource_uuid]
        return '', 204
    else:
        return jsonify({"message": "Resource not found."}), 410

@app.route('/digitalocean/resources/<resource_uuid>', methods=['PUT'])
def change_plan(resource_uuid):

    new_request = Request(
        method=request.method,
        url=request.url,
        payload=request.data.decode('utf-8')
    )
    db.session.add(new_request)
    db.session.commit()

    data = request.json
    if resource_uuid in resources:
        resources[resource_uuid]['plan_slug'] = data['plan_slug']
        return '', 204
    else:
        return jsonify({"message": "Resource not found."}), 404

@app.route('/digitalocean/notifications', methods=['POST'])
def handle_notifications():

    new_request = Request(
        method=request.method,
        url=request.url,
        payload=request.data.decode('utf-8')
    )
    db.session.add(new_request)
    db.session.commit()

    data = request.json
    # Log the notification
    print(f"Notification received: {data}")
    return '', 204

@app.route('/digitalocean/sso', methods=['GET', 'POST'])
@app.route('/dashboard/digitalocean/sso', methods=['GET', 'POST'])
def sso():
    # DigitalOcean posts the SSO form to {base}/digitalocean/sso.
    # This listing's Open dashboard button calls /dashboard/digitalocean/sso,
    # so both paths land on the same handler and then the real dashboard.
    payload = request.get_data(as_text=True)
    if not payload and request.query_string:
        payload = request.query_string.decode('utf-8')

    new_request = Request(
        method=request.method,
        url=request.url,
        payload=payload
    )
    db.session.add(new_request)
    db.session.commit()

    salt = os.getenv("DIGITALOCEAN_SSO_SALT")
    if salt:
        form = _sso_form()
        if not verify_sso_token(
            form.get("resource_uuid", ""),
            form.get("auth_token", ""),
            form.get("timestamp", ""),
            form.get("user_id", ""),
            form.get("user_email", ""),
            salt,
        ):
            abort(401)

    return redirect(url_for("dashboard"))