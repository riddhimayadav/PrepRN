import unittest
from app import app

class TestPrepRNEatOut(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret'
        self.client = app.test_client()

    def test_eatout_page_loads(self):
        """GET /eatout should load with status 200 and include the form."""
        response = self.client.get('/eatout')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Find Your Next Spot', response.data)

    def test_eatout_missing_fields(self):
        """POST /eatout with missing fields should return error message."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.post('/eatout', data={
            "location": "",
            "radius": "",
            "cuisine": "",
            "price": "",
            "vibe": ""
        }, follow_redirects=True)
        self.assertIn(b'Please fill out all fields', response.data)

    def test_eatout_valid_post(self):
        """POST /eatout with valid fields should return 200 and maybe results."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.post('/eatout', data={
            "location": "New York",
            "radius": "10",
            "cuisine": "Thai",
            "price": "$$",
            "vibe": "Cozy"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Top Recommendations', response.data)  # Only if mock returns something

if __name__ == '__main__':
    unittest.main()
