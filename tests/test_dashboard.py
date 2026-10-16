import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_URL"] = "sqlite:///" + _db.name
os.environ.pop("DIGITALOCEAN_SSO_SALT", None)

from app import Request, app, db  # noqa: E402


class DashboardRenderTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            Request.query.delete()
            db.session.commit()

    def test_dashboard_shows_heading_and_only_latest_requests(self):
        with app.app_context():
            db.session.add(Request(
                method="POST",
                url="https://example.test/oldest-marker",
                payload="{}",
            ))
            for index in range(120):
                db.session.add(Request(
                    method="GET",
                    url=f"https://example.test/filler/{index}",
                    payload="{}",
                ))
            db.session.add(Request(
                method="POST",
                url="https://example.test/newest-marker",
                payload='{"ok": true}',
            ))
            db.session.commit()

        response = self.client.get("/dashboard")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Your New Flask App", body)
        self.assertIn("https://example.test/newest-marker", body)
        self.assertNotIn("https://example.test/oldest-marker", body)
        self.assertLess(len(body), 500_000)


if __name__ == "__main__":
    unittest.main()
