#!/usr/bin/env python3
"""
Debug script to manually trace through the reward calculation
for the task_medium case with:
  fraud=false, type=legitimate, act=allow, conf=0.90

This is the _case_legitimate_new_device() case (ATO-004)
"""

import sys
sys.path.append('/Users/khushikumari/Documents/fraud-investigation-env')

from server.grader import _grade_task2, _match_signals, _fuzzy_match, _safe_score
from models import FraudAction

# The TRUTH from _case_legitimate_new_device()
truth = {
    "is_fraud": False,
    "fraud_type": "legitimate",
    "attack_vector": "none",
    "key_signals": ["support_call_context", "same_city",
                    "normal_time", "usual_merchant"],
    "action": "allow",
    "acceptable_actions": ["allow"],
    "regulatory_action": "none"
}

# The ACTION submitted by the agent (simulating what you submitted)
agent_action = FraudAction(
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
    reasoning="The user received a new iPhone 15 after reporting their old phone stolen. "
              "Login occurred from Mumbai at normal evening time. Transaction amount (₹3200) is "
              "within usual range for Amazon purchases. All signals align with legitimate device replacement."
)

print("="*70)
print("DETAILED REWARD CALCULATION FOR task_medium CASE")
print("="*70)
print()

print("TRUTH:")
print(f"  is_fraud: {truth['is_fraud']}")
print(f"  fraud_type: {truth['fraud_type']}")
print(f"  attack_vector: {truth['attack_vector']}")
print(f"  action: {truth['action']}")
print(f"  key_signals: {truth['key_signals']}")
print()

print("AGENT SUBMISSION:")
print(f"  is_fraud: {agent_action.is_fraud}")
print(f"  fraud_type: {agent_action.fraud_type}")
print(f"  attack_vector: {agent_action.attack_vector}")
print(f"  action: {agent_action.action}")
print(f"  evidence: {agent_action.evidence}")
print(f"  confidence: {agent_action.confidence}")
print(f"  reasoning: {agent_action.reasoning[:80]}...")
print()

print("="*70)
print("STEP-BY-STEP GRADING (from _grade_task2):")
print("="*70)
print()

reward = 0.0
feedback = []

# Step 1: Fraud/Legitimate Decision Match
print("1. FRAUD DECISION MATCH (+0.25 max):")
if agent_action.is_fraud == truth["is_fraud"]:
    reward += 0.25
    feedback.append("✅ CORRECT: Fraud/legitimate decision (+0.25)")
    print(f"   Agent is_fraud={agent_action.is_fraud} == Truth is_fraud={truth['is_fraud']}")
    print(f"   → +0.25")
elif not agent_action.is_fraud and truth["is_fraud"]:
    reward -= 0.10
    feedback.append("❌ MISSED: This was fraud (-0.10)")
    print(f"   MISSED FRAUD: -0.10")
else:
    print(f"   WRONG: Flagged legitimate")

print(f"   Running total: {reward:.2f}")
print()

# Step 2: Fraud Type Match
print("2. FRAUD TYPE MATCH (+0.10 max):")
if agent_action.fraud_type == truth["fraud_type"]:
    reward += 0.10
    feedback.append("✅ CORRECT: Fraud type (+0.10)")
    print(f"   Agent fraud_type={agent_action.fraud_type} == Truth fraud_type={truth['fraud_type']}")
    print(f"   → +0.10")
elif agent_action.fraud_type in truth.get("related_types", []):
    reward += 0.07
    feedback.append("⚠️  PARTIAL: Close fraud type (+0.07)")
    print(f"   PARTIAL MATCH: +0.07")

print(f"   Running total: {reward:.2f}")
print()

# Step 3: Attack Vector Match (fuzzy)
print("3. ATTACK VECTOR MATCH (+0.20 max, fuzzy matching):")
vector_match = _fuzzy_match(agent_action.attack_vector, truth["attack_vector"])
print(f"   _fuzzy_match('{agent_action.attack_vector}', '{truth['attack_vector']}') = {vector_match}")
if vector_match:
    reward += 0.20
    feedback.append("✅ CORRECT: Attack vector (+0.20)")
    print(f"   → +0.20")
