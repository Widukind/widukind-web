# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)

from werkzeug.contrib.fixers import ProxyFix
from flask import Flask, request, abort, session, g, redirect, url_for, render_template, current_app
from decouple import config as config_from_env

import gevent

from widukind_web import extensions
from widukind_web import constants
from widukind_web.extensions import cache

def _conf_converters(app):
    
    from werkzeug.routing import BaseConverter, ValidationError
    from bson.objectid import ObjectId
    from bson.errors import InvalidId
    
    class BSONObjectIdConverter(BaseConverter):

        def to_python(self, value):
            try:
                return ObjectId(value)
            except (InvalidId, ValueError, TypeError):
                raise ValidationError()
             
        def to_url(self, value):
            return str(value)    
        
    app.url_map.converters['objectid'] = BSONObjectIdConverter
    
def _conf_logging(debug=False, 
                  stdout_enable=True, 
                  syslog_enable=False,
                  prog_name='widukind_web',
                  config_file=None,
                  LEVEL_DEFAULT="INFO"):

    import sys
    import logging.config
    
    if config_file:
        logging.config.fileConfig(config_file, disable_existing_loggers=True)
        return logging.getLogger(prog_name)
    
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'debug': {
                'format': 'line:%(lineno)d - %(asctime)s %(name)s: [%(levelname)s] - [%(process)d] - [%(module)s] - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'simple': {
                'format': '%(asctime)s %(name)s: [%(levelname)s] - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },    
        'handlers': {
            'null': {
                'level':LEVEL_DEFAULT,
                'class':'logging.NullHandler',
            },
            'console':{
                'level':LEVEL_DEFAULT,
                'class':'logging.StreamHandler',
                'formatter': 'simple'
            },      
        },
        'loggers': {
            '': {
                'handlers': [],
                'level': LEVEL_DEFAULT,
                'propagate': False,
            },
            prog_name: {
                #'handlers': [],
                'level': LEVEL_DEFAULT,
                'propagate': True,
            },
        },
    }
    
    if sys.platform.startswith("win32"):
        LOGGING['loggers']['']['handlers'] = ['console']

    elif syslog_enable:
        LOGGING['handlers']['syslog'] = {
                'level':'INFO',
                'class':'logging.handlers.SysLogHandler',
                'address' : '/dev/log',
                'facility': 'daemon',
                'formatter': 'simple'    
        }       
        LOGGING['loggers']['']['handlers'].append('syslog')
        
    if stdout_enable:
        if not 'console' in LOGGING['loggers']['']['handlers']:
            LOGGING['loggers']['']['handlers'].append('console')

    '''if handlers is empty'''
    if not LOGGING['loggers']['']['handlers']:
        LOGGING['loggers']['']['handlers'] = ['console']
    
    if debug:
        LOGGING['loggers']['']['level'] = 'DEBUG'
        LOGGING['loggers'][prog_name]['level'] = 'DEBUG'
        for handler in LOGGING['handlers'].keys():
            LOGGING['handlers'][handler]['formatter'] = 'debug'
            LOGGING['handlers'][handler]['level'] = 'DEBUG' 

    #from pprint import pprint as pp 
    #pp(LOGGING)
    #werkzeug = logging.getLogger('werkzeug')
    #werkzeug.handlers = []
             
    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger('')
    
    return logger

def _conf_logging_mongo(app):
    from widukind_common.mongo_logging_handler import MongoHandler
    handler = MongoHandler(db=app.widukind_db, collection=constants.COL_LOGS)
    handler.setLevel(logging.ERROR)
    app.logger.addHandler(handler)
    
def _conf_logging_mail(app):
    from logging.handlers import SMTPHandler
    
    ADMIN = app.config.get("MAIL_ADMINS", None)
    if not ADMIN:
        app.logger.error("Emails address for admins are not configured")
        return
        
    ADMINS = ADMIN.split(",")
    """
    mailhost, fromaddr, toaddrs, subject, credentials=None, secure=None, timeout=5.0
    """
    mail_handler = SMTPHandler(app.config.get("MAIL_SERVER"),
                               app.config.get("MAIL_DEFAULT_SENDER"),
                               ADMINS, 
                               'Application Failed')
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler) 
    
def _conf_logging_errors(app):
    
    def log_exception(sender, exception, **extra):
        sender.logger.error(str(exception))
        
    from flask import got_request_exception
    got_request_exception.connect(log_exception, app)        

def _conf_sentry(app):
    try:
        from raven.contrib.flask import Sentry
        if app.config.get('SENTRY_DSN', None):
            sentry = Sentry(app, logging=True, level=app.logger.level)
    except ImportError:
        pass
    
