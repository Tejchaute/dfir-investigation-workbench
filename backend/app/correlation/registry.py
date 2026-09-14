from app.correlation.rules import (
    CorrelationRule,
    EvtxPrefetchRule,
    LnkEvtxRule,
    NtfsEvtxRule,
    RegistryEvtxRule,
)


class CorrelationRuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, CorrelationRule] = {}

    def register(self, rule: CorrelationRule) -> None:
        if rule.rule_id in self._rules:
            raise ValueError(f"Correlation rule {rule.rule_id} is already registered")
        self._rules[rule.rule_id] = rule

    def rules(self) -> tuple[CorrelationRule, ...]:
        return tuple(self._rules[key] for key in sorted(self._rules))


correlation_rule_registry = CorrelationRuleRegistry()
for _rule in (EvtxPrefetchRule(), LnkEvtxRule(), NtfsEvtxRule(), RegistryEvtxRule()):
    correlation_rule_registry.register(_rule)
