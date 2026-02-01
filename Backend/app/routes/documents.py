"""
Documents Routes - Refactored for Multilingual Pipeline Integration
Handles document upload with automated processing through all services
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
from werkzeug.utils import secure_filename
import os
import time
import logging
from bson import ObjectId

# Import models
from app.models.document import Document

from app.services.analysis.location_extraction import location_extraction_service
from app.services.core.pipeline_orchestrator import process_document_pipeline
from app.services.analysis.translation_service import translation_service
from app.services.analysis.sentiment_service import get_sentiment_service
from app.utils.language import decide_second_language, translate_analysis_additive, get_or_create_translated_analysis
from app.utils.preprocessing import preprocess_for_sentiment

logger = logging.getLogger(__name__)
documents_bp = Blueprint('documents', __name__)

ALLOWED_EXTENSIONS = {'csv', 'txt', 'pdf', 'docx', 'json', 'md', 'rtf'}


def extract_text(file_path, file_type):
    """
    Extract text from various file formats
    Returns: (text, error_message)
    """
    text = ""
    error = None
    try:
        if file_type == 'csv':
            try:
                import pandas as pd
                df = pd.read_csv(file_path)
                text = df.to_string()
            except ImportError:
                error = "CSV extraction library (pandas) not installed"
        elif file_type == 'txt' or file_type == 'md':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    text = f.read()
        elif file_type == 'pdf':
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                text = " ".join([p.extract_text() or "" for p in reader.pages])
            except ImportError:
                error = "PDF extraction library (PyPDF2) not installed"
        elif file_type == 'docx':
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except ImportError:
                error = "Word extraction library (python-docx) not installed"
        elif file_type == 'json':
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            text = json.dumps(data, indent=2)
        elif file_type == 'rtf':
            try:
                from striprtf.striprtf import rtf_to_text
                # RTF files are typically NOT utf-8, they are ASCII with escapes
                # but striprtf handles the content. We just need to read the raw string.
                with open(file_path, 'r', errors='ignore') as f:
                    text = rtf_to_text(f.read())
            except ImportError:
                error = "RTF extraction library (striprtf) not installed"
        
        if not error and (not text or len(text.strip()) == 0):
            error = f"File appeared to be empty or text could not be extracted from {file_type}"
            
    except Exception as e:
        text = ""
        error = f"Extraction error: {str(e)}"
        logger.warning(f"Text extraction failed for {file_type}: {e}")
        
    return text, error





@documents_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """
    Upload a document and process through multilingual pipeline
    
    Accepts:
    - file: Document file (required)
    - source: Data source (optional, default: 'file')
    - location_hint: Location hint (optional)
    - event_type_hint: Event type hint (optional)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        # Check for file
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400

        # Get metadata from form data
        source = request.form.get('source', 'file')
        location_hint = request.form.get('location_hint', None)
        event_type_hint = request.form.get('event_type_hint', None)

        filename = secure_filename(file.filename)
        file_type = filename.split('.')[-1].lower()

        if file_type not in ALLOWED_EXTENSIONS:
            return jsonify({
                'status': 'error',
                'message': f'File type .{file_type} not allowed'
            }), 400

        # Save file
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # Extract text
        raw_text, extraction_error = extract_text(file_path, file_type)
        
        if extraction_error:
            return jsonify({
                'status': 'error',
                'message': extraction_error
            }), 400

        # Get user ID
        user_id = get_jwt_identity()

        # Create document with new schema
        doc_id = Document.create(
            current_app.db,
            user_id=user_id,
            raw_text=raw_text,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            source=source,
            location_hint=location_hint,
            event_type_hint=event_type_hint
        )

        return jsonify({
            'status': 'success',
            'message': 'Document uploaded and saved successfully',
            'data': {
                'document_id': doc_id,
                'filename': filename,
                'file_type': file_type,
                'status': 'pending_analysis'
            }
        }), 201

    except Exception as e:
        import traceback
        logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500


