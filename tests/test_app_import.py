def test_app_imports():
    import app.main

    assert app.main.app.title == "Facturación Invisible API"
