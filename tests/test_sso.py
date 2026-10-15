import hmac
import hashlib
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_URL"] = "sqlite:///" + _db.name
os.environ.pop("DIGITALOCEAN_SSO_SALT", None)

from app import app  # noqa: E402


class SsoRedirectTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("DIGITALOCEAN_SSO_SALT", None)
        self.client = app.test_client()

    def test_registered_sso_path_redirects_to_dashboard(self):
        response = self.client.post(
            "/digitalocean/sso",
            data={
                "resource_uuid": "55e362e6-ec4e-4ba0-9d09-49ff4a97362e",
                "timestamp": str(int(time.time())),
                "user_id": "user",
                "user_email": "user@marketplace.digitalocean.com",
                "auth_token": "unused-without-salt",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")

    def test_dashboard_prefixed_sso_path_redirects_to_dashboard(self):
        response = self.client.post("/dashboard/digitalocean/sso", data={})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")

    def test_invalid_auth_token_is_rejected_when_salt_is_configured(self):
        os.environ["DIGITALOCEAN_SSO_SALT"] = "secretAppSalt"
        response = self.client.post(
            "/digitalocean/sso",
            data={
                "resource_uuid": "resUUID",
                "timestamp": str(int(time.time())),
                "user_id": "userID",
                "user_email": "userEmail",
                "auth_token": "not-the-token",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_stale_auth_token_is_rejected_when_salt_is_configured(self):
        salt = "secretAppSalt"
        os.environ["DIGITALOCEAN_SSO_SALT"] = salt
        timestamp = str(int(time.time()) - 300)
        message = f"{timestamp}:resUUID:userID:userEmail".encode()
        token = hmac.new(salt.encode(), message, hashlib.sha256).hexdigest()
        response = self.client.post(
            "/digitalocean/sso",
            data={
                "resource_uuid": "resUUID",
                "timestamp": timestamp,
                "user_id": "userID",
                "user_email": "userEmail",
                "auth_token": token,
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_browser_get_on_dashboard_sso_path_redirects_without_salt(self):
        response = self.client.get("/dashboard/digitalocean/sso")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")

    def test_valid_auth_token_redirects_when_salt_is_configured(self):
        salt = "secretAppSalt"
        os.environ["DIGITALOCEAN_SSO_SALT"] = salt
        timestamp = str(int(time.time()))
        message = f"{timestamp}:resUUID:userID:userEmail".encode()
        token = hmac.new(salt.encode(), message, hashlib.sha256).hexdigest()
        response = self.client.post(
            "/dashboard/digitalocean/sso",
            data={
                "resource_uuid": "resUUID",
                "timestamp": timestamp,
                "user_id": "userID",
                "user_email": "userEmail",
                "auth_token": token,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")


if __name__ == "__main__":
    unittest.main()
