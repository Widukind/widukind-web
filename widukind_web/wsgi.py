# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)

from werkzeug.contrib.fixers import ProxyFix
from flask import Flask, request, abort, session, g, redirect, url_for, render_template, current_app
from decouple import config as config_from_env

import gevent

from widukind_web import extensions
from widukind_web import constants
from widukind_web import utils
from widukind_web.extensions import cache

THEMES = [
    'widukind',
    'cerulean',
    'cyborg',
    'darkly',
    'flatly',
    'journal',
    'lumen',
    'paper',
    'readable',
    'sandstone',
    'simplex',
    'slate',
    'spacelab',
    'superhero',
    'united',              
]

def _conf_converters(app):
    
    from werkzeug.routing import BaseConverter, ValidationError
    from itsdangerous import base64_encode, base64_decode
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
    
def _conf_themes(app):
    
    @app.before_request
    def current_theme():
        if not constants.SESSION_THEME_KEY in session:
            session[constants.SESSION_THEME_KEY] = app.config.get('DEFAULT_THEME', 'slate')
        g.theme = session.get(constants.SESSION_THEME_KEY)
            
    @app.context_processor
    def inject_theme():
        try:
            return {
                constants.SESSION_THEME_KEY: g.theme.lower(),
                'current_theme_url': url_for('static', filename='themes/bootswatch/%s/bootstrap.min.css' % g.theme.lower()),
                'themes': THEMES,                        
            }
        except AttributeError:
            return {
                constants.SESSION_THEME_KEY: app.config.get('DEFAULT_THEME', 'slate'),
                'current_theme_url': url_for('static', filename='themes/bootswatch/%s/bootstrap.min.css' % self.config('DEFAULT_THEME', 'slate')),
                'themes': THEMES,
            }

    @app.route('/change-theme', endpoint="changetheme") 
    def change_theme():
        new_theme = request.args.get('theme', None)
        next = request.args.get('next') or request.referrer or '/'
        try:
            if new_theme:
                session[constants.SESSION_THEME_KEY] = new_theme
        except (Exception, err):
            pass 
        return redirect(next)


