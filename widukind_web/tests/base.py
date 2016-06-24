# -*- coding: utf-8 -*-

import os

from widukind_common import tests_tools as utils

from widukind_common.tests.flask_base_tests import BaseFlaskTestCase 

from widukind_web.utils import create_or_update_indexes as local_create_or_update_indexes
from widukind_web import constants

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(BASE_DIR, "resources"))

REFERENTIEL = {
    "providers": {
        "count": 1,
    },
    "categories": {
        "count": 226,
    },
    "datasets": {
        "count": 1,
    },
    "series": {
        "count": 100,
    },
    "tags": {
        "count": 51,
    },               
}

def create_fixtures(db):
    """
    mongoexport --host mongodb --pretty --jsonArray --db widukind --collection providers -q "{name: 'INSEE'}" | gzip -c >/widukind/providers.json.gz
    mongoexport --host mongodb --pretty --jsonArray --db widukind --collection categories -q "{provider_name: 'INSEE'}" | gzip -c >/widukind/categories.json.gz
    mongoexport --host mongodb --pretty --jsonArray --db widukind --collection datasets -q "{ dataset_code: 'IPCH-2015-FR-COICOP'}" | gzip -c >/widukind/datasets.json.gz
    mongoexport --host mongodb --pretty --jsonArray --db widukind --collection series -q "{provider_name: 'INSEE', dataset_code: 'IPCH-2015-FR-COICOP'}" --limit 100 | gzip -c >/widukind/series.json.gz
    mongoexport --host mongodb --pretty --jsonArray --db widukind --collection tags -q '{provider_name: {"$in": ["INSEE"]}, count: { "$gte": 50} }' | gzip -c >/widukind/tags.json.gz
    """
    import gzip
    from bson import json_util
    filenames = {
        "providers": os.path.abspath(os.path.join(RESOURCES_DIR, "providers.json.gz")),
        "categories": os.path.abspath(os.path.join(RESOURCES_DIR, "categories.json.gz")),
        "datasets": os.path.abspath(os.path.join(RESOURCES_DIR, "datasets.json.gz")),
        "series": os.path.abspath(os.path.join(RESOURCES_DIR, "series.json.gz")),
        "tags": os.path.abspath(os.path.join(RESOURCES_DIR, "tags.json.gz")),
    }
    for collection, filepath in filenames.items():
        #print("filepath : ", filepath)
        datas = json_util.loads(gzip.open(filepath).read().decode())
        if not isinstance(datas, list):
            datas = [datas]
        for d in datas:
            if 'metadata' in d:
                d['metadata'] = {}
        result = db[collection].insert_many(datas)
        #print(collection, " : ", len(result.inserted_ids))
            
class TestCase(BaseFlaskTestCase):
    
    def setUp(self):
        super().setUp()
        self.assertEqual(self.db.name, "widukind_test")

    def _create_app(self):
        from widukind_web import wsgi
        app = wsgi.create_app('widukind_web.settings.Test', db=self.db)
        return app
    
    def fixtures(self):
        create_fixtures(self.db)
    
    def set_indexes(self):
        super().set_indexes()
        local_create_or_update_indexes(self.db, force_mode=True)
        
    def clean_db(self):
        utils.clean_mongodb(collection_list=constants.COL_ALL, db=self.db)