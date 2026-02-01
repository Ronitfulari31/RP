from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import logging
import time

# DAG Core
from app.services.dag.executor import NLPDAGExecutor
from app.services.dag.context import create_initial_context
from app.services.dag.nodes.preprocessing_node import PreprocessingNode
from app.services.dag.nodes.translation_node import TranslationNode

translation_bp = Blueprint('translation', __name__)
logger = logging.getLogger(__name__)

@translation_bp.route('/translate', methods=['POST'])
@jwt_required()
def translate_text():
    """
    Translate text using the DAG Orchestrator (Transient Mode)
    Ensures 100% architectural parity with the main pipeline.
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Text is required'
            }), 400

        text = data['text']
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'en')
        # 🚀 Default to 'display' for standalone API (Human reading)
        translation_mode = data.get('mode') or data.get('translation_mode') or 'display'

        if not text:
            return jsonify({
                'status': 'error',
                'message': 'Text cannot be empty'
            }), 400

        # --- ORCHESTRATED EXECUTION (Final Target Architecture) ---
        from app.services.analysis.translation_orchestrator import translate_with_entities
        from flask import current_app
        from bson import ObjectId
        
        # Get database from Flask app (uses .env configuration)
        db = current_app.db if hasattr(current_app, 'db') else None
        
        # Generate a unique doc_id for this translation request
        doc_id = str(ObjectId())
        
        result = translate_with_entities(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            translation_mode=translation_mode,
            doc_id=doc_id,  # Pass doc_id for entity learning
            db=db  # Pass database for entity learning (from .env)
        )
        
        if not result.get("success"):
            return jsonify({
                'status': 'error',
                'message': result.get('error', 'Translation failed')
            }), 400

        return jsonify({
            'status': 'success',
            'data': {
                'original_text': text,
                'translated_text': result.get('translated_text'),
                'entities': result.get('entities'),
                'source_lang': result.get('source_lang'),
                'target_lang': target_lang,
                'metadata': result.get('metadata')
            }
        }), 200

    except Exception as e:
        logger.exception("Orchestrated Translation API error")
        return jsonify({
            'status': 'error',
            'message': f'Translation failed: {str(e)}'
        }), 500


@translation_bp.route('/detect', methods=['POST'])
@jwt_required()
def detect_language():
    """
    Detect language of the provided text using PreprocessingService
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Text is required'
            }), 400

        text = data['text']
        
        if not text:
            return jsonify({
                'status': 'error',
                'message': 'Text cannot be empty'
            }), 400

        # Use the core service for detection
        from app.services.core.preprocessing import preprocessing_service
        result = preprocessing_service.detect_language(text)
        
        return jsonify({
            'status': 'success',
            'data': {
                'language': result.get('value', 'unknown'),
                'confidence': result.get('confidence', 0.0),
                'role': result.get('role', 'unknown')
            }
        }), 200

    except Exception as e:
        logger.exception("Language detection failed")
        return jsonify({
            'status': 'error',
            'message': f'Detection failed: {str(e)}'
        }), 500