def _conf_logging(debug=False, 
                  stdout_enable=True, 
                  syslog_enable=False,
                  prog_name='widukind_web',
                  config_file=None,
                  LEVEL_DEFAULT="INFO"):

    import sys
    import logging
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
                'level': 'INFO',
                'propagate': False,
            },
            prog_name: {
                #'handlers': [],
                'level': 'INFO',
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
    logger = logging.getLogger(prog_name)
    
    return logger

def _conf_logging_mongo(app):
    from widukind_web.mongo_logging_handler import MongoHandler
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
        print("log_exception.exception : ", exception)
        print("log_exception;extra : ", extra)
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
    app.widukind_db = get_mongo_db(app.config.get("MONGODB_URL"))
    app.widukind_fs = gridfs.GridFS(app.widukind_db)
    create_or_update_indexes(app.widukind_db)

def _conf_session(app):
    from widukind_web.mongo_session import PyMongoSessionInterface
    app.session_interface = PyMongoSessionInterface(app.widukind_db)
    
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
        #return redirect(url_for("views.last_series"))

def _conf_record_query(app):
    
    from flask import request_finished
    from gevent.queue import Queue
    
    from widukind_web import queues    
    queues.RECORD_QUERY = Queue()
    
    def record():
        col = app.widukind_db[constants.COL_QUERIES]
        while True:
            q = queues.RECORD_QUERY.get()
            col.insert(q)
    
    """
    @request_finished.connect_via(app)
    def put_queue(sender, response, **extra):
        print(sender, response, extra)
        #print(response.response)
        print(response.headers)
        print(request.path)
    """
    
    return [gevent.spawn(record)]

def _conf_locker(app):
    from widukind_web.mongolock import MongoLock, MongoLockLocked
    app.task_locker = MongoLock(db=app.widukind_db, collection=constants.COL_LOCK)

def _conf_counters(app):
    """
    TODO: websocket 
    """
    from widukind_web.mongolock import MongoLockLocked
    from widukind_web import counters
    
    counter_sleep = app.config.get("COUNTER_SLEEP", 60)

    def update_counters():
        while True:
            try:
                with app.task_locker('update.counters', 'update.counters', expire=600, timeout=300):
                    counters.datasets_by_provider(app.widukind_db)
                    counters.series_by_provider(app.widukind_db)
                    counters.series_by_datasets(app.widukind_db)
            except MongoLockLocked as err:
                app.logger.warning(str(err))
            except Exception as err:
                app.logger.error(err)
            
            gevent.sleep(counter_sleep)

    return [gevent.spawn(update_counters)]
        
    
def _conf_auth(app):
    extensions.auth.init_app(app)
    
    @app.context_processor
    def is_auth():
        return dict(is_logged=extensions.auth.authenticate())        
    
def _conf_mail(app):
    extensions.mail.init_app(app)

def _conf_processors(app):
    
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
    def collection_counters():
        col = current_app.widukind_db[constants.COL_COUNTERS]
        d = {}
        #{"category": "collection"}
        cursor = col.find({}, 
                          projection={'_id': False}) #, "name": True, "count": True})
        for r in cursor:
            d[r['name']] = r
            
        def counter(key):
            if key in d:
                return d[key]['count']
            else:
                return 0
        
        return dict(collection_counters=d, counter=counter)
    
    @app.context_processor
    def provider_list():
        #TODO: update or cache !!!
        providers = []
        projection = {"_id": False, "name": True, "long_name": True}
        for doc in app.widukind_db[constants.COL_PROVIDERS].find({}, projection=projection):
            providers.append({"name": doc['name'], "long_name": doc['long_name']})
        return dict(provider_list=providers)

    @app.context_processor
    def frequencies():
        def frequency(value):
            return constants.FREQUENCIES_DICT.get(value, "Unknow")
        return dict(frequency=frequency)
            
    @app.context_processor
    def convert_pandas_period():
        def convert(date, frequency):
            import pandas
            sd = pandas.Period(ordinal=date, freq=frequency)
            return str(sd)
        return dict(pandas_period=convert)
    
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
        providers = current_app.widukind_db[constants.COL_PROVIDERS].find({}, projection={'_id': False})
        for doc in providers:
            yield ('views.datasets', {'provider_name': doc['name']}, None, "weekly", 0.9)

    @extensions.sitemap.register_generator
    def sitemap_datasets():
        projection = {'_id': False, "last_update": True, "name": True, 'provider_name': True, "datasetCode": True } 
        datasets = current_app.widukind_db[constants.COL_DATASETS].find({}, projection=projection)
        for doc in datasets:
            yield ('views.series_with_datasetCode', 
                   {'provider_name': doc['provider_name'], 'datasetCode': doc['datasetCode']}, 
                   doc['last_update'], 
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
    
    @app.errorhandler(500)
    def error_500(error):
        is_json = request.args.get('json') or request.is_xhr
        values = dict(error="Server Error", original_error=error, referrer=request.referrer)
        if is_json:
            return app.jsonify(values), 500
        return render_template('errors/500.html', **values), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        is_json = request.args.get('json') or request.is_xhr
        values = dict(error="404 Error", original_error=error, referrer=request.referrer)
        if is_json:
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
    
    #_conf_themes(app)
    
    _conf_sentry(app)
    
    #if app.config.get('SESSION_ENGINE_ENABLE', False):
    #    from flask_mongoengine import MongoEngineSessionInterface
    #    app.session_interface = MongoEngineSessionInterface(extensions.db)
    
    _conf_errors(app)
    
    _conf_cache(app)
    
    _conf_converters(app)
    
    _conf_jsonify(app)
    
    _conf_default_views(app)
    
    _conf_bp(app)
    
    _conf_record_query(app)

    _conf_processors(app)
    
    _conf_auth(app)
    
    _conf_sitemap(app)
    
    _conf_session(app)
    
    _conf_mail(app)
    
    _conf_locker(app)
    
    if app.config.get('COUNTERS_ENABLE', True):        
        _conf_counters(app)
    
    app.wsgi_app = ProxyFix(app.wsgi_app)

    return app