elif agent_action.attack_vector in truth.get("related_vectors", []):
    reward += 0.08
    feedback.append("⚠️  PARTIAL: Related attack vector (+0.08)")
    print(f"   → +0.08 (partial)")

print(f"   Running total: {reward:.2f}")
print()

# Step 4: Evidence/Signal Matching
print("4. EVIDENCE SIGNAL MATCHING (+0.25 max):")
matched = _match_signals(agent_action.evidence, truth["key_signals"])
signal_score = matched / max(len(truth["key_signals"]), 1)
signal_reward = 0.25 * signal_score
reward += signal_reward
print(f"   Agent evidence: {agent_action.evidence}")
print(f"   Truth key_signals: {truth['key_signals']}")
print(f"   Matched signals: {matched} out of {len(truth['key_signals'])}")
print(f"   Signal score: {signal_score:.2f} ({matched}/{len(truth['key_signals'])})")
print(f"   Signal reward: 0.25 × {signal_score:.2f} = {signal_reward:.2f}")

print(f"   Running total: {reward:.2f}")
print()

# Step 5: Action Match
print("5. ACTION MATCH (+0.20 max):")
if agent_action.action == truth["action"]:
    reward += 0.20
    feedback.append("✅ CORRECT: Action (+0.20)")
    print(f"   Agent action={agent_action.action} == Truth action={truth['action']}")
    print(f"   → +0.20")
elif agent_action.action in truth.get("acceptable_actions", []):
    reward += 0.10
    feedback.append("⚠️  PARTIAL: Acceptable action (+0.10)")
    print(f"   → +0.10 (acceptable)")

print(f"   Running total: {reward:.2f}")
print()

# Step 6: Fraud penalty (if agent says fraud when it's not)
print("6. FALSE POSITIVE PENALTY (-0.10 max):")
if agent_action.is_fraud and not truth["is_fraud"]:
    reward -= 0.10
    feedback.append("❌ FALSE POSITIVE: Flagged legitimate (-0.10)")
    print(f"   PENALTY APPLIED: -0.10")
else:
    print(f"   No penalty (is_fraud matches truth)")

print(f"   Running total: {reward:.2f}")
print()

# Step 7: Reasoning quality
print("7. REASONING QUALITY (+0.10 max, based on word count):")
reasoning_words = len(agent_action.reasoning.split())
reasoning_score = min(reasoning_words / 100, 1.0)
reasoning_reward = 0.10 * reasoning_score
reward += reasoning_reward
print(f"   Reasoning word count: {reasoning_words}")
print(f"   Reasoning score: min({reasoning_words}/100, 1.0) = {reasoning_score:.2f}")
print(f"   Reasoning reward: 0.10 × {reasoning_score:.2f} = {reasoning_reward:.2f}")

print(f"   Running total: {reward:.2f}")
print()

print("="*70)
print("RAW REWARD BEFORE CAPPING:")
print(f"  {reward:.4f}")
print()

# Now apply the capping function
safe_reward = _safe_score(reward)
print("="*70)
print("APPLYING _safe_score() FUNCTION:")
print(f"  Round to 2 decimals: {round(reward, 2)}")

if round(reward, 2) >= 0.99:
    print(f"  Score >= 0.99, so capping to 0.98")
    safe_reward_expected = 0.98
elif round(reward, 2) <= 0.01:
    print(f"  Score <= 0.01, so setting to 0.02")
    safe_reward_expected = 0.02
else:
    safe_reward_expected = round(reward, 2)
    print(f"  Score is in normal range, keeping as {safe_reward_expected}")

print()
print(f"FINAL SAFE REWARD: {safe_reward}")
print(f"EXPECTED (0.98 cap): {safe_reward_expected}")
print()

# Also check environment.py's additional capping
env_capped = max(0.02, min(0.98, safe_reward))
print("="*70)
print("ADDITIONAL CAPPING IN environment.py (line 105):")
print(f"  max(0.02, min(0.98, {safe_reward}))")
print(f"  = {env_capped}")
print()

print("="*70)
print("SUMMARY:")
print("="*70)
print(f"Raw reward: {reward:.4f}")
print(f"After _safe_score(): {safe_reward}")
print(f"After environment.py capping: {env_capped}")
print()
print("FEEDBACK:")
for fb in feedback:
    print(f"  {fb}")

