from playwright.sync_api import sync_playwright
import time
import subprocess
import os

def test_loading_state():
    print("Starting server...")

    # Set required environment variables
    env = os.environ.copy()
    env.update({
        "SESSION_SECRET": "test_secret_123",
        "ADMIN_PASSWORD": "test_password_456",
        "MAIL_FROM": "test@example.com",
        "DATABASE_URL": "sqlite:///./data/app.db",
        "DATA_DIR": "./data"
    })

    # Start the server
    server_process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8085"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    time.sleep(3) # Wait for server to start

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Go to login page
            print("Navigating to login page...")
            page.goto("http://127.0.0.1:8085/admin/login")

            # Fill out form
            page.fill("input[name='username']", "admin")
            page.fill("input[name='password']", "password")

            # Intercept form submission to see the loading state
            print("Intercepting form submission...")
            page.evaluate("""() => {
                document.querySelector('form').addEventListener('submit', (e) => {
                    e.preventDefault();
                });
            }""")

            # Submit the form
            print("Clicking submit button...")
            page.click("button[type='submit'], button:not([type='button'])")

            # Wait a tiny bit for the setTimeout in our base.html script
            page.wait_for_timeout(100)

            # Check for spinner and disabled state
            print("Verifying loading state...")
            submit_btn = page.locator("button:not([type='button'])")

            # Check disabled
            is_disabled = submit_btn.evaluate("el => el.disabled")
            assert is_disabled, "Button should be disabled"

            # Check innerHTML for spinner SVG
            inner_html = submit_btn.evaluate("el => el.innerHTML")
            assert "svg" in inner_html.lower() and "spinner" in inner_html.lower(), "Button should contain a spinner"

            # Check a11y announcer
            announcer_text = page.locator("#a11y-announcer").inner_text()
            assert "bitte warten" in announcer_text.lower(), f"Announcer text is incorrect: {announcer_text}"

            # Take a screenshot
            page.screenshot(path="screenshot_loading_state.png")
            print("Verification successful! Screenshot saved to screenshot_loading_state.png")

            browser.close()
    except Exception as e:
        print(f"Error during verification: {e}")
        raise
    finally:
        print("Stopping server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    test_loading_state()
