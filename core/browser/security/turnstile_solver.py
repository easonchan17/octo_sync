import re
import math
import random
import asyncio
from typing import Any, Dict, Union, Tuple
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
from core.logger.logger_manager import LoggerManager

class TurnstileSolver:
    SPIRAL_BIAS_X, SPIRAL_BIAS_Y = 15, 15
    SPIRAL_THETA_MULTIPLIER = 2.5
    SPIRAL_RADIUS_BASE, SPIRAL_RADIUS_MULTIPLIER = 10, 0.5

    # WIDGET_OFFSET_X, WIDGET_OFFSET_Y = 50, 20
    WIDGET_OFFSET_X, WIDGET_OFFSET_Y = 0, 0
    RANDOM_OFFSET_X_RANGE = (-5, 5)
    RANDOM_OFFSET_Y_RANGE = (-1, 2)

    DEFAULT_POLLING_INTERVAL = 500
    READY_CHECK_POLLING_INTERVAL = 1000
    DEFAULT_CLICK_TIMEOUT = 5

    SUSPICIOUS_TITLE_PATTERN = re.compile(
        r"请稍候|just a moment|attention required",
        re.IGNORECASE
    )

    _JS_SCRIPT_LOCATE_WIDGET = """
        () => {
            const getValidRect = (el) => {
                let curr = el;
                while (curr && curr !== document.body) {
                    const rect = curr.getBoundingClientRect();
                    if (rect.width > 200 && rect.height > 60 && rect.x > 20 && rect.y > 20) {
                        const style = window.getComputedStyle(curr);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                            return rect;
                        }
                    }
                    curr = curr.parentElement;
                }
                return null;
            };

            const TARGET_SELECTORS = [
                'iframe[src*="challenges.cloudflare.com"]',
                'iframe[src*="turnstile"]',
                'iframe[src*="challenge-platform"]',
                'iframe[src*="cdn-cgi"]',
                '[id*="cf-chl-widget"]',
                '.cf-turnstile',
                'input[name*="turnstile"]',
                'input[name*="cf-turnstile"]'
            ];

            for (const selector of TARGET_SELECTORS) {
                const elements = document.querySelectorAll(selector);
                for (const el of elements) {
                    const rect = getValidRect(el);
                    if (rect) {
                        return {
                            x: rect.x + (rect.width / 4),
                            y: rect.y + (rect.height / 2),
                            found_via: selector,
                            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                        };
                    }
                }
            }
            return null;
        }
    """

    _JS_SCRIPT_WAIT_FOR_READY = """
        () => {
            if (!document.body) return false;

            const text = document.body.innerText.toLowerCase();
            if (text.includes("verify you are human")) {
                return true;
            }

            return false;
        }
    """

    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def _get_spiral_offset(self, attempt: int) -> Tuple[float, float]:
        if attempt == 0: return (0, 0)
        if attempt == 1: return (self.SPIRAL_BIAS_X, self.SPIRAL_BIAS_Y)

        theta = (attempt - 1) * self.SPIRAL_THETA_MULTIPLIER
        r = self.SPIRAL_RADIUS_BASE * ((attempt - 1) * self.SPIRAL_RADIUS_MULTIPLIER)
        return (self.SPIRAL_BIAS_X + r * math.cos(theta), self.SPIRAL_BIAS_Y + r * math.sin(theta))

    async def _wait_for_widget_state(
        self,
        page_context: Any,
        expect_visible: bool,
        timeout: int,
        polling: int
    ) -> Union[Dict[str, Any], bool, None]:
        execution_expression = (
            self._JS_SCRIPT_LOCATE_WIDGET
            if expect_visible
            else f"() => !(({self._JS_SCRIPT_LOCATE_WIDGET})())"
        )

        try:
            js_handle = await asyncio.wait_for(
                page_context.wait_for_function(execution_expression, timeout=0, polling=polling),
                timeout=timeout
            )
            return await js_handle.json_value() if expect_visible else True
        except (asyncio.TimeoutError, PlaywrightTimeoutError):
            return None if expect_visible else False

    async def _wait_for_widget_ready(self, page_context: Any, timeout: int) -> None:
        title = await page_context.title()
        if not self.SUSPICIOUS_TITLE_PATTERN.search(title):
            return

        self.logger.info(f">>> Suspicious title detected: {title}")
        await page_context.wait_for_function(
            self._JS_SCRIPT_WAIT_FOR_READY, timeout=timeout * 1000, polling=self.READY_CHECK_POLLING_INTERVAL
        )

    async def _perform_mouse_click(
        self,
        page_context: Any,
        x: float,
        y: float
    ) -> None:
        await page_context.bring_to_front()
        await asyncio.sleep(0.1)
        await page_context.mouse.move(x, y, steps=random.randint(1, 3))
        await asyncio.sleep(random.uniform(0.2, 0.4))
        await page_context.mouse.down()
        await asyncio.sleep(random.uniform(0.1, 0.2))
        await page_context.mouse.up()

    async def _click_at_point(self, page_context: Any, x: float, y: float, timeout: int) -> bool:
        try:
            await self._perform_mouse_click(page_context, x, y)
            return await self._wait_for_widget_state(
                page_context, expect_visible=False, timeout=timeout, polling=self.DEFAULT_POLLING_INTERVAL
            )
        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["destroyed", "navigat", "closed"]):
                self.logger.info(">>> Navigation detected during click action.")
                return True

            self.logger.error(f">>> Error clicking at point ({x:.1f}, {y:.1f}): {e}", exc_info=True)
            return False

    async def solve(self, page_context: Any, timeout: int = 3, max_attempts: int = 12) -> bool:
        try:
            self.logger.debug(">>> Starting Cloudflare solver, finding challenge container...")

            result = await self._wait_for_widget_state(
                page_context, expect_visible=True, timeout=timeout, polling=self.DEFAULT_POLLING_INTERVAL
            )

            if result is None:
                self.logger.debug(">>> Challenge container did not appear within timeout")
                return False

            self.logger.debug(f">>> Found challenge container via: {result.get('found_via', 'unknown')}")
            self.logger.debug(">>> Waiting for challenge to be ready...")
            await self._wait_for_widget_ready(page_context, timeout)
            self.logger.debug(">>> Challenge is ready, starting click attempts")

            base_x = result['x'] + self.WIDGET_OFFSET_X + random.uniform(*self.RANDOM_OFFSET_X_RANGE)
            base_y = result['y'] + self.WIDGET_OFFSET_Y + random.uniform(*self.RANDOM_OFFSET_Y_RANGE)
            self.logger.debug(f">>> Base point: ({base_x:.1f}, {base_y:.1f})")

            if base_x < 0 or base_y < 0:
                return False

            for attempt in range(max_attempts):
                offset_x, offset_y = self._get_spiral_offset(attempt)
                target_x = base_x + offset_x
                target_y = base_y + offset_y

                self.logger.debug(
                    f">>> Attempt {attempt + 1}/{max_attempts}: "
                    f"Trying to click at point ({target_x:.1f}, {target_y:.1f})"
                )

                try:
                    is_completed = await self._click_at_point(
                        page_context, target_x, target_y, self.DEFAULT_CLICK_TIMEOUT
                    )
                    if is_completed:
                        self.logger.info(f">>> Click completed successfully at attempt {attempt + 1}")
                        return True
                except asyncio.CancelledError:
                    self.logger.info(f">>> Click daemon cancelled at attempt {attempt + 1} (page likely loaded)")
                    raise

            self.logger.warning(">>> All spiral attempts failed, challenge may not be solvable")
            return False
        except Exception as e:
            self.logger.error(f">>> Solver Error: {e}", exc_info=True)
            return False