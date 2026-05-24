import asyncio
import logging
import os
from typing import Dict, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


class BrowserBot:
    """
    Playwright-based browser automation engine for job application form filling.
    Each job portal may require custom selectors — extend fill_form() per portal.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def launch_browser(self, headless: Optional[bool] = None):
        """Launches a Playwright Chromium browser instance."""
        if headless is not None:
            self.headless = headless
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        self.page = await self.context.new_page()
        logging.info("Browser launched.")

    async def close_browser(self):
        """Gracefully closes the browser and Playwright instance."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logging.info("Browser closed.")
        except Exception as e:
            logging.warning(f"Error while closing browser: {e}")
        finally:
            self.browser = None
            self.context = None
            self.page = None
            self.playwright = None

    async def navigate(self, url: str):
        """Navigates to a URL and waits for the page to be ready."""
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch_browser() first.")
        logging.info(f"Navigating to: {url}")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(1.5)  # Allow dynamic content to settle
        logging.info(f"Page loaded: {url}")

    async def fill_form(self, form_data: Dict[str, str], resume_file_path: Optional[str] = None):
        """
        Fills a job application form using CSS selectors as keys.

        Args:
            form_data: Dict mapping CSS selectors to fill values.
                       Example: {'#name': 'Jane Doe', '#email': 'jane@example.com'}
            resume_file_path: Optional path to a resume file for upload fields.
        """
        if not self.page:
            raise RuntimeError("Browser not launched.")

        logging.info("Filling application form...")
        for selector, value in form_data.items():
            try:
                await self.page.wait_for_selector(selector, timeout=5000)
                await self.page.fill(selector, value)
                logging.info(f"  Filled '{selector}' with '{value}'")
                await asyncio.sleep(0.4 + 0.2 * (len(value) % 3))  # Human-like delay
            except Exception as e:
                logging.warning(f"  Could not fill '{selector}': {e}")

        if resume_file_path and os.path.exists(resume_file_path):
            logging.info(f"Uploading resume: {resume_file_path}")
            try:
                file_input = self.page.locator('input[type="file"]').first
                await file_input.set_input_files(resume_file_path)
                logging.info("Resume uploaded successfully.")
            except Exception as e:
                logging.warning(f"Resume upload failed: {e}")

    async def submit_form(self, submit_selector: str = 'button[type="submit"]') -> bool:
        """
        Clicks the form submit button.

        Returns:
            True if submission appeared successful, False otherwise.
        """
        if not self.page:
            raise RuntimeError("Browser not launched.")

        logging.info(f"Clicking submit button: '{submit_selector}'")
        try:
            await self.page.wait_for_selector(submit_selector, timeout=5000)
            await self.page.click(submit_selector)
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            logging.info("Form submitted successfully.")
            return True
        except Exception as e:
            logging.error(f"Submit failed for '{submit_selector}': {e}")
            page_content = await self.page.content()
            if "captcha" in page_content.lower():
                logging.warning("CAPTCHA detected after submit attempt.")
            return False

    async def check_for_captcha(self) -> bool:
        """
        Checks if a CAPTCHA challenge is present on the current page.

        Returns:
            True if CAPTCHA detected, False otherwise.
        """
        if not self.page:
            return False
        try:
            content = await self.page.content()
            captcha_signals = ["captcha", "i'm not a robot", "recaptcha", "hcaptcha"]
            return any(signal in content.lower() for signal in captcha_signals)
        except Exception:
            return False

    async def screenshot(self, path: str):
        """Saves a screenshot of the current page for debugging."""
        if self.page:
            await self.page.screenshot(path=path)
            logging.info(f"Screenshot saved to {path}")


async def _demo():
    """Quick smoke-test: open Google and take a screenshot."""
    bot = BrowserBot(headless=False)
    try:
        await bot.launch_browser()
        await bot.navigate("https://www.google.com")
        screenshot_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'data', 'screenshot_demo.png'
        )
        await bot.screenshot(screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
    finally:
        await bot.close_browser()


if __name__ == '__main__':
    asyncio.run(_demo())
