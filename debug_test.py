#!/usr/bin/env python3
from server.case_generator import _case_device_takeover, _case_legitimate_new_device
from models import FraudAction
from server.grader import _grade_task2

print("\n" + "="*80)
print("TEST 1: ATO-001 Device Takeover (FRAUD) with WRONG answer (saying legitimate)")
print("="*80)

case1 = _case_device_takeover()
obs1 = case1["observation"]
truth1 = case1["truth"]

print(f"Case: {obs1.case_id}")
print(f"Truth: is_fraud={truth1['is_fraud']}, type={truth1['fraud_type']}, action={truth1['action']}")

# Wrong answer
action1 = FraudAction(
    action_type="submit_decision",
    is_fraud=False,
    fraud_type="legitimate",
    confidence=0.90,
    evidence=["support_call_context"],
    attack_vector="none",
    action="allow",
    flagged_accounts=[],
    hub_account=None,
    regulatory_action="none",
    reasoning="Thinking this is legitimate..."
)

print("\nGrading WRONG answer...")
reward1, feedback1 = _grade_task2(action1, truth1)
print(f"\nFinal reward: {reward1:.6f} (formatted: {reward1:.2f})")

print("\n" + "="*80)
print("TEST 2: ATO-004 Legitimate (NO FRAUD) with CORRECT answer")
print("="*80)

case2 = _case_legitimate_new_device()
obs2 = case2["observation"]
truth2 = case2["truth"]

print(f"Case: {obs2.case_id}")
print(f"Truth: is_fraud={truth2['is_fraud']}, type={truth2['fraud_type']}, action={truth2['action']}")

# CORRECT answer - perfect match
action2 = FraudAction(
    action_type="submit_decision",
    is_fraud=False,
    fraud_type="legitimate",
    confidence=0.90,
    evidence=["support_call_context", "same_city", "normal_time", "usual_merchant"],
    attack_vector="none",
    action="allow",
    flagged_accounts=[],
    hub_account=None,
    regulatory_action="none",
    reasoning="The user received a new iPhone 15 after reporting their old phone stolen. Login occurred from Mumbai at normal evening time. Transaction amount (₹3200) is within usual range for Amazon purchases. All signals align with legitimate device replacement."
)

print("\nGrading CORRECT answer...")
reward2, feedback2 = _grade_task2(action2, truth2)
print(f"\nFinal reward: {reward2:.6f} (formatted: {reward2:.2f})")

print("\n" + "="*80)

