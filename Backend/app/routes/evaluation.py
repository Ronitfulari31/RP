"""
Evaluation Routes - Research Metrics & Model Evaluation
Handles cross-lingual consistency, ML metrics, and performance tracking
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
import time

from app.services.core.evaluation import evaluation_service
from app.services.core.pipeline_evaluator import get_pipeline_evaluator

logger = logging.getLogger(__name__)
evaluation_bp = Blueprint('evaluation', __name__)


@evaluation_bp.route('/cross-lingual-consistency', methods=['GET'])
@jwt_required()
def check_cross_lingual_consistency():
    """
    RESEARCH CRITICAL 
    Check cross-lingual sentiment consistency
    
    Compares sentiment of original text vs translated text
    to measure if sentiment is preserved across translation
    
    Query params:
    - limit: Number of documents to check (default: 100)
    - document_ids: Comma-separated list of specific document IDs (optional)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        # Get query params
        limit = int(request.args.get('limit', 100))
        document_ids_str = request.args.get('document_ids', None)
        
        document_ids = None
        if document_ids_str:
            document_ids = document_ids_str.split(',')

        logger.info(f"Checking cross-lingual consistency for {limit} documents...")

        # Call evaluation service
        result = evaluation_service.check_cross_lingual_consistency(
            document_ids=document_ids,
            limit=limit
        )

        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 500

        return jsonify({
            'status': 'success',
            'message': 'Cross-lingual consistency analysis complete',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Cross-lingual consistency check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Analysis failed: {str(e)}'
        }), 500


@evaluation_bp.route('/ml-metrics', methods=['POST'])
@jwt_required()
def calculate_ml_metrics():
    """
    Calculate ML classification metrics
    
    Request body:
    {
        "y_true": ["positive", "negative", "neutral", ...],
        "y_pred": ["positive", "negative", "neutral", ...],
        "labels": ["positive", "negative", "neutral"]  // optional
    }
    
    Returns: accuracy, precision, recall, F1 score, confusion matrix
    """
    try:
        data = request.get_json()
        
        if not data or 'y_true' not in data or 'y_pred' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Both y_true and y_pred are required'
            }), 400

        y_true = data['y_true']
        y_pred = data['y_pred']
        labels = data.get('labels', None)

        # Calculate metrics
        result = evaluation_service.calculate_ml_metrics(y_true, y_pred, labels)

        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 400

        return jsonify({
            'status': 'success',
            'message': 'ML metrics calculated successfully',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"ML metrics calculation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Calculation failed: {str(e)}'
        }), 500


