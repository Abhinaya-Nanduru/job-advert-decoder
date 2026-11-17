"""The API contract. These are the tests CI runs on every push."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SQLITE_PATH",
                      os.path.join(tempfile.mkdtemp(), "test_requests.db"))

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)
ADVERT = ("Senior AI Engineer, Python and LangChain, AWS, eight years, "
          "London three days a week.")


class Health(unittest.TestCase):
    def test_health_answers(self):
        r = client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_health_names_the_environment_and_database(self):
        d = client.get("/api/health").json()
        self.assertIn(d["environment"], ("development", "staging", "production"))
        self.assertIn(d["database"], ("sqlite", "postgres"))

    def test_health_never_leaks_the_key_itself(self):
        body = client.get("/api/health").text
        self.assertIn("api_key_configured", body)
        key = os.environ.get("GROQ_API_KEY")
        if key:
            self.assertNotIn(key, body)


class Decode(unittest.TestCase):
    def test_a_normal_advert_returns_all_five_stages(self):
        r = client.post("/api/decode", json={"advert": ADVERT})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d["ok"])
        self.assertEqual(len(d["trace"]), 5)
        self.assertIn("seniority", d["answer"])

    def test_empty_advert_is_refused_with_422(self):
        r = client.post("/api/decode", json={"advert": ""})
        self.assertEqual(r.status_code, 422)
        self.assertIsNone(r.json()["answer"])

    def test_oversized_advert_is_refused(self):
        r = client.post("/api/decode", json={"advert": "x" * 9000})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(len(r.json()["trace"]), 1)

    def test_a_body_that_is_not_json_gets_400(self):
        r = client.post("/api/decode", content="not json",
                        headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 400)

    def test_missing_advert_field_is_refused_not_crashed(self):
        r = client.post("/api/decode", json={"wrong_field": "hello"})
        self.assertEqual(r.status_code, 422)

    def test_the_response_says_which_environment_answered(self):
        d = client.post("/api/decode", json={"advert": ADVERT}).json()
        self.assertIn("environment", d)


class Recent(unittest.TestCase):
    def test_requests_are_remembered(self):
        before = client.get("/api/recent").json()["stats"]["requests"]
        client.post("/api/decode", json={"advert": ADVERT})
        after = client.get("/api/recent").json()["stats"]["requests"]
        self.assertEqual(after, before + 1)

    def test_refused_requests_are_remembered_too(self):
        before = client.get("/api/recent").json()["stats"]["requests"]
        client.post("/api/decode", json={"advert": ""})
        after = client.get("/api/recent").json()["stats"]["requests"]
        self.assertEqual(after, before + 1,
                         "a refusal is exactly what you want in the log")

    def test_limit_is_capped(self):
        d = client.get("/api/recent?limit=9999").json()
        self.assertLessEqual(len(d["rows"]), 100)


class Frontend(unittest.TestCase):
    def test_the_page_is_served(self):
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Job Advert Decoder", r.text)

    def test_static_files_are_served(self):
        for path in ("/static/app.js", "/static/styles.css"):
            self.assertEqual(client.get(path).status_code, 200, path)

    def test_the_page_contains_no_api_key(self):
        """The frontend must never carry a secret. This is the whole point."""
        page = client.get("/").text + client.get("/static/app.js").text
        # real secret shapes only. "api_key_configured" is a boolean flag the
        # health endpoint returns, and it is not a secret.
        for marker in ("gsk_", "GROQ_API_KEY", "sk-", "Authorization",
                       "Bearer ", "api.groq.com"):
            self.assertNotIn(marker, page, f"{marker} must not reach the browser")

    def test_the_browser_never_talks_to_the_model_directly(self):
        """Every call the page makes must go to our own backend."""
        js = client.get("/static/app.js").text
        import re as _re
        for url in _re.findall(r'fetch\(\s*["\'`]([^"\'`]+)', js):
            self.assertTrue(url.startswith("/"),
                            f"the page fetches {url}, which is not our backend")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class SurvivesLosingTheDatabase(unittest.TestCase):
    """A free host throws the container away. The service must not die with it."""

    def test_reading_after_the_file_vanishes(self):
        client.post("/api/decode", json={"advert": ADVERT})
        path = os.environ["SQLITE_PATH"]
        if os.path.exists(path):
            os.remove(path)
        r = client.get("/api/recent")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["stats"]["requests"], 0,
                         "the rows are gone, which is the lesson")

    def test_decoding_still_works_after_the_file_vanishes(self):
        path = os.environ["SQLITE_PATH"]
        if os.path.exists(path):
            os.remove(path)
        r = client.post("/api/decode", json={"advert": ADVERT})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_a_rejected_key_returns_readable_json_not_a_500(self):
        import pipeline as P
        original = P.call_groq
        P.call_groq = lambda *a, **k: (_ for _ in ()).throw(
            P.ModelUnavailable("the model API rejected the key (401)."))
        os.environ["GROQ_API_KEY"] = "gsk_definitely_wrong"
        try:
            r = client.post("/api/decode", json={"advert": ADVERT})
            self.assertEqual(r.status_code, 422)
            body = r.json()
            self.assertFalse(body["ok"])
            self.assertIn("rejected the key", body["refusal"])
        finally:
            P.call_groq = original
            os.environ.pop("GROQ_API_KEY", None)
