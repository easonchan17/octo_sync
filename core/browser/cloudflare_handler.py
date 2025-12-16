import asyncio
from typing import Any
from bs4 import BeautifulSoup
from core.logger.logger_manager import LoggerManager


class CloudflareHandler:
    DOMAIN = "https://challenges.cloudflare.com"

    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def is_challenge(self, page_content: str) -> bool:
        soup = BeautifulSoup(page_content, 'html.parser')
        title = soup.title.string if soup.title else ""
        text = soup.get_text()

        if "Just a moment" in title:
            return True
        if "Verifying you are human" in text or "needs to review the security" in text:
            return True

        return False

    async def wait_for_verification(self, page_context: Any, max_wait_time: int, check_interval: int = 3) -> None:
        current_content = await page_context.content()
        if not self.is_challenge(current_content):
            return

        self.logger.info(f"Waiting for manual verification (max {max_wait_time}s)...")
        self.logger.info("Please complete the verification in the browser window")

        check_count = 0
        max_checks = (max_wait_time // check_interval) if max_wait_time > 0 else 300

        while check_count < max_checks:
            await asyncio.sleep(check_interval)
            check_count += 1

            try:
                current_content = await page_context.content()

                if not self.is_challenge(current_content):
                    self.logger.info("Verification completed successfully")
                    await page_context.wait_for_load_state("networkidle", timeout=max_wait_time*1000)
                    return

                success_element = page_context.locator("#challenge-success-text")
                if await success_element.count() != 1:
                    continue

                is_visible = await success_element.first.is_visible()
                if not is_visible:
                    continue

                self.logger.info("Verification success element detected, waiting for redirect...")
                await page_context.wait_for_url(
                    lambda url: not url.startswith(self.DOMAIN),
                    timeout=max_wait_time*1000
                )
                await page_context.wait_for_load_state("networkidle", timeout=max_wait_time*1000)
                self.logger.info("Verification completed and redirected")
                await asyncio.sleep(check_interval)
                return

            except Exception as e:
                self.logger.debug(f"Error checking verification status: {e}")

        self.logger.warning(f"Verification wait timeout after {max_wait_time}s, proceeding anyway")
