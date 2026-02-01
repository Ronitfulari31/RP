# Switch-Back Guide: RSS & Articles Collection

If you wish to stop using the Kaggle `news_dataset` and return to the live RSS `articles` system, follow these steps:

## 1. Database Configuration
In various files, the collection name has been switched from `articles` to `news_dataset`. To revert, look for commented-out lines like:
```python
# self.article_store = ArticleStore(collection_name="articles")
self.article_store = ArticleStore(collection_name="news_dataset")
```
Uncomment the `articles` line and comment or delete the `news_dataset` line.

**Key Files to Check:**
- [news_fetcher.py](file:///d:/Projects/LAST_YEAR_PROJECT/Backend/app/services/discovery/news_fetcher.py)
- [rss_scheduler.py](file:///d:/Projects/LAST_YEAR_PROJECT/Backend/app/services/scheduler/rss_scheduler.py)
- [retriever.py](file:///d:/Projects/LAST_YEAR_PROJECT/Backend/app/services/intelli_search/retriever.py)
- [ingest_kaggle_news.py](file:///d:/Projects/LAST_YEAR_PROJECT/Backend/scripts/ingest_kaggle_news.py) (if reusing for local data)

## 2. Background Processing
The background worker currently targets `news_dataset`. Ensure any running scripts (like `process_news_dataset.py`) are stopped or redirected back to the `articles` collection by changing the `collection_name` parameter in the `ArticleStore` initialization.

## 3. Web API Routes
In [news.py](file:///d:/Projects/LAST_YEAR_PROJECT/Backend/app/routes/news.py), several routes have been modified. 
Revert the collection access:
```python
# db.articles.find(...)
db.news_dataset.find(...)
```

## 4. Vector Search Index
Ensure that the `articles_vector_index` in MongoDB Atlas is correctly associated with the `articles` collection. If a separate index was created for `news_dataset`, update the `VECTOR_INDEX_NAME` in [vector_retriever.py](file:///d:/Projects/LAST_YEAR_PROJECT/Backend/app/services/intelli_search/vector_retriever.py).

---
> [!NOTE]
> This guide ensures that the transition back to the original production-ready RSS pipeline is seamless and non-destructive.
