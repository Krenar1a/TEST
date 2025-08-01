from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS for all routes with specific origin
CORS(app, origins=["http://localhost:3000"], supports_credentials=True)

# Add missing admin routes if they don't exist
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    # Add authentication check here
    try:
        # Return admin statistics
        stats = {
            "total_bills": 0,  # Add actual logic
            "total_users": 0,  # Add actual logic
            "api_calls_today": 0,  # Add actual logic
        }
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/api-keys', methods=['GET', 'POST'])
def handle_api_keys():
    # Add authentication check here
    try:
        if request.method == 'GET':
            # Return API keys configuration
            return jsonify({
                "openai_key": "sk-...",  # Masked version
                "claude_key": "sk-...",  # Masked version
            }), 200
        elif request.method == 'POST':
            # Update API keys
            data = request.get_json()
            # Add logic to update API keys
            return jsonify({"message": "API keys updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/representatives', methods=['GET'])
def get_representatives():
    try:
        address = request.args.get('address', '')
        if not address:
            return jsonify({"error": "Address parameter is required"}), 400
        
        # Add logic to fetch representatives based on address
        representatives = []  # Add actual logic here
        
        return jsonify({"representatives": representatives}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Fix the bills endpoint to handle errors properly
@app.route('/api/bills', methods=['GET'])
def get_bills():
    try:
        page = int(request.args.get('page', 1))
        search = request.args.get('search', '')
        sort = request.args.get('sort', 'date')
        category = request.args.get('category', '')
        
        # Add your bills fetching logic here
        bills = []  # Replace with actual data
        
        return jsonify({
            "bills": bills,
            "page": page,
            "per_page": 12,
            "total": 0,
            "has_prev": False,
            "has_next": False,
            "prev_num": None,
            "next_num": None
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500