def _conf_db(app):
    import gridfs
    from widukind_common.utils import get_mongo_db
    from widukind_web.utils import create_or_update_indexes
    app.widukind_db = get_mongo_db(app.config.get("MONGODB_URL"), connect=False)
    app.widukind_fs = gridfs.GridFS(app.widukind_db)
    create_or_update_indexes(app.widukind_db)

def _conf_session(app):
    from widukind_common.flask_utils.mongo_session import PyMongoSessionInterface
    app.session_interface = PyMongoSessionInterface(app.widukind_db,
                                                    collection=constants.COL_SESSION)
    
def _conf_cache(app):
    """
    @cache.cached(timeout=50)
    @cache.cached(timeout=50, key_prefix='all_comments')
    @cache.memoize(50)
    """
    cache.init_app(app)
    
def _conf_default_views(app):

    @app.route("/", endpoint="home")
    def index():
        return render_template("index.html")

def _conf_record_query(app):
    
    from gevent.queue import Queue
    
    from widukind_web import queues    
    queues.RECORD_QUERY = Queue()
    
    def record():
        col = app.widukind_db[constants.COL_QUERIES]
        while True:
            q = queues.RECORD_QUERY.get()
            col.insert(q)
    
    return [gevent.spawn(record)]

    
def _conf_auth(app):
    extensions.auth.init_app(app)
    
    @app.context_processor
    def is_auth():
        def _is_logged():
            if session.get("is_logged"):
                return True
            
            result = extensions.auth.authenticate()
            
            if result:
                session["is_logged"] = True
                return True
        
        return dict(is_logged=_is_logged)        
    
def _conf_mail(app):
    extensions.mail.init_app(app)

def _conf_periods(app):
    
    import pandas
    
    def get_ordinal_from_period(date_str, freq=None):
        if not freq in constants.CACHE_FREQUENCY:
            return pandas.Period(date_str, freq=freq).ordinal
        
        key = "p-to-o-%s.%s" % (date_str, freq)
        value = cache.get(key)
        if value:
            return value
        
        value = pandas.Period(date_str, freq=freq).ordinal
        cache.set(key, value, timeout=300)
        return value
    
    def get_period_from_ordinal(date_ordinal, freq=None):
        if not freq in constants.CACHE_FREQUENCY:
            return str(pandas.Period(ordinal=date_ordinal, freq=freq))
    
        key = "o-to-p-%s.%s" % (date_ordinal, freq)
        value = cache.get(key)
        if value:
            return value
        
        value = str(pandas.Period(ordinal=date_ordinal, freq=freq))
        cache.set(key, value, timeout=300)
        return value
    
    app.get_ordinal_from_period = get_ordinal_from_period
    app.get_period_from_ordinal = get_period_from_ordinal
    
    @app.context_processor
    def convert_pandas_period():
        def convert(date_ordinal, frequency):
            return get_period_from_ordinal(date_ordinal, frequency)
        return dict(pandas_period=convert)
    

def _conf_processors(app):

    @app.context_processor
    def versions():
        from pkg_resources import get_distribution
        packages = ["widukind-web", "widukind-common", "pandas", "gevent", "pymongo"]
        _versions = {}
        for p in packages:
            try:
                _versions[p] = get_distribution(p).version
            except:
                _versions[p] = "None"
        return dict(versions=_versions)
    
    @app.context_processor
    def cart():
        cart = session.get("cart", [])
        return dict(cart=cart, cart_count=len(cart))

    @app.context_processor
    def bookmark():
        bookmark = session.get("bookmark", [])
        return dict(bookmark=bookmark, bookmark_count=len(bookmark))

    @app.context_processor
    def functions():
        def _split(s):
            return s.split()
        return dict(split=_split)
    
    @app.context_processor
    def provider_list():
        #TODO: update or cache !!!
        #providers = []
        query = {"enable": True}
        projection = {"_id": False, "name": True, "slug": True,
                      "long_name": True, "enable": True}
        cursor = app.widukind_db[constants.COL_PROVIDERS].find(query, projection)
            #providers.append({"name": doc['name'], "long_name": doc['long_name']})
        return dict(provider_list=list(cursor))

    @app.context_processor
    def frequencies():
        def frequency(value):
            return constants.FREQUENCIES_DICT.get(value, "Unknow")
        return dict(frequency=frequency)
                
def _conf_bootstrap(app):
    from flask_bootstrap import WebCDN
    from flask_bootstrap import Bootstrap
    Bootstrap(app)
    app.extensions['bootstrap']['cdns']['jquery'] = WebCDN(
        '//cdnjs.cloudflare.com/ajax/libs/jquery/2.1.4/'
    )    

