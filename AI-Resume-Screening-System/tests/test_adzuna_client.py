"""
Tests for AdzunaClient & Adzuna Live Jobs Integration
Covers:
- Success response parsing & schema normalization
- HTTP 401 / 403 Authentication Error
- HTTP 429 Rate Limit Error
- HTTP 500 Upstream Server Error
- Request Timeout Error
- Malformed JSON handling
- Missing fields in job results (safe parsing)
- Empty search results handling
- In-memory cache hit
- Missing environment credentials (Config Error)
- Live integration test (@pytest.mark.live / conditional unittest)
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import requests

from app.services.adzuna_client import (
    AdzunaClient,
    AdzunaError,
    AdzunaConfigError,
    AdzunaAuthError,
    AdzunaRateLimitError,
    AdzunaTimeoutError,
    AdzunaUpstreamError
)

# Optional pytest marker support
try:
    import pytest
    live_marker = pytest.mark.live
except ImportError:
    def live_marker(func):
        return func


class TestAdzunaClient(unittest.TestCase):
    """Unit tests for the resilient AdzunaClient service."""

    def setUp(self):
        # Instantiate a fresh client with mock credentials for unit testing
        self.client = AdzunaClient()
        self.client.app_id = "mock_test_id"
        self.client.app_key = "mock_test_key"
        self.client.country = "in"
        self.client.base_url = "https://api.adzuna.com/v1/api/jobs/in/search"
        self.client.timeout = 2.0
        self.client._cache.clear()

    @patch('requests.Session.get')
    def test_01_search_success(self, mock_get):
        """Verify successful Adzuna response parsing and normalization."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 1,
            "results": [
                {
                    "id": "12345",
                    "title": "Senior Python Developer",
                    "company": {"display_name": "Acme Software Corp"},
                    "location": {"display_name": "Bangalore, Karnataka"},
                    "description": "Looking for a <strong>Python</strong> expert with 3-5 years experience. Remote position.",
                    "salary_min": 1200000,
                    "salary_max": 1800000,
                    "contract_time": "full_time",
                    "created": "2026-09-24T10:00:00Z",
                    "redirect_url": "https://www.adzuna.in/details/12345"
                }
            ]
        }
        mock_get.return_value = mock_response

        jobs = self.client.search(q="Python", location="Bangalore")
        self.assertEqual(len(jobs), 1)
        job = jobs[0]

        self.assertEqual(job['id'], "adzuna_12345")
        self.assertEqual(job['title'], "Senior Python Developer")
        self.assertEqual(job['company'], "Acme Software Corp")
        self.assertEqual(job['location'], "Bangalore, Karnataka")
        self.assertEqual(job['work_mode'], "remote")
        self.assertEqual(job['salary_min'], 1200000)
        self.assertEqual(job['salary_max'], 1800000)
        self.assertIn("LPA", job['salary_display'])
        self.assertEqual(job['experience_hint'], "3-5 yrs")
        self.assertEqual(job['source'], "adzuna")
        self.assertEqual(job['apply_url'], "https://www.adzuna.in/details/12345")
        self.assertNotIn("<strong>", job['description_snippet'])

    @patch('requests.Session.get')
    def test_02_auth_failure_401(self, mock_get):
        """Verify HTTP 401 raises AdzunaAuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"error": "Unauthorized / Invalid App Key"}'
        mock_get.return_value = mock_response

        with self.assertRaises(AdzunaAuthError):
            self.client.search(q="Python")

    @patch('requests.Session.get')
    def test_03_rate_limit_429(self, mock_get):
        """Verify HTTP 429 raises AdzunaRateLimitError."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = '{"error": "Rate limit exceeded"}'
        mock_get.return_value = mock_response

        with self.assertRaises(AdzunaRateLimitError):
            self.client.search(q="Python")

    @patch('requests.Session.get')
    def test_04_upstream_failure_500(self, mock_get):
        """Verify HTTP 500 raises AdzunaUpstreamError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        with self.assertRaises(AdzunaUpstreamError):
            self.client.search(q="Python")

    @patch('requests.Session.get')
    def test_05_request_timeout(self, mock_get):
        """Verify request timeout raises AdzunaTimeoutError."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out after 2.0s")

        with self.assertRaises(AdzunaTimeoutError):
            self.client.search(q="Python")

    @patch('requests.Session.get')
    def test_06_malformed_json(self, mock_get):
        """Verify malformed JSON response raises AdzunaUpstreamError cleanly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        mock_get.return_value = mock_response

        with self.assertRaises(AdzunaUpstreamError):
            self.client.search(q="Python")

    @patch('requests.Session.get')
    def test_07_missing_fields_safe_parsing(self, mock_get):
        """Verify safe parsing with missing keys does not crash."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Results contain incomplete / None fields
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "999",
                    "title": None,
                    "company": None,
                    "location": None,
                    "description": None,
                    "salary_min": None,
                    "redirect_url": None
                },
                {
                    # completely empty object with no ID should be safely ignored
                }
            ]
        }
        mock_get.return_value = mock_response

        jobs = self.client.search(q="Test")
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job['id'], "adzuna_999")
        self.assertEqual(job['title'], "Job Opening")
        self.assertEqual(job['company'], "Confidential Company")
        self.assertEqual(job['location'], "India")
        self.assertEqual(job['salary_display'], "Not disclosed")

    @patch('requests.Session.get')
    def test_08_empty_results(self, mock_get):
        """Verify empty results array returns empty list without error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 0,
            "results": []
        }
        mock_get.return_value = mock_response

        jobs = self.client.search(q="NonExistentQueryXYZ123")
        self.assertEqual(jobs, [])

    @patch('requests.Session.get')
    def test_09_in_memory_cache_hit(self, mock_get):
        """Verify repeated calls with identical parameters hit memory cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 1,
            "results": [
                {"id": "cache_1", "title": "DevOps Engineer"}
            ]
        }
        mock_get.return_value = mock_response

        # Call 1: HTTP fetch
        res1 = self.client.search(q="DevOps", location="Remote")
        self.assertEqual(len(res1), 1)
        self.assertEqual(mock_get.call_count, 1)

        # Call 2: Cache hit (mock_get call count should NOT increase)
        res2 = self.client.search(q="DevOps", location="Remote")
        self.assertEqual(len(res2), 1)
        self.assertEqual(mock_get.call_count, 1)

    def test_10_missing_env_keys(self):
        """Verify client raises AdzunaConfigError when credentials are missing."""
        unconfigured_client = AdzunaClient()
        unconfigured_client.app_id = ""
        unconfigured_client.app_key = ""

        with self.assertRaises(AdzunaConfigError):
            unconfigured_client.search(q="Python")

    @live_marker
    def test_11_live_adzuna_api_integration(self):
        """
        Optional live integration test.
        Runs only if valid ADZUNA_APP_ID and ADZUNA_APP_KEY exist in environment.
        """
        real_client = AdzunaClient()
        if not real_client.is_configured():
            self.skipTest("Adzuna API keys not present in environment. Skipping live test.")

        diag = real_client.check_health(what="python", where="Ahmedabad", limit=2)
        self.assertTrue(diag["keys_loaded"])
        self.assertEqual(diag["status_code"], 200)
        self.assertGreaterEqual(diag["results_count"], 1)
        self.assertIsNone(diag["error_type"])


if __name__ == '__main__':
    unittest.main()
