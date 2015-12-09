import logging
from bson.timestamp import Timestamp
try:
    from pymongo import MongoClient as Connection
except ImportError:
    from pymongo import Connection

from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import OperationFailure, PyMongoError
import pymongo
if pymongo.version_tuple[0] >= 3:
    from pymongo.errors import ServerSelectionTimeoutError
    write_method = 'insert_one'
else:
    write_method = 'save'
    
from widukind_web.utils import utcnow    

"""
Example format of generated bson document:
{
    'thread': -1216977216,
    'threadName': 'MainThread',
    'level': 'ERROR',
    'timestamp': Timestamp(1290895671, 63),
    'message': 'test message',
    'module': 'test_module',
    'fileName': '/var/projects/python/log4mongo-python/tests/test_handlers.py',
    'lineNumber': 38,
    'method': 'test_emit_exception',
    'loggerName':  'testLogger',
    'exception': {
        'stackTrace': 'Traceback (most recent call last):
                       File "/var/projects/python/log4mongo-python/tests/\
                           test_handlers.py", line 36, in test_emit_exception
                       raise Exception(\'exc1\')
                       Exception: exc1',
        'message': 'exc1',
        'code': 0
    }
}
"""
_connection = None

class MongoFormatter(logging.Formatter):

    DEFAULT_PROPERTIES = logging.LogRecord(
        '', '', '', '', '', '', '', '').__dict__.keys()

    def format(self, record):
        """Formats LogRecord into python dictionary."""
        # Standard document
        document = {
            #'timestamp': Timestamp(int(record.created), int(record.msecs)),
            'timestamp': utcnow(),
            'level': record.levelname,
            'thread': record.thread,
            'threadName': record.threadName,
            'message': record.getMessage(),
            'loggerName': record.name,
            'fileName': record.pathname,
            'module': record.module,
            'method': record.funcName,
            'lineNumber': record.lineno
        }
        # Standard document decorated with exception info
        if record.exc_info is not None:
            document.update({
                'exception': {
                    'message': str(record.exc_info[1]),
                    'code': 0,
                    'stackTrace': self.formatException(record.exc_info)
                }
            })
        # Standard document decorated with extra contextual information
        if len(self.DEFAULT_PROPERTIES) != len(record.__dict__):
            contextual_extra = set(record.__dict__).difference(
                set(self.DEFAULT_PROPERTIES))
            if contextual_extra:
                for key in contextual_extra:
                    document[key] = record.__dict__[key]
        return document


class MongoHandler(logging.Handler):

    def __init__(self, db=None, level=logging.NOTSET, 
                 collection='logs',
                 fail_silently=False,
                 formatter=None, capped=True,
                 capped_max=10000, capped_size=None, reuse=True):
        """
        Setting up mongo handler, initializing mongo database connection via
        pymongo.

        If reuse is set to false every handler will have it's own MongoClient.
        This could hammer down your MongoDB instance, but you can still use this
        option.

        The default is True. As such a program with multiple handlers
        that log to mongodb will have those handlers share a single connection
        to MongoDB.
        """
        logging.Handler.__init__(self, level)
        self.db = db
        self.collection_name = collection
        self.fail_silently = fail_silently

        self.collection = None
        self.authenticated = False
        self.formatter = formatter or MongoFormatter()
        self.capped = capped
        self.capped_max = capped_max
        self.capped_size = capped_size
        self.reuse = reuse
        self._connect()
        self._create_index()        

    def _connect(self):
        """Connecting to mongo database."""
        
        if self.capped:
            try:
                kwargs = dict(capped=True)
                if self.capped_size:
                    kwargs['size'] = self.capped_size
                else:
                    kwargs['max'] = self.capped_max
                
                self.collection = Collection(self.db, self.collection_name,
                                             **kwargs)
            except OperationFailure:
                self.collection = self.db[self.collection_name]
        else:
            self.collection = self.db[self.collection_name]

    def _create_index(self):
        
        self.collection.create_index([
            ("timestamp", DESCENDING)], 
            name="timestamp_idx")

        self.collection.create_index([
            ("message", ASCENDING)], 
            name="message_idx")

        self.collection.create_index([
            ("loggerName", ASCENDING)], 
            name="loggerName_idx")
        
        
    def emit(self, record):
        """Inserting new logging record to mongo database."""
        if self.collection is not None:
            try:
                getattr(self.collection, write_method)(self.format(record))
            except Exception:
                if not self.fail_silently:
                    self.handleError(record)

