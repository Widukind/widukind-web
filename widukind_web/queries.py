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

    project = {
        "_id": False,
        "provider_name": True
    }
    pipelines.append({"$project": project})

    pipelines.append({
        "$group": {"_id": "$provider_name", "count": {"$sum": 1}}}
    )
    datasets_count = col_datasets(db).aggregate(pipelines, allowDiskUse=True)
    return dict([(d["_id"], d["count"]) for d in datasets_count])

def datasets_counter_status(db=None, match=None):
    pipelines = []
    
    if match:
        pipelines.append({"$match": match})

    project = {
        "_id": False,
        "provider_name": True,
        "enable": True
    }
    pipelines.append({"$project": project})

    pipelines.append({
        "$group": {"_id": {"provider": "$provider_name", "enable": "$enable"}, "count": {"$sum": 1}}
    })
    datasets_count = col_datasets(db).aggregate(pipelines, allowDiskUse=True)
    
    ds_enable = {}
    ds_disable = {}
    all_ds = {}
    for d in datasets_count:
        provider = d["_id"]["provider"]

        if not provider in all_ds:
            all_ds[provider] = 0
        all_ds[provider] += d["count"]
        
        if d["_id"]["enable"]:
            ds_enable[provider] = d["count"]
        else: 
            ds_disable[provider] = d["count"]
    
    return {
        "datasets": all_ds,
        "enabled": ds_enable,
        "disabled": ds_disable,
    }
    
def series_counter(db=None, match=None):
    pipelines = []
    
    if match:
        pipelines.append({"$match": match})

    project = {
        "_id": False,
        "provider_name": True,
        "dataset_code": True,
    }
    pipelines.append({"$project": project})

    pipelines.append({
        "$group": { "_id": {"provider": "$provider_name", "dataset_code": "$dataset_code"}, 
                   "count": {"$sum": 1}}}
    )
    series_count = col_series(db).aggregate(pipelines, allowDiskUse=True)

    counters = {}
    for d in series_count:
        provider = d["_id"]["provider"]
        if not provider in counters:
            counters[provider] = {"count": 0, "datasets": {}}
        
        dataset = d["_id"]["dataset_code"]
        counters[provider]["datasets"][dataset] = d["count"]
        counters[provider]["count"] += d["count"]
    
    return counters

