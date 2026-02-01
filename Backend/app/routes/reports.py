from flask import Blueprint, request, jsonify
from app.database import get_db

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/create-report', methods=['POST'])
def create_report():
    db = get_db()  # ✅ get db inside the route
    data = request.json
    result = db.reports.insert_one(data)
    return jsonify({'status': 'success', 'report_id': str(result.inserted_id)})

@reports_bp.route('/list-reports', methods=['GET'])
def list_reports():
    db = get_db()
    reports = list(db.reports.find({}, {'_id': 0}))
    return jsonify(reports)

@reports_bp.route('/reports/<report_id>/get-report', methods=['GET'])
def get_report(report_id):
    db = get_db()
    report = db.reports.find_one({'report_id': report_id}, {'_id': 0})
    return jsonify(report)

@reports_bp.route('/reports/<report_id>/delete-report', methods=['DELETE'])
def delete_report(report_id):
    db = get_db()
    db.reports.delete_one({'report_id': report_id})
    return jsonify({'status': 'success'})
