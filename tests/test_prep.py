import unittest
from app import app

class TestPrepPage(unittest.TestCase):
    def setUp(self):
        # Setup the test client
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret'
        self.client = app.test_client()

    def test_prep_get_requires_login(self):
        # GET /prep without login should redirect
        response = self.client.get('/prep')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_prep_get_logged_in(self):
        # GET /prep with login should load the form
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.get('/prep')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Find Your Next Favorite Recipe', response.data)

    def test_prep_post_missing_fields(self):
        # POST with missing data should show error
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.post('/prep', data={
            "location": "",
            "budget": "",
            "servings": ""
        }, follow_redirects=True)
        self.assertIn(b'Please fill out all fields', response.data)

    def test_prep_post_valid_data(self):
        # POST valid data should show loading or results
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.post('/prep', data={
            "location": "New York",
            "grocery": "yes",
            "budget": "25.00",
            "servings": "2",
            "meal_type": "Dinner"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Meal Plan', response.data)

if __name__ == '__main__':
    unittest.main()