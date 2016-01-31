# -*- coding: utf-8 -*-

from flask import current_app

from widukind_common import constants

def col_providers(db=None):
    db = db or current_app.widukind_db
    return db[constants.COL_PROVIDERS]

def col_datasets(db=None):
    db = db or current_app.widukind_db
    return db[constants.COL_DATASETS]

def col_categories(db=None):
    db = db or current_app.widukind_db
    return db[constants.COL_CATEGORIES]

def col_series(db=None):
    db = db or current_app.widukind_db
    return db[constants.COL_SERIES]

def datasets_counter(db=None, match=None):
    pipelines = []
    
    if match:
        pipelines.append({"$match": match})

    pipelines.append({
        "$group": {"_id": "$provider_name", "count": {"$sum": 1}}}
    )
    datasets_count = col_datasets(db).aggregate(pipelines)
    return dict([(d["_id"], d["count"]) for d in datasets_count])

def series_counter(db=None, match=None):
    pipelines = []
    
    if match:
        pipelines.append({"$match": match})

    pipelines.append({
        "$group": { "_id": {"provider": "$provider_name", "dataset_code": "$dataset_code"}, 
                   "count": {"$sum": 1}}}
    )
    series_count = col_series(db).aggregate(pipelines)

    counters = {}
    for d in series_count:
        provider = d["_id"]["provider"]
        if not provider in counters:
            counters[provider] = {"count": 0, "datasets": {}}
        
        dataset = d["_id"]["dataset_code"]
        counters[provider]["datasets"][dataset] = d["count"]
        counters[provider]["count"] += d["count"]
    
    return counters
