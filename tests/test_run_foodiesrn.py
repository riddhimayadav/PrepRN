import unittest
from app import app
from flask import session

class TestDashboardRoutes(unittest.TestCase):

    def setUp(self):
        # Set up the test client
        app.config['TESTING'] = True
        self.client = app.test_client()

    def login_simulation(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'

    def test_dashboard_requires_login(self):
        # Test that the dashboard redirects to login if not logged in
        response = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_dashboard_loads_when_logged_in(self):
        # Simulate login and check dashboard access
        self.login_simulation()
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My Pantry', response.data)

    def test_add_pantry_item_missing_field(self):
        self.login_simulation()
        response = self.client.post('/add_pantry_item', data={}, follow_redirects=True)
        self.assertIn(b'Pantry item name is required.', response.data)

    def test_add_pantry_item_valid(self):
        self.login_simulation()
        response = self.client.post('/add_pantry_item', data={'item': 'rice'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'rice', response.data)

    def test_remove_pantry_item_invalid_index(self):
        self.login_simulation()
        response = self.client.post('/remove_pantry_item', data={'index': 'abc'}, follow_redirects=True)
        self.assertIn(b'Invalid pantry item index.', response.data)

    def test_remove_pantry_item_valid(self):
        self.login_simulation()
        # Add item first
        self.client.post('/add_pantry_item', data={'item': 'apple'}, follow_redirects=True)
        # Remove item
        response = self.client.post('/remove_pantry_item', data={'index': '0'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'apple', response.data)

if __name__ == '__main__':
    unittest.main()
