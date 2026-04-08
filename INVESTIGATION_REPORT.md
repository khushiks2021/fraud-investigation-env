# DETAILED INVESTIGATION: Why Reward is 1.00 Instead of 0.98

## The Problem
Your task_medium run showed:
- Step 2 reward: **1.00** (displayed)
- Expected: **0.98** (capped value)

## Root Cause Analysis

### 1. Theoretical Calculation
We manually calculated the raw reward as **1.0380** for a perfect submission on the legitimate new device case.

**Raw reward breakdown:**
- Fraud decision match: +0.25 ✅
- Fraud type match: +0.10 ✅
- Attack vector match (fuzzy): +0.20 ✅
- Evidence signals (4/4 matched): +0.25 ✅
- Action match: +0.20 ✅
- No false positive penalty: 0
- Reasoning quality (38 words): +0.04
- **Total: 1.0380**

### 2. Capping Logic (Should Apply)

**In `grader.py` - `_safe_score()` function (lines 36-44):**
```python
def _safe_score(reward: float) -> float:
    score = round(reward, 2)  # 1.0380 → 1.04
    
    if score >= 0.99:         # 1.04 >= 0.99? YES
        score = 0.98          # Set to 0.98
    elif score <= 0.01:
        score = 0.02
    
    return score              # Return 0.98
```

**In `environment.py` - Step function (line 105):**
```python
reward = max(0.02, min(0.98, reward))  # Further cap at 0.98
```

**Expected flow:**
1. Raw reward: 1.0380
2. After `_safe_score()`: 0.98
3. After `max(0.02, min(0.98, ...))`: 0.98
4. Displayed with `.2f` format: **"0.98"**

### 3. Actual Result: 1.00

When printed with `{reward:.2f}`, you got **1.00**, which means:
- The actual value was ≥ 0.985

This suggests the capping logic **was not applied**.

## Possible Explanations

### Hypothesis 1: The capping condition is wrong
**Code location:** `grader.py` line 39-40

```python
if score >= 0.99:
    score = 0.98
```

**Problem:** If `round(1.0380, 2)` gives 1.04, but the condition checks `>= 0.99`, it should trigger.

Let's verify:
```python
>>> round(1.0380, 2)
1.04
>>> 1.04 >= 0.99
True
```

✅ Condition should trigger. **This is NOT the bug.**

---

### Hypothesis 2: `_safe_score()` is not being called
**Code location:** `grader.py` line 134

In `_grade_task2()`:
```python
score = _safe_score(reward)  # Line 134
return score, "\n".join(feedback)
```

This line should always execute. However, there could be a scenario where a DIFFERENT function is called.

**Check:** Is the task actually "task_medium"?
- From your output: `[START] task=task_medium` ✅ YES

**So `grade()` should call `_grade_task2()`** which should call `_safe_score()`.

**Unless...** the code in production is different from the code in the repo!

---

### Hypothesis 3: The reward capping at environment.py was removed or buggy
**Code location:** `environment.py` line 105

```python
reward = max(0.02, min(0.98, reward))
```

If this line doesn't execute or if the variable is wrong, the cap wouldn't apply.

**Checking the code path:**
- Line 102-103: `truth = ...; reward, feedback = grade(...)`
- Line 105: `reward = max(0.02, min(0.98, reward))`
- Line 120: `reward=reward` (passed to FraudObservation)

This looks correct. **But let's check if there's a version mismatch.**

---

### Hypothesis 4: Float precision/Rounding issue
If somewhere in the code, the rounding is done differently, like:

```python
# Instead of:
score = round(reward, 2)  # 1.0380 → 1.04

# Someone might have:
score = round(reward, 3)  # 1.0380 → 1.038
```

Then:
```python
if 1.038 >= 0.99:  # Still TRUE
    score = 0.98
```

**This still wouldn't explain the 1.00 output.**

---

### Hypothesis 5: The condition is `> 0.99` instead of `>= 0.99`
If the condition was:
```python
if score > 0.99:  # 1.04 > 0.99? YES, still true
    score = 0.98
```

**Nope, this would still work.**

---

### Hypothesis 6: There's a different capping mechanism or the cap was disabled
Could there be a feature flag, environment variable, or conditional code that disables the cap?

Let me search for any references to 0.98 or 0.99 in the code...

---

## The Real Investigation: Check Current Code vs What You're Running

### Option A: Check if your server code is using an OLDER or MODIFIED version

1. Is there a running server process that's using cached/compiled code?
2. Is there a `.pyc` file that's being used instead of the `.py` file?

**Evidence:** You mentioned `__pycache__/` directories exist. If the server started before code changes, it might be using old bytecode.

### Option B: The condition is checking the WRONG variable

What if there's a typo like:

```python
def _safe_score(reward: float) -> float:
    score = round(reward, 2)
    
    if reward >= 0.99:  # BUG! Checking original reward, not rounded score
        score = 0.98
    
    return score
```

In this case:
- `reward = 1.0380`
- `score = round(1.0380, 2) = 1.04`
- `if 1.0380 >= 0.99:` → TRUE, so `score = 0.98`
- Return 0.98

**Still works!**

---

## Solution: Check the ACTUAL source code on disk

Let me check if the current `_safe_score()` function is actually what we think it is:

---

## Check 1: Run _safe_score directly in your environment

```python
import sys
sys.path.insert(0, '/Users/khushikumari/Documents/fraud-investigation-env')

from server.grader import _safe_score

# Test with our calculated value
result = _safe_score(1.0380)
print(f"_safe_score(1.0380) = {result}")
print(f"Formatted: {result:.2f}")
```

---

## Check 2: Verify the code hasn't been modified

The file `/Users/khushikumari/Documents/fraud-investigation-env/server/grader.py` should have:
- Line 39: `if score >= 0.99:`
- Line 40: `score = 0.98`

If it says something else, that's your bug.

---

## Check 3: Make sure Python cache is cleared

The `.pyc` files in `__pycache__/` might be stale. Try:

```bash
find /Users/khushikumari/Documents/fraud-investigation-env -type d -name __pycache__ -exec rm -rf {} +
find /Users/khushikumari/Documents/fraud-investigation-env -name "*.pyc" -delete
```

Then restart the server.

---

## The Most Likely Explanation

You're getting **1.00** when the formatted value should be **0.98** because:

1. **The capping code is NOT being executed**, OR
2. **The bytecode cache is using an old version of the code**, OR
3. **The actual server code is different from what's in the repo**

The fact that you're getting exactly 1.00 (not 1.04, not 0.99) suggests that either:
- The raw reward (1.0380) is being displayed directly without capping
- There's custom rounding logic that's converting 0.985+ to 1.00

---

## Next Steps to Debug

1. **Restart the server** with cache cleared
2. **Add logging** to `_safe_score()` and `environment.py` line 105
3. **Verify the source code** hasn't been modified
4. **Check if there's a monkey-patch** in `app.py` or `environment.py`

---

## Summary

| Component | Expected | Likely Actual | Status |
|-----------|----------|---------------|--------|
| Raw reward from _grade_task2() | 1.0380 | 1.0380 | ✅ Correct |
| After _safe_score() | 0.98 | ? | ❓ Unknown |
| After environment.py capping | 0.98 | ? | ❓ Unknown |
| Displayed value | 0.98 | 1.00 | ❌ MISMATCH |

**The capping code should work. If it's not, check for:**
- Stale `.pyc` files
- Modified source code
- Running with a different Python path
- Monkey-patching in `app.py`