@evaluation_bp.route('/performance-metrics', methods=['GET'])
@jwt_required()
def get_performance_metrics():
    """
    Get system performance metrics
    
    Returns average latencies and throughput for:
    - Translation
    - Sentiment analysis
    - NER
    - Total processing time
    
    Query params:
    - limit: Number of documents to analyze (default: 100)
    - document_ids: Comma-separated list of specific document IDs (optional)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        # Get query params
        limit = int(request.args.get('limit', 100))
        document_ids_str = request.args.get('document_ids', None)
        
        document_ids = None
        if document_ids_str:
            document_ids = document_ids_str.split(',')

        logger.info(f"Calculating performance metrics for {limit} documents...")

        # Call evaluation service
        result = evaluation_service.calculate_performance_metrics(
            document_ids=document_ids,
            limit=limit
        )

        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 500

        return jsonify({
            'status': 'success',
            'message': 'Performance metrics calculated successfully',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Performance metrics error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Calculation failed: {str(e)}'
        }), 500


@evaluation_bp.route('/benchmark-sentiment-models', methods=['POST'])
@jwt_required()
def benchmark_sentiment_models():
    """
    Benchmark different sentiment analysis models
    
    Request body:
    {
        "test_texts": [
            "This is a positive statement",
            "This is terrible",
            "This is ok"
        ]
    }
    
    Returns: Comparison of BERTweet, VADER, and TextBlob
    """
    try:
        data = request.get_json()
        
        if not data or 'test_texts' not in data:
            return jsonify({
                'status': 'error',
                'message': 'test_texts array is required'
            }), 400

        test_texts = data['test_texts']
        
        if not isinstance(test_texts, list) or len(test_texts) == 0:
            return jsonify({
                'status': 'error',
                'message': 'test_texts must be a non-empty array'
            }), 400

        logger.info(f"Benchmarking sentiment models on {len(test_texts)} texts...")

        # Call evaluation service
        result = evaluation_service.benchmark_sentiment_models(test_texts)

        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 500

        return jsonify({
            'status': 'success',
            'message': 'Model benchmarking complete',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Model benchmarking error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Benchmarking failed: {str(e)}'
        }), 500


# ============================================================================
# NEW ENDPOINTS - Pipeline Evaluation Metrics
# ============================================================================

@evaluation_bp.route('/trigger', methods=['POST'])
@jwt_required()
def trigger_evaluation():
    """
    Trigger evaluation on selected articles for specified pipeline version(s)
    
    Request body options:
    1. Specific article IDs:
       {
         "article_ids": ["6963792720089a755a508e98"],
         "pipeline_version": "v1"
       }
    
    2. Random N articles:
       {
         "limit": 10,
         "pipeline_version": "v1"
       }
    
    3. Filter-based selection:
       {
         "filters": {"source": "BBC", "category": "Politics"},
         "limit": 20,
         "pipeline_version": "v2"
       }
    
    4. All articles (with safety limit):
       {
         "all": true,
         "limit": 100,
         "pipeline_version": "both"
       }
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400

        # Validate pipeline_version
        pipeline_version = data.get('pipeline_version')
        if pipeline_version not in ['v1', 'v2', 'both']:
            return jsonify({
                'status': 'error',
                'message': 'pipeline_version must be one of: v1, v2, both'
            }), 400

        # Determine article selection method
        article_ids = data.get('article_ids')
        limit = data.get('limit', 10)
        filters = data.get('filters')
        all_articles = data.get('all', False)

        # Validate that at least one selection method is provided
        if not any([article_ids, filters, all_articles]):
            return jsonify({
                'status': 'error',
                'message': 'Must provide one of: article_ids, filters, or all=true'
            }), 400

        # Safety limit
        max_limit = 100
        if limit > max_limit:
            limit = max_limit
            logger.warning(f"Limit exceeded max ({max_limit}), using {max_limit}")

        # Fetch articles based on selection method
        articles_collection = current_app.db['articles']
        query = {}

        if article_ids:
            # Specific article IDs
            try:
                object_ids = [ObjectId(aid) for aid in article_ids]
                query = {'_id': {'$in': object_ids}}
            except InvalidId as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid article ID format: {str(e)}'
                }), 400
        elif filters:
            # Filter-based selection
            if 'source' in filters:
                query['source'] = filters['source']
            if 'category' in filters:
                query['category'] = filters['category']
            if 'date_from' in filters:
                query['published_date'] = {'$gte': filters['date_from']}
            if 'date_to' in filters:
                if 'published_date' not in query:
                    query['published_date'] = {}
                query['published_date']['$lte'] = filters['date_to']
        # else: all_articles = True, query remains {}

        # Fetch articles
        articles = list(articles_collection.find(query).limit(limit))

        if not articles:
            return jsonify({
                'status': 'error',
                'message': 'No articles found matching the criteria'
            }), 404

        logger.info(f"Evaluating {len(articles)} articles with pipeline version: {pipeline_version}")

        # Evaluate articles
        evaluator = get_pipeline_evaluator()
        evaluated_articles_collection = current_app.db['evaluated_articles']
        
        start_time = time.time()
        articles_processed = []
        successful = 0
        failed = 0

        versions_to_evaluate = ['v1', 'v2'] if pipeline_version == 'both' else [pipeline_version]

        for article in articles:
            article_id = article['_id']
            
            try:
                # Check if article already exists in evaluated_articles
                existing = evaluated_articles_collection.find_one({'original_article_id': article_id})
                
                for version in versions_to_evaluate:
                    # Run evaluation
                    evaluation_result = evaluator.evaluate_article(article, version)
                    
                    if existing:
                        # Update specific version
                        versions_evaluated = existing.get('evaluation_metadata', {}).get('versions_evaluated', [])
                        if version not in versions_evaluated:
                            versions_evaluated.append(version)
                        
                        evaluated_articles_collection.update_one(
                            {'original_article_id': article_id},
                            {
                                '$set': {
                                    f'evaluations.{version}': evaluation_result,
                                    'evaluation_metadata.updated_at': datetime.utcnow(),
                                    'evaluation_metadata.versions_evaluated': versions_evaluated
                                }
                            }
                        )
                    else:
                        # Insert new evaluated article
                        evaluated_article = {
                            'original_article_id': article_id,
                            'title': article.get('title', ''),
                            'content': article.get('content', ''),
                            'source': article.get('source', ''),
                            'published_date': article.get('published_date'),
                            'evaluations': {
                                version: evaluation_result
                            },
                            'evaluation_metadata': {
                                'created_at': datetime.utcnow(),
                                'updated_at': datetime.utcnow(),
                                'versions_evaluated': [version],
                                'triggered_by_user': get_jwt_identity()
                            }
                        }
                        evaluated_articles_collection.insert_one(evaluated_article)
                
                articles_processed.append({
                    'article_id': str(article_id),
                    'title': article.get('title', ''),
                    'versions_evaluated': versions_to_evaluate,
                    'status': 'completed'
                })
                successful += 1
                
            except Exception as e:
                logger.error(f"Evaluation failed for article {article_id}: {str(e)}")
                articles_processed.append({
                    'article_id': str(article_id),
                    'title': article.get('title', ''),
                    'status': 'failed',
                    'error': str(e)
                })
                failed += 1

        end_time = time.time()
        evaluation_time_ms = round((end_time - start_time) * 1000, 2)

        # Determine response status
        if failed == 0:
            status = 'success'
            message = f'Evaluation completed for {successful} articles'
        elif successful == 0:
            status = 'error'
            message = f'All evaluations failed'
        else:
            status = 'partial_success'
            message = f'Evaluation completed with {failed} errors'

        return jsonify({
            'status': status,
            'message': message,
            'summary': {
                'total_articles': len(articles),
                'successful': successful,
                'failed': failed,
                'evaluated_versions': versions_to_evaluate,
                'evaluation_time_ms': evaluation_time_ms,
                'articles_processed': articles_processed
            }
        }), 200

    except Exception as e:
        logger.error(f"Trigger evaluation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Evaluation trigger failed: {str(e)}'
        }), 500


