import re
from enum import StrEnum
from collections import defaultdict
from typing import Dict, List, Optional, Any
from core.utils.string_utils import normalize_url
from core.browser.components.component_factory import ComponentFactory


class InterceptType(StrEnum):
    HTTP = "http"
    DOM = "dom"
    WS = "ws"

class InterceptRule:
    def __init__(
        self,
        type: str,
        pattern: Optional[str] = None,
        receiver: Optional[str] = None,
        sender: Optional[str] = None
    ) -> None:
        self.type = InterceptType(type)
        if not self.is_dom() and pattern is None:
            raise ValueError("pattern is required for non-dom intercept rules")

        self.pattern = pattern
        self.receiver = ComponentFactory.create_inst(receiver)
        self.sender = ComponentFactory.create_inst(sender)

    def is_http(self) -> bool:
        return self.type == InterceptType.HTTP

    def is_dom(self) -> bool:
        return self.type == InterceptType.DOM

    def is_ws(self) -> bool:
        return self.type == InterceptType.WS

class InterceptPolicy:
    def __init__(self) -> None:
        self.rules: Dict[InterceptType, List[InterceptRule]] = defaultdict(list)
        self.selector: Optional[str] = None
        self.timeout: int = 60
        self.page_delay: int = 3
        self.retry_count: int = 3

    def set_timeout(self, timeout: int) -> None:
        self.timeout = timeout

    def set_page_delay(self, page_delay: int) -> None:
        self.page_delay = page_delay

    def set_retry_count(self, retry_count: int) -> None:
        self.retry_count = retry_count

    def set_selector(self, selector: str) -> None:
        self.selector = selector

    def add_rule(self, rule: InterceptRule) -> None:
        self.rules[rule.type].append(rule)

    def has_rules(self, type: InterceptType) -> bool:
        return len(self.rules[type]) > 0

    def has_receivers(self, type: InterceptType) -> bool:
        return any(rule.receiver for rule in self.rules[type])

    def has_senders(self, type: InterceptType) -> bool:
        return any(rule.sender for rule in self.rules[type])

    def find_rule(
        self,
        type: InterceptType,
        url: Optional[str] = None,
    ) -> Optional[InterceptRule]:
        rules = self.rules[type]
        if not rules:
            return None

        if not url:
            return rules[0]

        normalized_url = normalize_url(url)
        for rule in rules:
            if re.match(rule.pattern, normalized_url):
                return rule

        return None

    @classmethod
    def from_rules(cls, rules: List[dict[str, Any]], selector: Optional[str] = None) -> 'InterceptPolicy':
        policy = cls()
        if not rules:
            return policy

        for rule in rules:
            policy.add_rule(InterceptRule(
                type=rule.get("type"),
                pattern=rule.get("pattern"),
                receiver=rule.get("receiver"),
                sender=rule.get("sender"))
            )
        policy.selector = selector
        return policy


class InterceptPolicyCreator:
    def __init__(self, selector: Optional[str] = None) -> None:
        self.selector = selector

    def __call__(self, rules: List[dict[str, Any]]) -> InterceptPolicy:
        return InterceptPolicy.from_rules(rules, selector=self.selector)