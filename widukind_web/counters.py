# -*- coding: utf-8 -*-

import logging

from widukind_web import constants
from widukind_web import utils

logger = logging.getLogger(__name__)

def upsert(db, category, name, new_count):
    col_counters = db[constants.COL_COUNTERS]
    
    logger.info("count category[%s] for %s: new[%s]" % (category, name, new_count))
    
    data = {"category": category,
            'count': new_count, 
            'lastUpdated': utils.utcnow()}
    return col_counters.update_one({"name": name}, {"$set": data}, upsert=True)

def datasets_by_provider(db):
    """Datasets count by Provider"""
    _group_by = {"$group": {"_id": "$provider", "count": {"$sum": 1}}}
    result = db[constants.COL_DATASETS].aggregate([_group_by])
    category = "counter.datasets"
    for r in result:
        name = "%s.datasets" % r['_id']
        upsert(db, category, name, r['count'])

def series_by_provider(db):
    """Series count by Provider"""
    _group_by = {"$group": {"_id": "$provider", "count": {"$sum": 1}}}
    result = db[constants.COL_SERIES].aggregate([_group_by])
    category = "counter.series"
    for r in result:
        name = "%s.series" % r['_id']
        upsert(db, category, name, r['count'])

#TODO: update_many or bulk update
def series_by_datasets(db):
    """Series count by Provider and Datasets"""        
    _group_by = {"$group": {"_id": {"provider": "$provider", "datasetCode": "$datasetCode"}, "count": {"$sum": 1}}}
    result = db[constants.COL_SERIES].aggregate([_group_by])
    category = "counter.series.bydataset"
    for r in result:
        name = "%s.%s.series" % (r['_id']['provider'], r['_id']['datasetCode'])
        upsert(db, category, name, r['count'])

