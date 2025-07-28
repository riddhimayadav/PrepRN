import unittest
from app import app
from flask import session

class TestFoodiesRN(unittest.TestCase):
    def setUp(self):
        # Setup test client
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret'
        self.client = app.test_client()

    def test_get_foodies_page(self):
        # Check if the GET request loads the Eat Out page
        response = self.client.get('/run_foodiesrn')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Find Your Next Spot', response.data)

    def test_post_missing_fields(self):
        # Simulate a POST request with missing fields
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1  # simulate login
        response = self.client.post('/run_foodiesrn', data={
            'location': '',
            'cuisine': '',
            'price': '',
            'vibe': ''
        }, follow_redirects=True)
        self.assertIn(b'Please fill out all fields.', response.data)

    def test_post_with_valid_input(self):
        # Simulate a POST request with valid data
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.post('/run_foodiesrn', data={
            'location': 'New York, NY',
            'cuisine': 'Mexican',
            'price': '$$',
            'vibe': 'Cozy',
            'radius': '10'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Top Recommendations', response.data)

    def test_love_restaurant_post(self):
        # Test POST to /love_restaurant with sample data
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.post('/love_restaurant', json={
            'name': 'Taco Place',
            'location': 'New York, NY'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'loved', response.data)

if __name__ == '__main__':
    unittest.main()
