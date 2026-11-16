"""Tests for the Django admin page."""

from django.test import TestCase


class AdminPageTests(TestCase):
    """Check that the Django admin login page is available."""

    def test_admin_login_page_is_available(self):
        """Verify the login page responds successfully."""
        response = self.client.get("/admin/login/")

        self.assertEqual(response.status_code, 200)
