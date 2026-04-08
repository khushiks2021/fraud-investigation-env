#!/usr/bin/env python3
"""
Debug script to instrument the grader and environment to see exactly
what reward values are being calculated and returned.
"""

import sys
sys.path.append('/Users/khushikumari/Documents/fraud-investigation-env')

# Monkey-patch the grader to log
original_safe_score = None
original_grade = None

def patched_safe_score(reward: float) -> float:
    score = round(reward, 2)
    print(f"  [_safe_score] Input: {reward:.6f}, Rounded: {score}, ", end="", file=sys.stderr)

    if score >= 0.99:
        score = 0.98
        print(f"CAPPED to 0.98", file=sys.stderr)
    elif score <= 0.01:
        score = 0.02
        print(f"FLOORED to 0.02", file=sys.stderr)
    else:
        print(f"KEPT as {score}", file=sys.stderr)

    print(f"  [_safe_score] Output: {score:.6f}", file=sys.stderr)
    return score

def patched_grade(action, truth, task):
    print(f"\n[GRADE] Task: {task}", file=sys.stderr)
    from server.grader import _grade_task1, _grade_task2, _grade_task3

    if task == "task_easy":
        reward, feedback = _grade_task1(action, truth)
    elif task == "task_medium":
        reward, feedback = _grade_task2(action, truth)
    elif task == "task_hard":
        reward, feedback = _grade_task3(action, truth)
    else:
        reward, feedback = 0.02, "Unknown task"

    print(f"[GRADE] Returned reward from grader: {reward:.6f}", file=sys.stderr)
    return reward, feedback

# Apply patches
from server import grader
grader._safe_score = patched_safe_score
original_safe_score = grader._safe_score

# Patch the environment step function too
def patched_env_step(self, action):
    print(f"\n[ENV.STEP] Starting step {self.step_count + 1}", file=sys.stderr)

    if self.is_done:
        raise RuntimeError("Episode is done. Call reset() to start a new one.")

    if self.current_case is None:
        raise RuntimeError("No active episode. Call reset() first.")

    self.step_count += 1
    full = self._full_obs

    # Step 1: investigate
    if action.action_type == "investigate" and self.step_count == 1:
        print(f"[ENV.STEP] Action is 'investigate', step 1", file=sys.stderr)
        return type(self).__bases__[0].step(self, action)  # Call original

    # Final step: grade the decision
    print(f"[ENV.STEP] Action is 'submit_decision', grading...", file=sys.stderr)
    truth = self.current_case["truth"]
    reward, feedback = grader.grade(action, truth, self.current_task)

    print(f"[ENV.STEP] Reward from grade(): {reward:.6f}", file=sys.stderr)

    reward = max(0.02, min(0.98, reward))
    print(f"[ENV.STEP] After capping (max(0.02, min(0.98, {reward}))): {reward:.6f}", file=sys.stderr)

    self.total_reward += reward
    self.is_done = True

    from models import FraudObservation
    obs = FraudObservation(
        case_id=full.case_id,
        task=full.task,
        step=self.step_count,
        account=full.account,
        transactions=full.transactions,
        login_events=full.login_events,
        account_events=full.account_events,
        linked_accounts=full.linked_accounts,
        additional_signals=full.additional_signals,
        reward=reward,
        done=True,
        feedback=feedback
    )
    print(f"[ENV.STEP] FraudObservation created with reward: {obs.reward:.6f}", file=sys.stderr)

    return obs

from server.environment import FraudEnvironment
FraudEnvironment.step = patched_env_step

# Now run a test episode
print("=" * 70, file=sys.stderr)
print("STARTING DEBUG EPISODE WITH INSTRUMENTATION", file=sys.stderr)
print("=" * 70, file=sys.stderr)

from client import FraudEnvClient
from models import FraudAction

# Create client (must have server running!)
try:
    client = FraudEnvClient(base_url="http://localhost:8000")
    print("Connected to server", file=sys.stderr)
except Exception as e:
    print(f"ERROR: Cannot connect - {e}", file=sys.stderr)
    print("Make sure the fraud investigation server is running on port 8000", file=sys.stderr)
    sys.exit(1)

# Run task_medium case
task = "task_medium"
print(f"\nRunning task: {task}", file=sys.stderr)

obs1 = client.reset(task=task)
print(f"Reset done. Case: {obs1.case_id}", file=sys.stderr)

# Step 1: investigate
hyp = FraudAction(
    action_type="investigate",
    is_fraud=False,
    fraud_type="legitimate",
    confidence=0.9,
    evidence=[],
    attack_vector="none",
    action="allow",
    flagged_accounts=[],
    hub_account=None,
    regulatory_action="none",
    reasoning="Investigating..."
)

print(f"\nSubmitting investigate action...", file=sys.stderr)
obs2 = client.step(hyp)
print(f"Step 1 reward from obs: {obs2.reward:.6f}", file=sys.stderr)

# Step 2: submit_decision
final = FraudAction(
    action_type="submit_decision",
    is_fraud=False,
    fraud_type="legitimate",
    confidence=0.9,
    evidence=["support_call_context", "same_city", "normal_time", "usual_merchant"],
    attack_vector="none",
    action="allow",
    flagged_accounts=[],
    hub_account=None,
    regulatory_action="none",
    reasoning="The user received a new iPhone 15 after reporting their old phone stolen. Login was from Mumbai at normal time."
)

print(f"\nSubmitting final decision...", file=sys.stderr)
result = client.step(final)
print(f"\n[FINAL] Step 2 reward from obs: {result.reward:.6f}", file=sys.stderr)
print(f"[FINAL] Formatted with .2f: {result.reward:.2f}", file=sys.stderr)

client.close()

print("\n" + "=" * 70, file=sys.stderr)
print("DEBUG EPISODE COMPLETE", file=sys.stderr)
print("=" * 70, file=sys.stderr)

