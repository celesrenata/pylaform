# pylaform/routes/ai_routes.py

from flask import Blueprint, jsonify, request
from pylaform.services.ai_factory import get_ai_service

ai_bp = Blueprint('ai', __name__, url_prefix='/api')


@ai_bp.route('/ai-status', methods=['GET'])
def check_ai_status():
    """API endpoint to check AI service connection status"""
    ai_service = get_ai_service()
    success, message = ai_service.check_connection()

    if success:
        return jsonify({'status': 'ok', 'message': message})
    else:
        return jsonify({'status': 'error', 'message': message})


@ai_bp.route('/improve-text', methods=['POST'])
def improve_text():
    """API endpoint to improve text with AI assistance"""
    data = request.json
    if not data or 'text' not in data or 'type' not in data:
        return jsonify({'error': 'Missing text or improvement type'}), 400

    text = data['text']
    improvement_type = data['type']

    ai_service = get_ai_service()
    result = ai_service.improve_text(text, improvement_type)

    return jsonify(result)