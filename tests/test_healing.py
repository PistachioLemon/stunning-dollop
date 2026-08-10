from nova.healing import HealthFinding, RepairHandler, RepairRecipe, RiskLevel, SelfHealingEngine


def unhealthy(signature="service_down"):
    return HealthFinding("issue-1", "demo", signature, False)


def test_low_risk_auto_heals():
    state = {"up": False}
    engine = SelfHealingEngine()
    engine.register_probe("demo", lambda: unhealthy())
    engine.register_recipe(
        RepairRecipe("restart", "service_down", "restart", RiskLevel.LOW),
        RepairHandler(lambda _: state.__setitem__("up", True), lambda _: state["up"]),
    )
    report = engine.run_cycle()
    assert report["repairs"][0]["status"] == "healed"


def test_high_risk_requires_approval():
    called = {"n": 0}
    engine = SelfHealingEngine(auto_risk=RiskLevel.LOW)
    engine.register_probe("demo", lambda: unhealthy("firmware_bad"))
    engine.register_recipe(
        RepairRecipe("flash", "firmware_bad", "flash", RiskLevel.HIGH),
        RepairHandler(lambda _: called.__setitem__("n", called["n"] + 1), lambda _: True),
    )
    report = engine.run_cycle()
    assert report["repairs"][0]["status"] == "approval_required"
    assert called["n"] == 0


def test_failed_verification_rolls_back():
    state = {"rolled_back": False}
    engine = SelfHealingEngine()
    engine.register_probe("demo", lambda: unhealthy())
    engine.register_recipe(
        RepairRecipe("restart", "service_down", "restart", RiskLevel.LOW),
        RepairHandler(lambda _: None, lambda _: False, lambda _: state.__setitem__("rolled_back", True)),
    )
    report = engine.run_cycle()
    assert report["repairs"][0]["status"] == "verification_failed"
    assert report["repairs"][0]["rolled_back"] is True
    assert state["rolled_back"] is True


def test_sandbox_is_fail_closed():
    engine = SelfHealingEngine(auto_risk=RiskLevel.MEDIUM)
    engine.register_probe("demo", lambda: unhealthy("dependency_bad"))
    engine.register_recipe(
        RepairRecipe("reinstall", "dependency_bad", "reinstall", RiskLevel.MEDIUM, sandbox_required=True),
        RepairHandler(lambda _: None, lambda _: True),
    )
    report = engine.run_cycle()
    assert report["repairs"][0]["status"] == "sandbox_failed"
