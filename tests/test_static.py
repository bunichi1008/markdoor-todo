def test_screen_and_assets_are_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="ja"' in response.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
