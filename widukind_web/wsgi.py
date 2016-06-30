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
    
def _conf_db(app, db=None):
    import gridfs
    from widukind_common.utils import get_mongo_db
    from widukind_web.utils import create_or_update_indexes
    if not db:
        app.widukind_db = get_mongo_db(app.config.get("MONGODB_URL"), connect=False)
    else:
        app.widukind_db = db
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
    
    from widukind_web.views import home_views
    home_views(app)

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

    @app.context_processor
    def server_time():
        import arrow
        return dict(server_time=arrow.utcnow().to('local').format('YYYY-MM-DD HH:mm:ss ZZ'))
                
def _conf_bootstrap(app):
    from flask_bootstrap import WebCDN
    from flask_bootstrap import Bootstrap
    Bootstrap(app)

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
            yield ('views.explorer_p', {'provider': doc['slug']}, None, "weekly", 0.9)

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

    extensions.sitemap.decorators = []
    app.config['SITEMAP_VIEW_DECORATORS'] = [load_page]

    extensions.sitemap.init_app(app)
    
def _conf_bp(app):
    from widukind_web import views
    from widukind_web import admin
    app.register_blueprint(views.bp, url_prefix='/views')
    app.register_blueprint(admin.bp, url_prefix='/_cepremap/admin')

def _conf_errors(app):

    from werkzeug.exceptions import HTTPException

    class DisabledElement(HTTPException):
        code = 307
        description = 'Disabled element'
    abort.mapping[307] = DisabledElement

    @app.errorhandler(DisabledElement)
    def disable_error(error):
        is_json = request.args.get('json') or request.is_xhr
        values = dict(error="307 Error", original_error=error, referrer=request.referrer)
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
    
def _conf_assets(app):
    from flask_assets import Bundle
    assets = extensions.assets
    #app.debug = True
    assets.init_app(app)
    
    import os
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "static"))
    
    common_css = [
        #"local/bootstrap-3.3.6/css/bootstrap.min.css",
        #"local/bootstrap-3.3.6/css/bootstrap-theme.min.css",
        "themes/bootswatch/widukind/bootstrap.min.css", #3.3.6
        "local/font-awesome.min.css",
        #"widukind/style-light.css",
        "local/toastr.min.css",
    ]
    
    common_js = [
        "local/jquery.min.js",
        "local/bootstrap-3.3.6/js/bootstrap.min.js",
        "local/humanize.min.js",
        "local/lodash.min.js",
        "local/jquery.blockUI.min.js",
        "local/bootbox.min.js",
        "local/toastr.min.js",
        "widukind/scripts.js",
    ]

    table_css = [
        "local/bootstrap-table.min.css",
    ]    
    table_js = [
        "local/bootstrap-table.min.js",
        "local/bootstrap-table-cookie.min.js",
        "local/bootstrap-table-export.min.js",
        #"local/bootstrap-table-filter-control.min.js",
        #"local/bootstrap-table-filter.min.js",
        #"local/bootstrap-table-flat-json.min.js",
        "local/bootstrap-table-mobile.min.js",
        #"local/bootstrap-table-natural-sorting.min.js",
        #"local/bootstrap-table-toolbar.min.js",
        #"local/bootstrap-table-resizable.min.js",
        "local/bootstrap-table-en-US.min.js",
    ]
    
    form_css = [
        "local/awesome-bootstrap-checkbox.min.css",
        #"local/select2.min.css",
        #"local/select2-bootstrap.min.css",
        "local/daterangepicker.min.css",
        "local/formValidation.min.css",
        "local/chosen.min.css",
        "local/bootstrap-treeview.min.css",
    ] + table_css

    form_js = [
        #"local/select2.min.js",
        "local/daterangepicker.min.js",
        "local/formValidation.min.js",
        "local/formvalidation-bootstrap.min.js",
        "local/chosen.jquery.min.js",
        "local/mustache.min.js",
        "local/clipboard.min.js",
        "local/bootstrap-treeview.min.js",
        #"local/jquery.sparkline.min.js",
        #"local/dygraph-combined.js",
    ] + table_js

    #TODO: export    
    table_export_js = [
        'bootstrap-table/extensions/export/bootstrap-table-export.min.js',    
        'bootstrap-table/extensions/flat-json/bootstrap-table-flat-json.min.js',
        'bootstrap-table/extensions/toolbar/bootstrap-table-toolbar.js',
        'table-export/tableExport.js',
        'table-export/jquery.base64.js',
        'table-export/html2canvas.js',
        'table-export/jspdf/libs/sprintf.js',
        'table-export/jspdf/jspdf.js',
        'table-export/jspdf/libs/base64.js'
    ]
    
    for filename in common_css + common_js + form_css + form_js:
        filepath = os.path.abspath(os.path.join(STATIC_DIR, filename))
        if not os.path.exists(filepath):
            raise Exception("file not found [%s]" % filepath)
    
    #274Ko
    common_css_bundler = Bundle(*common_css, 
                                filters='cssmin',
                                #output='gen/common-%(version)s.css'
                                output='local/common.css'
                                )
    if not 'common_css' in assets._named_bundles:
        assets.register('common_css', common_css_bundler)
    
    #207Ko
    common_js_bundler = Bundle(*common_js,
                               filters='jsmin', 
                               output='local/common.js')
    if not 'common_js' in assets._named_bundles:
        assets.register('common_js', common_js_bundler)
    
    #49Ko
    if not 'form_css' in assets._named_bundles:
        assets.register('form_css', Bundle(*form_css,
                                           filters='cssmin', 
                                           output='local/form.css'))
    
    #505Ko
    if not 'form_js' in assets._named_bundles:
        assets.register('form_js', Bundle(*form_js, 
                                          filters='jsmin',
                                          output='local/form.js'))

    if not 'table_css' in assets._named_bundles:
        assets.register('table_css', Bundle(*table_css,
                                           filters='cssmin', 
                                           output='local/table.css'))

    if not 'table_js' in assets._named_bundles:
        assets.register('table_js', Bundle(*table_js,
                                           filters='jsmin', 
                                           output='local/table.js'))
    
    with app.app_context():
        assets.cache = True #not app.debug
        assets.manifest = 'cache' if not app.debug else False
        assets.debug = False #app.debug
        #print(assets['common_css'].urls())

def create_app(config='widukind_web.settings.Prod', db=None):
    
    env_config = config_from_env('WIDUKIND_SETTINGS', config)
    
    app = Flask(__name__)
    app.config.from_object(env_config)    

    _conf_db(app, db=db)

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
    
    _conf_assets(app)
    
    app.wsgi_app = ProxyFix(app.wsgi_app)
    
    return app
