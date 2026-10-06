import os
import socket
import threading
import time

import pytest
import uvicorn

from app.main import create_app


@pytest.fixture
def live_url(database_url):
    app = create_app(database_url)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.02)
    try:
        assert server.started, "Test server did not start"
        yield f"http://127.0.0.1:{sock.getsockname()[1]}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


@pytest.fixture
def page(live_url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
            args=["--no-sandbox"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900}, timezone_id="UTC")
        page = context.new_page()
        page.set_default_timeout(10000)
        page.goto(live_url)
        yield page
        context.close()
        browser.close()
