from flask import Flask, jsonify, request
import os
import sys
import time
import random

# CRASH_ON_START check at module level — before Flask even initializes
if os.getenv("CRASH_ON_START") == "true":
    print("CRASH_ON_START=true — crashing intentionally for demo", flush=True)
    sys.exit(1)

app = Flask(__name__)

# Simulated memory leak storage
memory_hog = []

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "app": "broken-demo",
        "version": os.getenv("APP_VERSION", "1.0")
    })

@app.route('/health')
def health():
    # If CRASH_HEALTH is set, fail health checks to trigger liveness probe failure
    if os.getenv("CRASH_HEALTH") == "true":
        return jsonify({"status": "unhealthy"}), 500
    return jsonify({"status": "healthy"}), 200

@app.route('/crash')
def crash():
    """Endpoint that crashes the app"""
    print("Crash endpoint hit — exiting", flush=True)
    sys.exit(1)

@app.route('/memory-leak')
def memory_leak():
    """Endpoint that causes OOMKill"""
    memory_hog.append(' ' * 10 * 1024 * 1024)
    return jsonify({
        "message": "Memory allocated",
        "total_mb": len(memory_hog) * 10
    })

@app.route('/slow')
def slow():
    """Slow endpoint that might timeout"""
    time.sleep(random.randint(5, 15))
    return jsonify({"message": "finally done"})

@app.route('/random-error')
def random_error():
    """50% chance of error"""
    if random.random() > 0.5:
        return jsonify({"error": "Random failure"}), 500
    return jsonify({"message": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
