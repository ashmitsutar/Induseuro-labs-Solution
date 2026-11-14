import json

import pytest

from question1.agent import SupportCopilot
from question2.agent import SupportPipeline


@pytest.mark.parametrize("agent_class,budget", [(SupportCopilot, 3000), (SupportPipeline, 2500)])
@pytest.mark.parametrize("ticket_id", ["T-1001", "T-1002", "T-1003", "T-1004"])
def test_per_ticket_budget_and_call_count(agent_class, budget, ticket_id):
    agent = agent_class()
    agent.handle_ticket(ticket_id)
    assert agent.session.total_points() <= budget
    assert len(agent.session.calls) == 1


def test_q1_uses_one_call_and_retains_subscription_policy():
    agent = SupportCopilot()
    result = agent.handle_ticket("T-1091")
    assert (result.action, result.kb_article) == ("SEND_ARTICLE", "subscription-cooling-off")
    assert len(agent.session.calls) == 1
    prompt = agent.session.calls[0].prompt
    assert "subscription-cooling-off" in prompt
    assert "ORDER_SNAPSHOT:" in prompt and "END_SNAPSHOT" in prompt


def test_q2_retrieves_from_facts_not_ticket_id():
    pipe = SupportPipeline()
    ids = pipe._triage({"product_type": "physical", "damage_reported": True})
    assert "damage-replacement-7-days" in ids
    assert "returns-within-30-days" in ids
    assert "digital-license-no-refund" not in ids
    assert "damage-replacement-7-days" in pipe._retrieve(ids)


def test_q2_subscription_holdout():
    pipe = SupportPipeline()
    result = pipe.handle_ticket("T-1091")
    assert (result.action, result.kb_article) == ("SEND_ARTICLE", "subscription-cooling-off")


@pytest.mark.parametrize("draft", [
    "not json",
    json.dumps({"action": "DELETE", "kb_article": "returns-within-30-days"}),
    json.dumps({"action": "REFUND", "kb_article": "not-retrieved"}),
    json.dumps({"action": "REFUND"}),
])
def test_audit_rejects_unusable_drafts(draft):
    with pytest.raises(ValueError):
        SupportPipeline._audit(draft, ["returns-within-30-days"], {})


@pytest.mark.parametrize("days,should_pass", [(7, True), (8, False)])
def test_audit_replacement_window(days, should_pass):
    order = {"product_type": "physical", "damage_reported": True, "customized": False, "delivered_days_ago": days}
    draft = json.dumps({"action": "REPLACE", "kb_article": "damage-replacement-7-days"})
    if should_pass:
        assert SupportPipeline._audit(draft, ["damage-replacement-7-days"], order).action == "REPLACE"
    else:
        with pytest.raises(ValueError):
            SupportPipeline._audit(draft, ["damage-replacement-7-days"], order)


@pytest.mark.parametrize("days,opened,should_pass", [(30, False, True), (31, False, False), (10, True, False)])
def test_audit_physical_refund_conditions(days, opened, should_pass):
    order = {"product_type": "physical", "opened": opened, "license_revealed": False,
             "delivered_days_ago": days}
    draft = json.dumps({"action": "REFUND", "kb_article": "returns-within-30-days"})
    if should_pass:
        assert SupportPipeline._audit(draft, ["returns-within-30-days"], order).action == "REFUND"
    else:
        with pytest.raises(ValueError):
            SupportPipeline._audit(draft, ["returns-within-30-days"], order)


def test_audit_missing_facts_fail_closed():
    draft = json.dumps({"action": "REPLACE", "kb_article": "damage-replacement-7-days"})
    with pytest.raises(ValueError):
        SupportPipeline._audit(draft, ["damage-replacement-7-days"], {})


@pytest.mark.parametrize("age,should_pass", [(30, True), (31, False), (-1, False), (True, False), ("7", False)])
def test_subscription_refund_guard(age, should_pass):
    order = {"product_type": "subscription", "subscription_age_days": age}
    draft = json.dumps({"action": "REFUND", "kb_article": "subscription-cooling-off"})
    if should_pass:
        assert SupportPipeline._audit(draft, ["subscription-cooling-off"], order).action == "REFUND"
    else:
        with pytest.raises(ValueError):
            SupportPipeline._audit(draft, ["subscription-cooling-off"], order)


def test_audit_rejects_custom_replacement():
    draft = json.dumps({"action": "REPLACE", "kb_article": "damage-replacement-7-days"})
    order = {"product_type": "custom", "damage_reported": True, "customized": True,
             "delivered_days_ago": 2}
    with pytest.raises(ValueError):
        SupportPipeline._audit(draft, ["damage-replacement-7-days"], order)
