"""The built docs are served from DOCS_BUILD_DIR, not bundled with the app -- see
app/routes/docs.py and scripts/build-docs.sh."""


def test_docs_404_when_not_built(client, app):
    app.config["DOCS_BUILD_DIR"] = "/nonexistent-docs-dir"
    resp = client.get("/docs/")
    assert resp.status_code == 404


def test_docs_serves_built_html(client, app, tmp_path):
    (tmp_path / "index.html").write_text("<html>docs home</html>")
    features = tmp_path / "features"
    features.mkdir()
    (features / "workout_logging.html").write_text("<html>workout logging</html>")
    app.config["DOCS_BUILD_DIR"] = str(tmp_path)

    assert b"docs home" in client.get("/docs/").data
    assert b"docs home" in client.get("/docs", follow_redirects=True).data
    assert b"workout logging" in client.get("/docs/features/workout_logging.html").data
    assert client.get("/docs/features/missing.html").status_code == 404
