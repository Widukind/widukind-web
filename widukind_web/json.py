# -*- coding: utf-8 -*-

import datetime

try:
    import simplejson as _json
except ImportError:
    import json as _json

from bson import ObjectId

import arrow

"""
def decode_datetime(obj):
    if '__datetime__' in obj:
        obj = datetime.datetime.strptime(obj["as_str"], "%Y%m%dT%H:%M:%S.%f")
    return obj

def encode_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return {'__datetime__': True, 'as_str': obj.strftime("%Y%m%dT%H:%M:%S.%f")}
    return obj
"""    

def json_dump_convert(obj):
    
    if isinstance(obj, ObjectId):
        return str(obj)
    
    elif isinstance(obj, datetime.datetime):
        """
        produit: '2015-11-16T23:38:04.551214+00:00'
        
        convert JS: new Date('2015-11-16T23:38:04.551214+00:00')
                    Date {Tue Nov 17 2015 00:38:04 GMT+0100}
        """
        return arrow.get(obj).for_json()
    
    
        #return {'__datetime__': True, 'as_str': obj.strftime("%Y%m%dT%H:%M:%S.%f")}

    return obj

"""
def json_load_convert(obj):
    
    if isinstance(obj, ObjectId):
        return str(obj)
    
    elif isinstance(obj, datetime.datetime):
        return arrow.get(obj).for_json()
        #return {'__datetime__': True, 'as_str': obj.strftime("%Y%m%dT%H:%M:%S.%f")}

    return obj
"""

"""
json.dumps(obj, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None, default=None, sort_keys=False, **kw)
json.loads(s, encoding=None, cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw)
"""

def dumps(obj, default=None, **kwargs):
    #from bson import json_util
    #return json_util.dumps(obj, **kwargs)
    return _json.dumps(obj, default=json_dump_convert, **kwargs)
 
def loads(s, object_hook=None, **kwargs):
     return _json.loads(s, **kwargs)
     #return _json.loads(s, object_hook=json_load_convert, **kwargs)
 