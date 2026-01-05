import asyncio
import math
import random
from typing import Any, Dict, Union, Tuple
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
from core.logger.logger_manager import LoggerManager

class TurnstileSolver:
    SUSPICIOUS_TITLES = [
        "请稍候",
        "just a moment",
        "attention required"
    ]

    CHALLENGE_KEYWORDS = [
        "验证您是否是真人",
        "验证您是真人",
        "请完成以下操作",
        "verifying you are human",
        "needs to review the security",
        "cf-turnstile-response"
    ]

    SPIRAL_BIAS_X = 15
    SPIRAL_BIAS_Y = 15
    SPIRAL_THETA_MULTIPLIER = 2.5
    SPIRAL_RADIUS_BASE = 10
    SPIRAL_RADIUS_MULTIPLIER = 0.5

    WIDGET_OFFSET_X = 50
    WIDGET_OFFSET_Y = 20

    RANDOM_OFFSET_X_RANGE = (-5, 5)
    RANDOM_OFFSET_Y_RANGE = (-1, 2)

    DEFAULT_POLLING_INTERVAL = 500
    READY_CHECK_POLLING_INTERVAL = 1000
    DEFAULT_CLICK_TIMEOUT = 5

    _JS_SCRIPT_LOCATE_WIDGET = """
        () => {
            const TARGET_SELECTORS = [
                'input[name*="turnstile"]',
                'input[name*="cf-turnstile"]',
                '[id*="cf-chl-widget"]',
                '[id*="cf-chl"]',
                'iframe[src*="challenges.cloudflare.com"]',
                'iframe[src*="turnstile"]',
                'iframe[src*="challenge-platform"]',
                'iframe[src*="cdn-cgi"]'
            ];

            for (const selector of TARGET_SELECTORS) {
                try {
                    const element = document.querySelector(selector);
                    if (element) {
                        let container = element;
                        let parent = element.parentElement;

                        while (parent && parent !== document.body) {
                            const rect = parent.getBoundingClientRect();
                            if (rect.width > 100 && rect.height > 50) {
                                container = parent;
                                break;
                            }
                            parent = parent.parentElement;
                        }

                        const rect = container.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            return {
                                x: rect.x,
                                y: rect.y + rect.height / 2,
                                found_via: selector,
                                rect: {
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height
                                }
                            };
                        }
                    }
                } catch (e) {}
            }
            return null;
        }
    """

    _JS_SCRIPT_CHECK_KEYWORDS = """
        (keywords) => {
            if (!document.body) return false;

            const text = document.body.innerText.toLowerCase();
            return keywords.some(k => text.includes(k));
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

    async def _wait_for_widget_state(
        self,
        page_context: Any,
        expect_visible: bool,
        timeout: int,
        polling: int = DEFAULT_POLLING_INTERVAL
    ) -> Union[Dict[str, Any], bool, None]:

        execution_expression = (
            self._JS_SCRIPT_LOCATE_WIDGET
            if expect_visible
            else f"() => !(({self._JS_SCRIPT_LOCATE_WIDGET})())"
        )

        js_handle = await page_context.wait_for_function(
            execution_expression,
            timeout=timeout * 1000,
            polling=polling
        )
        return await js_handle.json_value() if expect_visible else True

    async def _is_challenge(
        self,
        page_context: Any,
        timeout: int,
        polling: int = DEFAULT_POLLING_INTERVAL
    ) -> bool:
        title = (await page_context.title()).lower()
        if not any(keyword in title for keyword in self.SUSPICIOUS_TITLES):
            return False

        self.logger.info(f">>> Suspicious title detected: {title}")
        try:
            await page_context.wait_for_function(
                self._JS_SCRIPT_CHECK_KEYWORDS,
                arg=self.CHALLENGE_KEYWORDS,
                timeout=timeout * 1000,
                polling=polling
            )
            self.logger.info(">>> Challenge confirmed by keywords")
            return True
        except Exception as e:
            self.logger.warning(f">>> Challenge detection failed: {e}")
            return False

    async def _click_at_point(
        self,
        page_context: Any,
        x: float,
        y: float,
        timeout: int = DEFAULT_CLICK_TIMEOUT
    ) -> bool:
        try:
            await page_context.mouse.move(x, y, steps=random.randint(1, 3))
            await asyncio.sleep(random.uniform(0.2, 0.4))
            await page_context.mouse.down()
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await page_context.mouse.up()
            return await self._wait_for_widget_state(page_context, expect_visible=False, timeout=timeout)
        except PlaywrightTimeoutError:
            return False
        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["destroyed", "navigat", "closed"]):
                self.logger.info(">>> Navigation detected during click action.")
                return True

            self.logger.error(f">>> Error clicking at point ({x:.1f}, {y:.1f}): {e}", exc_info=True)
            return False

    def _get_spiral_offset(self, attempt: int) -> Tuple[float, float]:
        if attempt == 0:
            return (0, 0)

        if attempt == 1:
            return (self.SPIRAL_BIAS_X, self.SPIRAL_BIAS_Y)

        theta = (attempt - 1) * self.SPIRAL_THETA_MULTIPLIER
        r = self.SPIRAL_RADIUS_BASE * ((attempt - 1) * self.SPIRAL_RADIUS_MULTIPLIER)

        x = self.SPIRAL_BIAS_X + (r * math.cos(theta))
        y = self.SPIRAL_BIAS_Y + (r * math.sin(theta))
        return (x, y)

    async def _try_click_checkbox(
        self,
        page_context: Any,
        timeout: int,
        max_attempts: int
    ) -> bool:
        try:
            self.logger.info(">>> Starting Cloudflare solver, finding challenge container...")

            result = await self._wait_for_widget_state(
                page_context, expect_visible=True, timeout=timeout
            )

            if not result:
                self.logger.warning(">>> Challenge container did not appear within timeout")
                return False

            self.logger.info(f">>> Found challenge container via: {result.get('found_via', 'unknown')}")
            self.logger.info(">>> Waiting for challenge to be ready...")
            await page_context.wait_for_function(
                self._JS_SCRIPT_WAIT_FOR_READY,
                timeout=timeout * 1000,
                polling=self.READY_CHECK_POLLING_INTERVAL
            )
            self.logger.info(">>> Challenge is ready, starting click attempts")

            base_x = result['x'] + self.WIDGET_OFFSET_X + random.uniform(*self.RANDOM_OFFSET_X_RANGE)
            base_y = result['y'] + self.WIDGET_OFFSET_Y + random.uniform(*self.RANDOM_OFFSET_Y_RANGE)
            self.logger.info(f">>> Base point: ({base_x:.1f}, {base_y:.1f})")

            for attempt in range(max_attempts):
                offset_x, offset_y = self._get_spiral_offset(attempt)
                target_x = base_x + offset_x
                target_y = base_y + offset_y

                self.logger.info(
                    f">>> Attempt {attempt + 1}/{max_attempts}: "
                    f"Trying to click at point ({target_x:.1f}, {target_y:.1f})"
                )

                is_completed = await self._click_at_point(page_context, target_x, target_y)

                if is_completed:
                    self.logger.info(f">>> Click completed successfully at attempt {attempt + 1}")
                    return True

            self.logger.warning(">>> All spiral attempts failed, challenge may not be solvable")
            return False
        except Exception as e:
            self.logger.error(f">>> Solver Error: {e}", exc_info=True)
            return False

    async def solve(
        self,
        page_context: Any,
        timeout: int,
        max_attempts: int = 12
    ) -> bool:
        if not await self._is_challenge(page_context, timeout=timeout):
            self.logger.info(">>> No challenge detected")
            return True

        return await self._try_click_checkbox(
            page_context,
            timeout=timeout,
            max_attempts=max_attempts
        )