def _conf_sitemap(app):
    
    from datetime import datetime, timedelta

    from functools import wraps
    from flask_sitemap import sitemap_page_needed
    
    from widukind_web import queries
    
    CACHE_KEY = 'sitemap-page-{0}'
    
    @sitemap_page_needed.connect
    def create_page(app, page, urlset):
        key = CACHE_KEY.format(page)
        cache.set(key, extensions.sitemap.render_page(urlset=urlset))
        
    def load_page(fn):
        @wraps(fn)
        def loader(*args, **kwargs):
            page = kwargs.get('page')
            key = CACHE_KEY.format(page)
            return cache.get(key) or fn(*args, **kwargs)
        return loader

    @extensions.sitemap.register_generator
    def sitemap_providers():
        query = {"enable": True}
        providers = queries.col_providers().find(query, {'_id': False, 'slug': True})
        for doc in providers:
            yield ('views.datasets', {'slug': doc['slug']}, None, "weekly", 0.9)

    @extensions.sitemap.register_generator
    def sitemap_datasets():
        query = {"enable": True}
        projection = {'_id': False, "download_last": True, "slug": True} 
        datasets = queries.col_datasets().find(query, projection)
        for doc in datasets:
            yield ('views.dataset-by-slug', 
                   {'slug': doc['slug']}, 
                   doc['download_last'], 
                   "daily", 0.9)
            
    @extensions.sitemap.register_generator
    def sitemap_global():
        yield ('home', {}, None, "daily", 1.0)
        yield ('download.fs_list_dataset', {}, None, "daily", 0.8)
        yield ('download.fs_list_series', {}, None, "hourly", 0.8)

    extensions.sitemap.decorators = []
    app.config['SITEMAP_VIEW_DECORATORS'] = [load_page]

    extensions.sitemap.init_app(app)
    
def _conf_bp(app):
    from widukind_web import download
    from widukind_web import views
    from widukind_web import admin
    app.register_blueprint(download.bp, url_prefix='/download')    
    app.register_blueprint(views.bp, url_prefix='/views')
    app.register_blueprint(admin.bp, url_prefix='/_cepremap/admin')

def _conf_errors(app):

    from werkzeug import exceptions as ex

    class DisabledElement(ex.HTTPException):
        code = 307
        description = 'Disabled element'
    abort.mapping[307] = DisabledElement

    @app.errorhandler(307)
    def disable_error(error):
        is_json = request.args.get('json') or request.is_xhr
        values = dict(error="307 Error", original_error=error, referrer=request.referrer)
        print(dir(error), type(error))
        if is_json:
            values['original_error'] = str(values['original_error'])
            return app.jsonify(values), 307
        return render_template('errors/307.html', **values), 307
    
    @app.errorhandler(500)
    def error_500(error):
        is_json = request.args.get('json') or request.is_xhr
        values = dict(error="Server Error", original_error=error, referrer=request.referrer)
        if is_json:
            values['original_error'] = str(values['original_error'])
            return app.jsonify(values), 500
        return render_template('errors/500.html', **values), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        is_json = request.args.get('json') or request.is_xhr
        values = dict(error="404 Error", original_error=error, referrer=request.referrer)
        if is_json:
            values['original_error'] = str(values['original_error'])
            return app.jsonify(values), 404
        return render_template('errors/404.html', **values), 404

def _conf_jsonify(app):

    from widukind_web import json

    def jsonify(obj):
        content = json.dumps(obj)
        return current_app.response_class(content, mimetype='application/json')

    app.jsonify = jsonify

def create_app(config='widukind_web.settings.Prod'):
    
    env_config = config_from_env('WIDUKIND_SETTINGS', config)
    
    app = Flask(__name__)
    app.config.from_object(env_config)    

    _conf_db(app)

    app.config['LOGGER_NAME'] = 'widukind_web'
    app._logger = _conf_logging(debug=app.debug, prog_name='widukind_web')
    
    if app.config.get("LOGGING_MONGO_ENABLE", True):
        _conf_logging_mongo(app)

    if app.config.get("LOGGING_MAIL_ENABLE", False):
        _conf_logging_mail(app)

    _conf_logging_errors(app)    
    
    extensions.moment.init_app(app)
    
    _conf_bootstrap(app)
    
    _conf_sentry(app)
    
    _conf_errors(app)
    
    _conf_cache(app)
    
    _conf_converters(app)
    
    _conf_jsonify(app)
    
    _conf_default_views(app)
    
    _conf_bp(app)
    
    _conf_record_query(app)

    _conf_processors(app)
    
    _conf_periods(app)
    
    _conf_auth(app)
    
    _conf_sitemap(app)
    
    _conf_session(app)
    
    _conf_mail(app)
    
    app.wsgi_app = ProxyFix(app.wsgi_app)
    
    return app
