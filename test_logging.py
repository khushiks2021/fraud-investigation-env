#!/usr/bin/env python3
"""
Test script to debug the reward calculation with full logging
Run a single task_medium legitimate case and trace the reward
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import FraudEnvClient
from models import FraudAction

print("\n" + "="*70, flush=True)
print("TEST: task_medium - Legitimate New Device Case", flush=True)
print("="*70 + "\n", flush=True)

# Connect to server
try:
    env = FraudEnvClient(base_url="http://localhost:8000")
    print("[TEST] Connected to server\n", flush=True)
except Exception as e:
    print(f"[ERROR] Cannot connect: {e}", flush=True)
    sys.exit(1)

# Reset for task_medium
print("[TEST] Resetting environment for task_medium...\n", flush=True)
obs1 = env.reset(task="task_medium")
print(f"[TEST] Case ID: {obs1.case_id}\n", flush=True)

# Step 1: investigate
print("[TEST] Step 1: Submitting investigate action...\n", flush=True)
hyp = FraudAction(
    action_type="investigate",
    is_fraud=False,
    fraud_type="legitimate",
    confidence=0.5,
    evidence=[],
    attack_vector="none",
    action="allow",
    flagged_accounts=[],
    hub_account=None,
    regulatory_action="none",
    reasoning="Investigating..."
)

obs2 = env.step(hyp)
print(f"[TEST] Step 1 complete. Step 1 reward: {obs2.reward}\n", flush=True)

# Wait a bit
import time
time.sleep(1)

# Step 2: submit_decision (PERFECT SUBMISSION)
print("[TEST] Step 2: Submitting final decision...\n", flush=True)
final = FraudAction(
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

print("[TEST] Calling env.step()...\n", flush=True)
result = env.step(final)

print("\n" + "="*70, flush=True)
print("[TEST] FINAL RESULT:", flush=True)
print(f"  result.reward: {result.reward}", flush=True)
print(f"  result.reward type: {type(result.reward)}", flush=True)
print(f"  result.reward (raw): {result.reward:.6f}", flush=True)
print(f"  result.reward (.2f): {result.reward:.2f}", flush=True)
print("="*70 + "\n", flush=True)

env.close()

# Verify
if result.reward == 0.98:
    print("[✓] PASS: Reward correctly capped to 0.98", flush=True)
elif result.reward >= 0.985:
    print(f"[⚠] WARNING: Reward {result.reward:.6f} rounds to {result.reward:.2f}", flush=True)
    print("[!] This suggests the capping might not be applied", flush=True)
else:
    print(f"[!] Unexpected reward: {result.reward:.6f}", flush=True)

