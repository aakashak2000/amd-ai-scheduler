#!/usr/bin/env python3
"""
Debug version of main.py to identify import/startup issues
"""

print("🔍 Starting debug process...")

# Test basic Python functionality
print("✅ Python execution working")

# Test Flask import
try:
    from flask import Flask, request, jsonify
    print("✅ Flask import successful")
except ImportError as e:
    print(f"❌ Flask import failed: {e}")
    exit(1)

# Test other basic imports
try:
    import asyncio
    import json
    from datetime import datetime
    import traceback
    print("✅ Basic imports successful")
except ImportError as e:
    print(f"❌ Basic imports failed: {e}")
    exit(1)

# Test our custom imports one by one
imports_to_test = [
    ('coordinator_agent', 'CoordinatorAgent'),
    ('mock_data', 'TEST_SCENARIOS'),
    ('json_validator', 'sanitize_json_request'),
]

for module_name, class_name in imports_to_test:
    try:
        if module_name == 'coordinator_agent':
            from coordinator_agent import CoordinatorAgent
            print(f"✅ {module_name} import successful")
        elif module_name == 'mock_data':
            from mock_data import TEST_SCENARIOS
            print(f"✅ {module_name} import successful")
        elif module_name == 'json_validator':
            from json_validator import sanitize_json_request
            print(f"✅ {module_name} import successful")
    except ImportError as e:
        print(f"❌ {module_name} import failed: {e}")
        print(f"   Make sure {module_name}.py exists in current directory")
    except Exception as e:
        print(f"❌ {module_name} import error: {e}")
        traceback.print_exc()

# Test coordinator initialization
try:
    print("\n🔧 Testing CoordinatorAgent initialization...")
    coordinator = CoordinatorAgent()
    print("✅ CoordinatorAgent created successfully")
except Exception as e:
    print(f"❌ CoordinatorAgent initialization failed: {e}")
    traceback.print_exc()

# Test Flask app creation
try:
    print("\n🌐 Testing Flask app creation...")
    app = Flask(__name__)
    print("✅ Flask app created successfully")
except Exception as e:
    print(f"❌ Flask app creation failed: {e}")
    traceback.print_exc()

# Test a simple route
try:
    @app.route('/test')
    def test():
        return {"status": "working"}
    print("✅ Test route added successfully")
except Exception as e:
    print(f"❌ Route creation failed: {e}")
    traceback.print_exc()

# Test app.run() with debug
try:
    print("\n🚀 Starting Flask app...")
    print("If you see this message, then starting the server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
except Exception as e:
    print(f"❌ Flask app failed to start: {e}")
    traceback.print_exc()
