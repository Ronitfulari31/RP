from flask import Blueprint, request, jsonify
from app.database import get_db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET'])
def get_settings():
    db = get_db()
    settings = db.settings.find_one({}, {'_id': 0})
    return jsonify(settings or {})

@settings_bp.route('/settings', methods=['PUT'])
def update_settings():
    db = get_db()
    data = request.get_json()  # safer version of request.json
    if not data:
        return jsonify({'error': 'Invalid or empty JSON body'}), 400

    db.settings.update_one({}, {'$set': data}, upsert=True)
    return jsonify({'status': 'success'})
