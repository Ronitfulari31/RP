from datetime import datetime

def log_resolver_metrics(db, metric_name: str):
    db.resolver_metrics.update_one(
        {"metric": metric_name},
        {
            "$inc": {"count": 1},
            "$set": {"last_updated": datetime.utcnow()}
        },
        upsert=True
    )
