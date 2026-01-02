import re
from enum import StrEnum
from collections import defaultdict
from typing import Dict, List, Optional, Any, Type
from core.utils.parsing import normalize_url

class InterceptType(StrEnum):
    HTTP = "http"
    DOM = "dom"
    WS = "ws"

class InterceptRule:
    def __init__(
        self,
        type: str,
        pattern: Optional[str] = None,
        receiver: Optional[Type[Any]] = None,
        sender: Optional[Type[Any]] = None
    ) -> None:
        self.type = InterceptType(type)
        if not self.is_dom() and pattern is None:
            raise ValueError("pattern is required for non-dom intercept rules")

        self.pattern = pattern
        self.receiver = receiver() if receiver else None
        self.sender = sender() if sender else None

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
        self.timeout: Optional[int] = None
        self.page_delay: Optional[float] = None
        self.retry_count: Optional[int] = None
        self.debug: Optional[bool] = False
        self.url: Optional[str] = None

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
            if re.search(rule.pattern, normalized_url):
                return rule

        return None

    def get_url_patterns(self, type: InterceptType) -> List[str]:
        patterns = []
        for rule in self.rules[type]:
            if rule.pattern:
                patterns.append(rule.pattern)
        return patterns

    @classmethod
    def from_rules(cls, policy_config: Optional[Dict[str, Any]] = None) -> 'InterceptPolicy':
        if not policy_config:
            return None

        rules = policy_config.get("rules", [])
        selector = policy_config.get("selector", None)
        debug = policy_config.get("debug", False)
        timeout = policy_config.get("timeout", 60)
        page_delay = policy_config.get("page_delay", 3.5)
        retry_count = policy_config.get("retry_count", 3)
        url_template = policy_config.get("url_template")
        url = policy_config.get("url")

        policy = cls()
        for rule in rules:
            policy.add_rule(InterceptRule(
                type=rule.get("type"),
                pattern=rule.get("pattern"),
                receiver=rule.get("receiver"),
                sender=rule.get("sender"))
            )
        policy.selector = selector
        policy.debug = debug
        policy.timeout = timeout
        policy.page_delay = page_delay
        policy.retry_count = retry_count
        policy.url = url_template or url
        return policy