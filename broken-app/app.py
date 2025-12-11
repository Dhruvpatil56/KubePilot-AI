from flask import Flask, jsonify, request
import os
import sys
import time
import random

app = Flask(__name__)

# Simulated memory leak
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
    return jsonify({"status": "healthy"}), 200

@app.route('/memory-leak')
def memory_leak():
    """Endpoint that causes OOMKill"""
    # Allocate 10MB each call
    memory_hog.append(' ' * 10 * 1024 * 1024)
    return jsonify({
        "message": "Memory allocated",
        "total_mb": len(memory_hog) * 10
    })

@app.route('/crash')
def crash():
    """Endpoint that crashes the app"""
    sys.exit(1)

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
    # Check for crash-on-start mode
    if os.getenv("CRASH_ON_START") == "true":
        print("CRASH_ON_START is true, exiting...")
        sys.exit(1)
    
    app.run(host='0.0.0.0', port=5000)