@evaluation_bp.route('/query', methods=['POST'])
@jwt_required()
def query_evaluations():
    """
    Query evaluation results from evaluated_articles collection
    
    Request body:
    {
      "article_ids": ["6963792720089a755a508e98"],
      "pipeline_version": "v1"  // or "v2" or "both"
    }
    
    Returns evaluation results for specified articles and version(s)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400

        # Validate pipeline_version
        pipeline_version = data.get('pipeline_version')
        if pipeline_version not in ['v1', 'v2', 'both']:
            return jsonify({
                'status': 'error',
                'message': 'pipeline_version must be one of: v1, v2, both'
            }), 400

        # Validate article_ids
        article_ids = data.get('article_ids')
        if not article_ids or not isinstance(article_ids, list) or len(article_ids) == 0:
            return jsonify({
                'status': 'error',
                'message': 'article_ids must be a non-empty array'
            }), 400

        # Convert to ObjectIds
        try:
            object_ids = [ObjectId(aid) for aid in article_ids]
        except InvalidId as e:
            return jsonify({
                'status': 'error',
                'message': f'Invalid article ID format: {str(e)}'
            }), 400

        # Query evaluated_articles collection
        evaluated_articles_collection = current_app.db['evaluated_articles']
        query = {'original_article_id': {'$in': object_ids}}

        # Build projection based on pipeline_version
        if pipeline_version == 'both':
            projection = {
                'original_article_id': 1,
                'title': 1,
                'evaluations.v1': 1,
                'evaluations.v2': 1
            }
        else:
            projection = {
                'original_article_id': 1,
                'title': 1,
                f'evaluations.{pipeline_version}': 1
            }

        results_cursor = evaluated_articles_collection.find(query, projection)
        results = []

        for doc in results_cursor:
            if pipeline_version == 'both':
                # Return both versions
                results.append({
                    'article_id': str(doc['original_article_id']),
                    'title': doc.get('title', ''),
                    'evaluations': {
                        'v1': doc.get('evaluations', {}).get('v1'),
                        'v2': doc.get('evaluations', {}).get('v2')
                    }
                })
            else:
                # Return single version
                evaluation = doc.get('evaluations', {}).get(pipeline_version)
                if evaluation:
                    results.append({
                        'article_id': str(doc['original_article_id']),
                        'title': doc.get('title', ''),
                        'evaluation': evaluation
                    })

        message = None
        if len(results) == 0:
            message = 'No evaluation results found for the specified articles'

        return jsonify({
            'status': 'success',
            'pipeline_version': pipeline_version,
            'count': len(results),
            'results': results,
            'message': message
        }), 200

    except Exception as e:
        logger.error(f"Query evaluations error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Query failed: {str(e)}'
        }), 500
