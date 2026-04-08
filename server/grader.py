from models import FraudAction


def _match_signals(agent_signals: list[str], truth_signals: list[str]) -> int:
    matched = 0

    for truth_sig in truth_signals:
        truth_words = set(truth_sig.lower().replace("_", " ").split())

        for agent_sig in agent_signals:
            agent_words = set(agent_sig.lower().replace("_", " ").split())

            overlap = truth_words & agent_words
            coverage = len(overlap) / max(len(truth_words), 1)

            if coverage >= 0.5:
                matched += 1
                break

    return matched


def _fuzzy_match(a: str, b: str) -> bool:
    if not a or not b:
        return False

    words_a = set(a.lower().replace("_", " ").split())
    words_b = set(b.lower().replace("_", " ").split())

    overlap = words_a & words_b
    coverage = len(overlap) / max(len(words_b), 1)

    return coverage >= 0.5


def _safe_score(reward: float) -> float:
    score = reward

    # 🔥 HARD clamp BEFORE any rounding
    if score >= 0.99:
        score = 0.98
    elif score <= 0.01:
        score = 0.02

    return round(score, 2)


def grade(action: FraudAction, truth: dict, task: str) -> tuple[float, str]:
    if task == "task_easy":
        return _grade_task1(action, truth)
    elif task == "task_medium":
        return _grade_task2(action, truth)
    elif task == "task_hard":
        return _grade_task3(action, truth)

    return 0.02, "Unknown task"


def _grade_task1(action: FraudAction, truth: dict) -> tuple[float, str]:
    reward = 0.0
    feedback = []

    if action.is_fraud == truth["is_fraud"]:
        reward += 0.30
        feedback.append("CORRECT: Fraud/legitimate decision (+0.30)")
    elif not action.is_fraud and truth["is_fraud"]:
        reward -= 0.10
        feedback.append("MISSED: This was fraud (-0.10)")
    else:
        feedback.append("WRONG: Flagged legitimate")

    if action.fraud_type == truth["fraud_type"]:
        reward += 0.15
        feedback.append("CORRECT: Fraud type (+0.15)")
    elif action.fraud_type in truth.get("related_types", []):
        reward += 0.07
        feedback.append("PARTIAL: Close fraud type (+0.07)")

    matched = _match_signals(action.evidence, truth["key_signals"])
    signal_score = matched / max(len(truth["key_signals"]), 1)
    reward += 0.25 * signal_score

    if action.action == truth["action"]:
        reward += 0.20
    elif action.action in truth.get("acceptable_actions", []):
        reward += 0.10

    if action.is_fraud and not truth["is_fraud"]:
        reward -= 0.10

    expected_confidence = 0.9 if truth["is_fraud"] else 0.1
    confidence_score = 1.0 - abs(action.confidence - expected_confidence)
    reward += 0.10 * confidence_score

    score = _safe_score(reward)
    return score, "\n".join(feedback)


def _grade_task2(action: FraudAction, truth: dict) -> tuple[float, str]:
    reward = 0.0
    feedback = []

    if action.is_fraud == truth["is_fraud"]:
        reward += 0.25
    elif not action.is_fraud and truth["is_fraud"]:
        reward -= 0.10
        feedback.append("MISSED: This was fraud (-0.10)")

    if action.fraud_type == truth["fraud_type"]:
        reward += 0.10
        feedback.append("CORRECT: Fraud type (+0.10)")

    if _fuzzy_match(action.attack_vector, truth["attack_vector"]):
        reward += 0.20
        feedback.append("CORRECT: Attack vector (+0.20)")
    elif action.attack_vector in truth.get("related_vectors", []):
        reward += 0.08
        feedback.append("PARTIAL: Related attack vector (+0.08)")

    matched = _match_signals(action.evidence, truth["key_signals"])
    signal_score = matched / max(len(truth["key_signals"]), 1)
    reward += 0.25 * signal_score

    if action.action == truth["action"]:
        reward += 0.20
    elif action.action in truth.get("acceptable_actions", []):
        reward += 0.10

    if action.is_fraud and not truth["is_fraud"]:
        reward -= 0.10

    reasoning_score = min(len(action.reasoning.split()) / 100, 1.0)
    reward += 0.10 * reasoning_score

    score = _safe_score(reward)
    return score, "\n".join(feedback)


def _grade_task3(action: FraudAction, truth: dict) -> tuple[float, str]:
    reward = 0.0
    feedback = []

    if action.is_fraud == truth["is_fraud"]:
        reward += 0.20
    elif not action.is_fraud and truth["is_fraud"]:
        reward -= 0.10
        feedback.append("MISSED: This was fraud (-0.10)")

    if action.fraud_type == truth["fraud_type"]:
        reward += 0.15

    truth_accounts = set(truth.get("network_accounts", []))
    agent_accounts = set(action.flagged_accounts)

    if truth_accounts:
        found = truth_accounts & agent_accounts
        precision = len(found) / max(len(agent_accounts), 1)
        recall = len(found) / max(len(truth_accounts), 1)
        f1 = 2 * precision * recall / max(precision + recall, 0.01)
        reward += 0.25 * f1

    if action.hub_account == truth.get("hub_account"):
        reward += 0.15

    if action.regulatory_action == truth["regulatory_action"]:
        reward += 0.15
    elif truth["regulatory_action"] != "none" and action.regulatory_action != "none":
        reward += 0.07

    if action.is_fraud and not truth["is_fraud"]:
        reward -= 0.10

    reasoning_score = min(len(action.reasoning.split()) / 150, 1.0)
    reward += 0.10 * reasoning_score

    score = _safe_score(reward)
    return score, "\n".join(feedback)