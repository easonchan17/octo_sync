import re
from enum import StrEnum
from collections import defaultdict
from typing import Dict, List, Optional, Any, Type
from urllib.parse import urlparse, urlunparse

class InterceptType(StrEnum):
    HTTP = "http"
    DOM = "dom"
    WS = "ws"
    JS = "js"

class InterceptRule:
    def __init__(
        self,
        type: str,
        pattern: Optional[str] = None,
        receiver: Optional[Type[Any]] = None,
        sender: Optional[Type[Any]] = None,
        hook_script: Optional[str] = None,
        wait_selector: Optional[str] = None,
        on_trace: Optional[Any] = None,
    ) -> None:
        self.type = InterceptType(type)
        if not self.is_dom() and not self.is_js() and pattern is None:
            raise ValueError("pattern is required for non-dom intercept rules")

        self.pattern = pattern
        self.receiver = receiver() if receiver else None
        self.sender = sender() if sender else None
        self.hook_script = hook_script
        self.wait_selector = wait_selector
        self.on_trace = on_trace

    def is_http(self) -> bool:
        return self.type == InterceptType.HTTP

    def is_dom(self) -> bool:
        return self.type == InterceptType.DOM

    def is_ws(self) -> bool:
        return self.type == InterceptType.WS

    def is_js(self) -> bool:
        return self.type == InterceptType.JS

class InterceptStrategy:
    def __init__(self) -> None:
        self.rules: Dict[InterceptType, List[InterceptRule]] = defaultdict(list)
        self.timeout: Optional[int] = None
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

        res = urlparse(url)
        normalized_url = urlunparse((res.scheme, res.netloc, res.path, res.params, res.query, ''))
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
    def from_rules(cls, policy_config: Optional[Dict[str, Any]] = None, rule_extras: Optional[List[Optional[Dict[str, Any]]]] = None) -> 'InterceptStrategy':
        if not policy_config:
            return None

        rules = policy_config.get("rules", [])
        if rule_extras:
            rules = [{**rule, **extra} if extra else rule for rule, extra in zip(rules, rule_extras)]
        debug = policy_config.get("debug", False)
        timeout = policy_config.get("timeout", 300)
        url = policy_config.get("url_template", policy_config.get("url"))

        policy = cls()
        for rule in rules:
            policy.add_rule(InterceptRule(
                type=rule.get("type"),
                pattern=rule.get("pattern"),
                receiver=rule.get("receiver"),
                sender=rule.get("sender"),
                hook_script=rule.get("hook_script"),
                wait_selector=rule.get("wait_selector"),
                on_trace=rule.get("on_trace"),
            ))
        policy.debug = debug
        policy.timeout = timeout
        policy.url = url
        return policy
