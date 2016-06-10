# -*- coding: utf-8 -*-

import logging
import os

from pymongo import ASCENDING, DESCENDING

from widukind_common.utils import retry_on_reconnect_error

from widukind_web import constants

UPDATE_INDEXES = False

import arrow

logger = logging.getLogger(__name__)

@retry_on_reconnect_error()
def create_or_update_indexes(db, force_mode=False, background=True):
    """Create or update MongoDB indexes"""
    
    global UPDATE_INDEXES
    
    if not force_mode and UPDATE_INDEXES:
        return

    db[constants.COL_COUNTERS].create_index([
        ("name", ASCENDING)], 
        name="name_idx", unique=True, background=background)

    UPDATE_INDEXES = True

def utcnow():
    return arrow.utcnow().datetime

def do_filesizeformat(value, binary=False):
    """Format the value like a 'human-readable' file size (i.e. 13 kB,
    4.1 MB, 102 Bytes, etc).  Per default decimal prefixes are used (Mega,
    Giga, etc.), if the second parameter is set to `True` the binary
    prefixes are used (Mebi, Gibi).
    """
    _bytes = float(value)
    base = binary and 1024 or 1000
    prefixes = [
        (binary and "KiB" or "kB"),
        (binary and "MiB" or "MB"),
        (binary and "GiB" or "GB"),
        (binary and "TiB" or "TB"),
        (binary and "PiB" or "PB"),
        (binary and "EiB" or "EB"),
        (binary and "ZiB" or "ZB"),
        (binary and "YiB" or "YB")
    ]
    if _bytes == 1:
        return "1 Byte"
    elif _bytes < base:
        return "%d Bytes" % _bytes
    else:
        for i, prefix in enumerate(prefixes):
            unit = base * base ** (i + 1)
            if _bytes < unit:
                return "%.1f %s" % ((_bytes / unit), prefix)
        return "%.1f %s" % ((_bytes / unit), prefix)


def stats():

    import psutil
    
    pid = os.getpid()
    process = psutil.Process(pid)

    try:
        mem = process.memory_info()
        
        result = {
            'mem_rss': round(mem.rss, 2), #do_filesizeformat(mem.rss),
            'mem_vms': round(mem.vms, 2), #do_filesizeformat(mem.vms),
            'mem_percent': round(process.memory_percent(), 2),
            'cpu_percent': round(process.cpu_percent(None), 2),
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None,
            'connections': len(process.connections()),
        }
        return result
        
    except Exception as err:
        logger.error(str(err))
        return {}
        