@documents_bp.route('/upload-text', methods=['POST'])
@jwt_required()
def upload_text():
    """
    Upload raw text directly (no file upload)
    
    Request body:
    {
        "text": "Raw text content",
        "source": "twitter|news|file",
        "location_hint": "Optional location",
        "event_type_hint": "Optional event type"
}
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Text content required'
            }), 400

        raw_text = data['text']
        source = data.get('source', 'api')
        location_hint = data.get('location_hint', None)
        event_type_hint = data.get('event_type_hint', None)

        if not raw_text or len(raw_text.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Text cannot be empty'
            }), 400

        # Get user ID
        user_id = get_jwt_identity()

        # Create document
        doc_id = Document.create(
            current_app.db,
            user_id=user_id,
            raw_text=raw_text,
            source=source,
            location_hint=location_hint,
            event_type_hint=event_type_hint
        )

        return jsonify({
            'status': 'success',
            'message': 'Text saved successfully',
            'data': {
                'document_id': doc_id,
                'status': 'pending_analysis'
            }
        }), 201

    except Exception as e:
        import traceback
        logger.error(f"Text upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500


@documents_bp.route('/upload-batch', methods=['POST'])
@jwt_required()
def upload_batch():
    """
    Upload multiple text documents at once
    
    Request body:
    {
        "documents": [
            {
                "text": "Document 1 text",
                "source": "twitter",
                "location_hint": "Mumbai",
                "event_type_hint": "flood"
            },
            ...
        ]
    }
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        data = request.get_json()
        
        if not data or 'documents' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Documents array required'
            }), 400

        documents = data['documents']
        
        if not isinstance(documents, list) or len(documents) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Documents must be a non-empty array'
            }), 400

        user_id = get_jwt_identity()
        results = []

        for idx, doc_data in enumerate(documents):
            try:
                raw_text = doc_data.get('text', '')
                
                if not raw_text:
                    results.append({
                        'index': idx,
                        'status': 'error',
                        'message': 'Empty text'
                    })
                    continue

                # Create document
                doc_id = Document.create(
                    current_app.db,
                    user_id=user_id,
                    raw_text=raw_text,
                    source=doc_data.get('source', 'batch'),
                    location_hint=doc_data.get('location_hint', None),
                    event_type_hint=doc_data.get('event_type_hint', None)
                )

                results.append({
                    'index': idx,
                    'status': 'success',
                    'document_id': doc_id,
                    'message': 'Saved successfully (ready for analysis)'
                })

            except Exception as e:
                results.append({
                    'index': idx,
                    'status': 'error',
                    'message': str(e)
                })

        success_count = sum(1 for r in results if r['status'] == 'success')

        return jsonify({
            'status': 'success',
            'message': f'Batch upload complete: {success_count}/{len(documents)} successful',
            'data': {
                'total': len(documents),
                'successful': success_count,
                'results': results
            }
        }), 201

    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Batch upload failed: {str(e)}'
        }), 500


