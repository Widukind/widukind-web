# -*- coding: utf-8 -*-

"""
Stored session:
{
    "_id" : ObjectId("565c35c38ffacf92d42b0c30"),
    "sid" : "9300c59a-1bbc-40d4-bab4-fdc0b9f0984a",
    "data" : {
            "current_theme" : "darkly"
    },
    "expiration" : ISODate("2015-12-01T11:40:51.312Z")
}
"""

import datetime
import sys
import uuid

from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict
from bson.tz_util import utc
from pymongo import ASCENDING

__all__ = ("PyMongoSession", "PyMongoSessionInterface")

if sys.version_info >= (3, 0):
    basestring = str

#31 days
DEFAULT_EXPIRE = 60 * 60 * 24 * 7 * 31

class PyMongoSession(CallbackDict, SessionMixin):

    def __init__(self, initial=None, sid=None):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.modified = False


class PyMongoSessionInterface(SessionInterface):
    """SessionInterface for mongoengine"""

    def __init__(self, db, collection='session', 
                 expireAfterSeconds=DEFAULT_EXPIRE):
        """
        The MongoSessionInterface

        :param db: The app's db eg: MongoEngine()
        :param collection: The session collection name defaults to "session"
        """

        if not isinstance(collection, basestring):
            raise ValueError('collection argument should be string or unicode')

        self.db = db
        self.col = self.db[collection]
        self.expireAfterSeconds = expireAfterSeconds
        
        self.create_indexes()
    
    def create_indexes(self):
        self.col.create_index([
            ("expiration", ASCENDING)], 
            name="expiration_idx", unique=True, expireAfterSeconds=self.expireAfterSeconds)

    def get_expiration_time(self, app, session):
        if session.permanent:
            return app.permanent_session_lifetime
        return datetime.timedelta(days=1)

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)
        if sid:
            stored_session = self.col.find_one({"sid":sid})

            if stored_session:
                expiration = stored_session['expiration']

                if not expiration.tzinfo:
                    expiration = expiration.replace(tzinfo=utc)

                if expiration > datetime.datetime.utcnow().replace(tzinfo=utc):
                    return PyMongoSession(initial=stored_session['data'], sid=stored_session['sid'])

        return PyMongoSession(sid=str(uuid.uuid4()))

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        httponly = self.get_cookie_httponly(app)

        if not session:
            if session.modified:
                response.delete_cookie(app.session_cookie_name, domain=domain)
            return

        expiration = datetime.datetime.utcnow().replace(tzinfo=utc) + self.get_expiration_time(app, session)

        if session.modified:
            datas = {
                "$set": {"expiration": expiration, "data": session},
            }
            self.col.update_one({"sid": session.sid}, datas, upsert=True)

        response.set_cookie(app.session_cookie_name, session.sid,
                            expires=expiration, httponly=httponly, domain=domain)
