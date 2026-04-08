# Quick Start: Debug the 1.00 Reward Issue

## Step 1: Stop Any Running Servers
```bash
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "python.*app.py" 2>/dev/null || true
sleep 2
```

## Step 2: Clear Python Cache
```bash
cd /Users/khushikumari/Documents/fraud-investigation-env
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "✓ Cache cleared"
```

## Step 3: Start the Server (in background)
```bash
cd /Users/khushikumari/Documents/fraud-investigation-env
python -B server/app.py > /tmp/server.log 2>&1 &
echo $! > /tmp/server.pid
sleep 3
echo "✓ Server started (PID: $(cat /tmp/server.pid))"
```

## Step 4: Run Inference and Capture Logs
```bash
cd /Users/khushikumari/Documents/fraud-investigation-env
export PYTHONDONTWRITEBYTECODE=1
python -B inference.py 2>&1 | tee fraud_debug.log
```

## Step 5: Kill the Server
```bash
kill $(cat /tmp/server.pid) 2>/dev/null || true
```

## Step 6: Check the Logs for Key Patterns

### Look for these patterns in `fraud_debug.log`:

**Pattern 1: RAW REWARD (should be around 1.04 for perfect answer)**
```
[GRADER] INFO: >>> RAW REWARD BEFORE CAPPING: 1.038
```

**Pattern 2: CAPPING (should convert 1.04 → 0.98)**
```
[GRADER] DEBUG: Score 1.04 >= 0.99, capping to 0.98
[GRADER] INFO: >>> AFTER _safe_score(): 0.980000
```

**Pattern 3: ENVIRONMENT CAPPING (should keep as 0.98)**
```
[ENVIRONMENT] INFO: After max(0.02, min(0.98, 0.980000)): reward = 0.980000
```

**Pattern 4: FINAL RESULT (should display as 0.98)**
```
[INFERENCE] result.reward (.2f): 0.98
[STEP] step=2 ... reward=0.98
```

## What Each Pattern Tells You

| Pattern | Means | Status |
|---------|-------|--------|
| RAW REWARD = 1.04+ | Calculating correctly | ✓ OK |
| AFTER _safe_score = 0.98 | Capping working | ✓ OK |
| After env capping = 0.98 | Environment capping working | ✓ OK |
| Final display = 0.98 | Everything working | ✓ OK |

| Pattern | Means | Problem |
|---------|-------|---------|
| RAW REWARD = 1.04 but NO capping logs | Capping not happening | ✗ BUG |
| AFTER _safe_score = 1.04 | _safe_score not capping | ✗ BUG |
| Final display = 1.00 | Float rounding issue | ⚠ CHECK |

## Quick Copy-Paste: All in One

```bash
#!/bin/bash
cd /Users/khushikumari/Documents/fraud-investigation-env
pkill -f "python.*app.py" 2>/dev/null || true
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
python -B server/app.py > /tmp/server.log 2>&1 &
SERVER_PID=$!
sleep 3
export PYTHONDONTWRITEBYTECODE=1
python -B inference.py 2>&1 | tee fraud_debug.log
kill $SERVER_PID 2>/dev/null || true
echo "✓ Done. Check fraud_debug.log for [GRADER], [ENVIRONMENT], [INFERENCE] messages"
```

## If Still 1.00

If the logs show everything is correct (0.98 after capping) but you still see 1.00:

1. **Check for rounding**: `0.985 → rounds to 0.99 → displays as 1.00` with different format
2. **Check Python float precision**: Different Python versions handle floats differently
3. **Check HTTP serialization**: The value might change during JSON transmission
4. **Add print statements**: Direct print to see the exact float value

## Files Modified

- ✓ `server/grader.py` - Added detailed logging
- ✓ `server/environment.py` - Added logging
- ✓ `inference.py` - Added logging
- ✓ Created `test_logging.py` - Standalone test
- ✓ Created `debug_test.py` - Test grader directly

All logging outputs go to **stderr** so they don't interfere with stdout JSON parsing.

