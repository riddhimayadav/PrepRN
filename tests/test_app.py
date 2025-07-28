import unittest
from PrepRN.app import app
class TestPrepRNFlaskApp(unittest.TestCase):
    def setUp(self):
        # Configure test client
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret'
        self.client = app.test_client()
    def test_home_redirects_to_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
    def test_signup_page_loads(self):
        response = self.client.get('/signup')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign Up', response.data)
    def test_login_page_loads(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
    def test_my_recommendations_requires_login(self):
        response = self.client.get('/my_recommendations')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
    def test_prep_get_requires_login(self):
        response = self.client.get('/prep')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
    def test_logout_clears_session(self):
        with self.client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['user_id'] = 1
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn('username', sess)
            self.assertNotIn('user_id', sess)
if __name__ == '__main__':
    unittest.main()