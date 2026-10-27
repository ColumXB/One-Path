from django.test import TestCase


class AdminPageTests(TestCase):
    def test_admin_login_page_is_available(self):
        response = self.client.get('/admin/login/')

        self.assertEqual(response.status_code, 200)
