import sqlalchemy as db

from shared.database import engine


def test_saved_recommendations_and_deletion_are_scoped_to_current_user(authenticated_client, csrf_token):
    with authenticated_client.session_transaction() as session:
        user_id = session["user_id"]
    with engine.begin() as connection:
        connection.execute(db.text("INSERT INTO foodiesrn_recommendations (name, location, user_id) VALUES (:name, 'Austin', :uid)"),
                           [{"name": "My Cafe", "uid": user_id}, {"name": "Private Other Cafe", "uid": 99}])
    response = authenticated_client.get("/my_recommendations")
    assert response.status_code == 200
    assert b"My Cafe" in response.data
    assert b"Private Other Cafe" not in response.data
    response = authenticated_client.post("/delete_restaurant", json={"name": "Private Other Cafe", "location": "Austin"},
                                         headers={"X-CSRFToken": csrf_token(authenticated_client)})
    assert response.status_code == 200
    with engine.connect() as connection:
        assert connection.execute(db.text("SELECT count(*) FROM foodiesrn_recommendations WHERE user_id = 99")).scalar_one() == 1