@documents_bp.route('/list', methods=['GET'])
@jwt_required()
def list_documents():
    """
    List all documents for the logged-in user with filters
    
    Query params:
    - event_type: Filter by event type
    - sentiment: Filter by sentiment (positive, negative, neutral)
    - language: Filter by language
    - source: Filter by source
    - limit: Number of results (default: 100)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Get filters from query params
        event_type = request.args.get('event_type', None)
        sentiment = request.args.get('sentiment', None)
        language = request.args.get('language', None)
        source = request.args.get('source', None)
        limit = int(request.args.get('limit', 100))

        # Get documents with filters
        documents = Document.get_by_filters(
            current_app.db,
            user_id=user_id,
            event_type=event_type,
            sentiment=sentiment,
            language=language,
            source=source,
            limit=limit
        )

        docs_list = []
        for doc in documents:
            docs_list.append({
                'document_id': str(doc['_id']),
                'filename': doc.get('filename', 'N/A'),
                'source': doc.get('source', 'unknown'),
                'language': doc.get('language', 'unknown'),
                'sentiment': doc.get('sentiment', {}).get('label', 'unknown'),
                'event_type': doc.get('event_type', 'unknown'),
                'locations': len(doc.get('locations', [])),
                'timestamp': str(doc.get('timestamp', '')),
                'processed': doc.get('processed', False),
                'text_preview': doc.get('clean_text','')[:150] + '...' if doc.get('clean_text') else doc.get('raw_text', '')[:150] + '...'
            })

        return jsonify({
            'status': 'success',
            'message': 'Documents retrieved successfully',
            'data': {
                'documents': docs_list,
                'total': len(docs_list),
                'filters_applied': {
                    'event_type': event_type,
                    'sentiment': sentiment,
                    'language': language,
                    'source': source
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"List documents error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve documents: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>', methods=['GET'])
@jwt_required()
def get_document(doc_id):
    """Get full document details with all analysis results"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        doc_data = {
            'document_id': str(document['_id']),
            'filename': document.get('filename', 'N/A'),
            'source': document.get('source', 'unknown'),
            'timestamp': str(document.get('timestamp', '')),
            'raw_text': document.get('raw_text', ''),
            'clean_text': document.get('clean_text', ''),
            'language': document.get('language', 'unknown'),
            'translated_text': document.get('translated_text', None),
            'sentiment': document.get('sentiment', {}),
            'event_type': document.get('event_type', 'unknown'),
            'event_confidence': document.get('event_confidence', 0.0),
            'locations': document.get('locations', []),
            'processing_time': document.get('processing_time', 0.0),
            'pipeline_metrics': document.get('pipeline_metrics', {}),
            'processed': document.get('processed', False)
        }

        # 🔹 Multi-Language Response Architecture (Additive)
        article_lang = document.get("language")
        second_lang = decide_second_language(article_lang)

        if second_lang:
            try:
                # Build analysis_en for translation helper
                analysis_en = {
                    "sentiment": doc_data["sentiment"],
                    "location": doc_data["locations"],
                }
                
                # Use read-through cache
                translated_data = get_or_create_translated_analysis(
                    doc=document,
                    analysis_en=analysis_en,
                    target_lang=second_lang,
                    translator_service=translation_service,
                    collection=current_app.db.documents,
                    logger=logger
                )
                
                doc_data["analysis_translated"] = {
                    second_lang: translated_data
                }
            except Exception as te:
                logger.error(f"Additive translation failed for {second_lang}: {te}")

        return jsonify({
            'status': 'success',
            'message': 'Document retrieved successfully',
            'data': doc_data
        }), 200

    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve document: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id):
    """Delete a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        # Delete file if exists
        try:
            file_path = document.get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Could not delete file: {e}")

        # Delete from database
        current_app.db.documents.delete_one({'_id': ObjectId(doc_id)})

        return jsonify({
            'status': 'success',
            'message': 'Document deleted successfully',
            'data': {
                'document_id': doc_id
            }
        }), 200

    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete document: {str(e)}'
        }), 500


# Using unified process_document_pipeline (V2-DAG Engine)

@documents_bp.route('/<doc_id>/analyze', methods=['POST'])
@jwt_required()
@cross_origin()
def analyze_document_full(doc_id):
    """
    NLP Pipeline – Unified Entry Point
    Triggers the high-accuracy DAG pipeline for a document via the core wrapper.
    """
    try:
        if current_app.db is None:
            return jsonify({'status': 'error', 'message': 'Database not available'}), 500

        # 🔒 ATOMIC LOCK: Only proceed if metadata.status is not already 'processing'
        document = current_app.db.documents.find_one_and_update(
            {
                "_id": ObjectId(doc_id),
                "user_id": user_id,
                "metadata.status": {"$ne": "processing"}
            },
            {
                "$set": {"metadata.status": "processing"}
            },
            return_document=True
        )

        if not document:
            # Check if it was because it's already processing or doesn't exist
            existing = current_app.db.documents.find_one({'_id': ObjectId(doc_id), 'user_id': user_id})
            if not existing:
                return jsonify({'status': 'error', 'message': 'Document not found'}), 404
            
            return jsonify({
                'status': 'processing',
                'message': 'Analysis is already in progress for this document.'
            }), 202

        # Unified pipeline call (now powered by V2 DAG)
        result = process_document_pipeline(
            current_app.db,
            doc_id,
            document.get('raw_text', ''),
            collection="documents"
        )

        if not result.get("success"):
            return jsonify({
                'status': 'error', 
                'message': result.get("error", "Analysis failed"),
                'reason': result.get("reason")
            }), 400

        return jsonify({
            'status': 'success',
            'message': 'Analysis completed',
            'data': result
        }), 200

    except Exception as e:
        logger.exception("Unified Pipeline Analysis failed")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@documents_bp.route('/<doc_id>/analyze-sentiment', methods=['POST'])
@jwt_required()
def analyze_document_sentiment(doc_id):
    """Run standalone sentiment analysis on a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        # Trigger Unified Orchestrator DAG for Sentiment
        result = process_document_pipeline(
            current_app.db,
            doc_id,
            document.get('raw_text', ''),
            stages=['sentiment'], # The dispatcher will route this through the DAG
            collection="documents"
        )

        if not result.get("success"):
            return jsonify({
                'status': 'error',
                'message': result.get("reason") or result.get("error") or "Analysis failed",
                'data': result
            }), 400

        return jsonify({
            'status': 'success',
            'message': 'Sentiment analysis completed via Orchestrator',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Analysis failed: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>/summarize', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def summarize_document(doc_id):
    """Generate summary for a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        # Trigger Unified Orchestrator DAG for Summary
        from app.services.core.pipeline_orchestrator import process_document_pipeline
        result = process_document_pipeline(
            current_app.db,
            doc_id,
            document.get('raw_text', ''),
            stages=['summary'], # The dispatcher will route this through the DAG
            collection="documents"
        )

        if not result.get("success"):
            return jsonify({
                'status': 'error',
                'message': result.get("reason") or result.get("error") or "Summarization failed",
                'data': result
            }), 400

        return jsonify({
            'status': 'success',
            'message': 'Summarization completed via Orchestrator',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Summarization error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Summarization failed: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>/extract-keywords', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def extract_keywords(doc_id):
    """Extract keywords from a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        # Trigger Unified Orchestrator DAG for Keywords
        from app.services.core.pipeline_orchestrator import process_document_pipeline
        result = process_document_pipeline(
            current_app.db,
            doc_id,
            document.get('raw_text', ''),
            stages=['preprocessing', 'extraction'], # Reroute to DAG
            collection="documents"
        )

        if not result.get("success"):
            return jsonify({
                'status': 'error',
                'message': result.get("reason") or result.get("error") or "Keyword extraction failed",
                'data': result
            }), 400

        return jsonify({
            'status': 'success',
            'message': 'Keyword extraction completed via Orchestrator',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Keyword extraction error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Keyword extraction failed: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>/translate', methods=['POST'])
@jwt_required()
def translate_document(doc_id):
    """Translate a document to English via Orchestrator"""
    try:
        if current_app.db is None:
            return jsonify({'status': 'error', 'message': 'Database not available'}), 500

        user_id = get_jwt_identity()
        document = current_app.db.documents.find_one({'_id': ObjectId(doc_id), 'user_id': user_id})

        if not document:
            return jsonify({'status': 'error', 'message': 'Document not found'}), 404

        # Trigger Unified Orchestrator DAG for Translation
        from app.services.core.pipeline_orchestrator import process_document_pipeline
        result = process_document_pipeline(
            current_app.db,
            doc_id,
            document.get('raw_text', ''),
            stages=['translation'],
            collection="documents"
        )

        return jsonify({
            'status': 'success',
            'message': 'Translation completed via Orchestrator',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Translation failed: {str(e)}'}), 500
