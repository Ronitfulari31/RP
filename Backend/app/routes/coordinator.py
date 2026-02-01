"""
Coordinator API Endpoints
Control and monitor the global fetch-process coordinator
"""

from flask import Blueprint, jsonify
from app.coordinator import get_coordinator
import logging

logger = logging.getLogger(__name__)

coordinator_bp = Blueprint('coordinator', __name__, url_prefix='/api/coordinator')


@coordinator_bp.route('/status', methods=['GET'])
def get_status():
    """Get coordinator status"""
    try:
        coordinator = get_coordinator()
        status = coordinator.get_status()
        
        return jsonify({
            "status": "success",
            **status
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting coordinator status: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@coordinator_bp.route('/pause-fetch', methods=['POST'])
def pause_fetch():
    """Manually pause RSS fetching"""
    try:
        coordinator = get_coordinator()
        coordinator.pause_fetch()
        
        return jsonify({
            "status": "success",
            "message": "RSS fetching paused"
        }), 200
        
    except Exception as e:
        logger.error(f"Error pausing fetch: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@coordinator_bp.route('/resume-fetch', methods=['POST'])
def resume_fetch():
    """Manually resume RSS fetching"""
    try:
        coordinator = get_coordinator()
        coordinator.resume_fetch()
        
        return jsonify({
            "status": "success",
            "message": "RSS fetching resumed"
        }), 200
        
    except Exception as e:
        logger.error(f"Error resuming fetch: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@coordinator_bp.route('/pause-process', methods=['POST'])
def pause_process():
    """Manually pause NLP processing"""
    try:
        coordinator = get_coordinator()
        coordinator.pause_process()
        
        return jsonify({
            "status": "success",
            "message": "NLP processing paused"
        }), 200
        
    except Exception as e:
        logger.error(f"Error pausing process: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@coordinator_bp.route('/resume-process', methods=['POST'])
def resume_process():
    """Manually resume NLP processing"""
    try:
        coordinator = get_coordinator()
        coordinator.resume_process()
        
        return jsonify({
            "status": "success",
            "message": "NLP processing resumed"
        }), 200
        
    except Exception as e:
        logger.error(f"Error resuming process: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@coordinator_bp.route('/reset-stats', methods=['POST'])
def reset_stats():
    """Reset processing statistics"""
    try:
        coordinator = get_coordinator()
        coordinator.reset_stats()
        
        return jsonify({
            "status": "success",
            "message": "Statistics reset"
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
