"""
Evaluation Service (RESEARCH CRITICAL)
Handles ML performance metrics, cross-lingual consistency, and performance tracking
This is the research novelty component
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from app.database import db
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import numpy as np

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for model evaluation and research metrics"""
    
    def __init__(self):
        pass
    
    def calculate_ml_metrics(self, y_true: List, y_pred: List, labels: Optional[List] = None) -> Dict:
        """
        Calculate standard ML classification metrics
        
        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            labels: List of possible labels (optional)
            
        Returns:
            Dictionary with accuracy, precision, recall, F1 score
        """
        try:
            if len(y_true) != len(y_pred):
                raise ValueError("True and predicted labels must have same length")
            
            if len(y_true) == 0:
                raise ValueError("Cannot calculate metrics on empty data")
            
            # Calculate metrics
            accuracy = accuracy_score(y_true, y_pred)
            
            # Use 'weighted' average for multi-class
            precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            
            # Confusion matrix
            cm = confusion_matrix(y_true, y_pred, labels=labels)
            
            logger.info(f"Metrics - Accuracy: {accuracy:.3f}, Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {f1:.3f}")
            
            return {
                'accuracy': round(accuracy, 3),
                'precision': round(precision, 3),
                'recall': round(recall, 3),
                'f1_score': round(f1, 3),
                'confusion_matrix': cm.tolist(),
                'sample_size': len(y_true)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate ML metrics: {e}")
            return {
                'error': str(e),
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0
            }
    
    def check_cross_lingual_consistency(self, document_ids: Optional[List[str]] = None, limit: int = 100) -> Dict:
        """
        CHECK CROSS-LINGUAL CONSISTENCY 
        This is the RESEARCH NOVELTY!
        
        Compare sentiment of original text vs translated text
        to measure if sentiment is preserved across translation
        
        Args:
            document_ids: Specific document IDs to check (optional)
            limit: Maximum number of documents to check
            
        Returns:
            Dictionary with:
                - consistency_percentage: % of documents with consistent sentiment
                - total_checked: Number of documents checked
                - consistent_count: Number of consistent documents
                - inconsistent_docs: List of inconsistent documents with details
        """
        try:
            # Build query
            query = {}
            
            # Filter for documents that have both original and translated sentiment
            # (These would have been processed through the pipeline)
            query['language'] = {'$ne': 'en'}  # Non-English documents
            query['translated_text'] = {'$exists': True, '$ne': ''}
            query['sentiment.label'] = {'$exists': True}
            
            if document_ids:
                from bson import ObjectId
                query['_id'] = {'$in': [ObjectId(doc_id) for doc_id in document_ids]}
            
            # Fetch documents
            documents = list(db.documents.find(query).limit(limit))
            
            if len(documents) == 0:
                return {
                    'consistency_percentage': 0.0,
                    'total_checked': 0,
                    'consistent_count': 0,
                    'inconsistent_docs': [],
                    'message': 'No multilingual documents found with sentiment analysis'
                }
            
            # Import services for re-analysis
            from app.services.analysis.sentiment_service import get_sentiment_service
            
            consistent_count = 0
            inconsistent_docs = []
            
            for doc in documents:
                original_text = doc.get('clean_text', doc.get('raw_text', ''))
                translated_text = doc.get('translated_text', '')
                stored_sentiment = doc.get('sentiment', {}).get('label', '')
                
                # Analyze sentiment of translated text
                translated_sentiment_result = sentiment_service.analyze(translated_text, method='auto')
                translated_sentiment = translated_sentiment_result.get('sentiment', 'neutral')
                
                # Compare
                if stored_sentiment.lower() == translated_sentiment.lower():
                    consistent_count += 1
                else:
                    inconsistent_docs.append({
                        'document_id': str(doc['_id']),
                        'title': doc.get('title', 'Untitled'),
                        'language': doc.get('language', 'unknown'),
                        'original_sentiment': stored_sentiment,
                        'translated_sentiment': translated_sentiment,
                        'original_text_preview': original_text[:100],
                        'translated_text_preview': translated_text[:100]
                    })
            
            total_checked = len(documents)
            consistency_percentage = (consistent_count / total_checked) * 100
            
            logger.info(f"✓ Cross-lingual consistency: {consistency_percentage:.1f}% ({consistent_count}/{total_checked})")
            
            return {
                'consistency_percentage': round(consistency_percentage, 2),
                'total_checked': total_checked,
                'consistent_count': consistent_count,
                'inconsistent_count': len(inconsistent_docs),
                'inconsistent_docs': inconsistent_docs[:10],  # Limit to 10 for response size
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Cross-lingual consistency check failed: {e}")
            return {
                'error': str(e),
                'consistency_percentage': 0.0,
                'total_checked': 0,
                'consistent_count': 0
            }
    
    def calculate_performance_metrics(self, document_ids: Optional[List[str]] = None, limit: int = 100) -> Dict:
        """
        Calculate system performance metrics
        
        Args:
            document_ids: Specific document IDs (optional)
            limit: Maximum documents to analyze
            
        Returns:
            Dictionary with average latencies and throughput
        """
        try:
            query = {}
            
            if document_ids:
                from bson import ObjectId
                query['_id'] = {'$in': [ObjectId(doc_id) for doc_id in document_ids]}
            
            # Fetch documents with pipeline metrics
            documents = list(db.documents.find(
                query,
                {
                    'pipeline_metrics': 1,
                    'processing_time': 1,
                    'created_at': 1
                }
            ).limit(limit))
            
            if len(documents) == 0:
                return {
                    'message': 'No documents with performance metrics found',
                    'total_documents': 0
                }
            
            # Aggregate metrics
            translation_times = []
            sentiment_times = []
            ner_times = []
            total_processing_times = []
            
            for doc in documents:
                metrics = doc.get('pipeline_metrics', {})
                
                if 'translation_time' in metrics:
                    translation_times.append(metrics['translation_time'])
                
                if 'sentiment_time' in metrics:
                    sentiment_times.append(metrics['sentiment_time'])
                
                if 'ner_time' in metrics:
                    ner_times.append(metrics['ner_time'])
                
                if 'processing_time' in doc:
                    total_processing_times.append(doc['processing_time'])
            
            # Calculate averages
            avg_translation_time = np.mean(translation_times) if translation_times else 0
            avg_sentiment_time = np.mean(sentiment_times) if sentiment_times else 0
            avg_ner_time = np.mean(ner_times) if ner_times else 0
            avg_total_time = np.mean(total_processing_times) if total_processing_times else 0
            
            # Calculate throughput (documents per second)
            if avg_total_time > 0:
                throughput = 1.0 / avg_total_time
            else:
                throughput = 0
            
            logger.info(f"Performance metrics: Avg total time: {avg_total_time:.3f}s, Throughput: {throughput:.2f} docs/s")
            
            return {
                'total_documents_analyzed': len(documents),
                'average_translation_time': round(avg_translation_time, 3),
                'average_sentiment_time': round(avg_sentiment_time, 3),
                'average_ner_time': round(avg_ner_time, 3),
                'average_total_processing_time': round(avg_total_time, 3),
                'throughput_docs_per_second': round(throughput, 2),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {
                'error': str(e),
                'total_documents_analyzed': 0
            }
    
    def benchmark_sentiment_models(self, test_texts: List[str]) -> Dict:
        """
        Benchmark different sentiment analysis models
        
        Args:
            test_texts: List of texts to test
            
        Returns:
            Comparison of BERTweet, VADER, and TextBlob
        """
        try:
            from app.services.analysis.sentiment_service import get_sentiment_service
            
            results = {
                'bertweet': {'times': [], 'sentiments': []},
                'vader': {'times': [], 'sentiments': []},
                'textblob': {'times': [], 'sentiments': []}
            }
            
            for text in test_texts:
                # Test BERTweet
                start = time.time()
                bertweet_result = sentiment_service.analyze(text, method='bertweet')
                results['bertweet']['times'].append(time.time() - start)
                results['bertweet']['sentiments'].append(bertweet_result.get('sentiment'))
                
                # Test VADER
                start = time.time()
                vader_result = sentiment_service.analyze(text, method='vader')
                results['vader']['times'].append(time.time() - start)
                results['vader']['sentiments'].append(vader_result.get('sentiment'))
                
                # Test TextBlob
                start = time.time()
                textblob_result = sentiment_service.analyze(text, method='textblob')
                results['textblob']['times'].append(time.time() - start)
                results['textblob']['sentiments'].append(textblob_result.get('sentiment'))
            
            # Calculate average times
            return {
                'bertweet': {
                    'avg_time': round(np.mean(results['bertweet']['times']), 4),
                    'sentiments': results['bertweet']['sentiments']
                },
                'vader': {
                    'avg_time': round(np.mean(results['vader']['times']), 4),
                    'sentiments': results['vader']['sentiments']
                },
                'textblob': {
                    'avg_time': round(np.mean(results['textblob']['times']), 4),
                    'sentiments': results['textblob']['sentiments']
                },
                'sample_size': len(test_texts)
            }
            
        except Exception as e:
            logger.error(f"Model benchmarking failed: {e}")
            return {'error': str(e)}


# Singleton instance
evaluation_service = EvaluationService()
