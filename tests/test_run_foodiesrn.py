from shared.pantry import add_pantry_item, get_pantry_items


def test_dashboard_updates_only_the_current_users_pantry(authenticated_client, csrf_token):
    with authenticated_client.session_transaction() as session:
        user_id = session["user_id"]
    add_pantry_item(99, "private-other-user-item")
    response = authenticated_client.post("/dashboard", data={
        "action": "update_pantry", "pantry_list": "rice, beans",
        "csrf_token": csrf_token(authenticated_client),
    }, follow_redirects=True)
    assert response.status_code == 200
    assert get_pantry_items(user_id) == ["beans", "rice"]
    assert get_pantry_items(99) == ["private-other-user-item"]
    assert b"private-other-user-item" not in response.data


def test_form_mutations_require_csrf(authenticated_client):
    response = authenticated_client.post("/dashboard", data={"action": "update_pantry", "pantry_list": "rice"})
    assert response.status_code == 400
