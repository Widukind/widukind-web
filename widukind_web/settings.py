# -*- coding: utf-8 -*-

from decouple import config
gettext = lambda s: s

class Config(object):
    
    BOOTSTRAP_SERVE_LOCAL = True
    
    DEFAULT_URL_API = "http://widukind-api.cepremap.org/api/v1"
    BASE_URL_API_JSON = config('WIDUKIND_BASE_URL_API_JSON', "%s/json" % DEFAULT_URL_API)
    BASE_URL_API_SDMX = config('WIDUKIND_BASE_URL_API_SDMX', "%s/sdmx" % DEFAULT_URL_API)

    GOOGLE_ANALYTICS_ID = config('WIDUKIND_WEB_GOOGLE_ANALYTICS_ID', None)
    
    PIWIK_ENABLE = config('WIDUKIND_PIWIK_ENABLE', False, cast=bool)
    PIWIK_URL = config('WIDUKIND_PIWIK_URL', None)
    PIWIK_SITE_ID = config('WIDUKIND_PIWIK_SITE_ID', 0, cast=int)
    
    CACHE_TYPE = config('WIDUKIND_CACHE_TYPE', "simple")
    CACHE_KEY_PREFIX = "widukind_web"
    ENABLE_CACHE = config('WIDUKIND_ENABLE_CACHE', True, cast=bool)
    ENABLE_REDIS = config('WIDUKIND_ENABLE_REDIS', True, cast=bool)
    
    CACHE_REDIS_URL = config('WIDUKIND_REDIS_URL', 'redis://localhost:6379/0')
    if ENABLE_CACHE and ENABLE_REDIS:
        CACHE_TYPE = "redis"
        CACHE_REDIS_URL = config('WIDUKIND_REDIS_URL', 'redis://localhost:6379/0')
    
    MONGODB_URL = config('WIDUKIND_MONGODB_URL', 'mongodb://localhost/widukind')
    
    SECRET_KEY = config('WIDUKIND_SECRET_KEY', 'very very secret key key key')
    
    DEBUG = config('WIDUKIND_DEBUG', False, cast=bool)
        
    SENTRY_DSN = config('WIDUKIND_SENTRY_DSN', None)
    
    SESSION_ENGINE_ENABLE = config('WIDUKIND_SESSION_ENGINE_ENABLE', False, cast=bool)

    COUNTERS_ENABLE = config('WIDUKIND_COUNTERS_ENABLE', True, cast=bool)
    
    DEFAULT_THEME = config('WIDUKIND_THEME', 'darkly')
    
    #---Flask-Babel
    TIMEZONE = "UTC"#"Europe/Paris" 
    DEFAULT_LANG = "en"
    ACCEPT_LANGUAGES = ['en', 'fr']
    
    ACCEPT_LANGUAGES_CHOICES = (
        ('en', gettext('English')),
        ('fr', gettext('French')),
    )
    
    BABEL_DEFAULT_LOCALE = DEFAULT_LANG
    BABEL_DEFAULT_TIMEZONE = TIMEZONE
    
    #SITEMAP_URL_METHOD = "http"
    SITEMAP_GZIP = False
    #SITEMAP_MAX_URL_COUNT = 10000
    SITEMAP_INCLUDE_RULES_WITHOUT_PARAMS = False #not True
    FULL_URL_SITEMAP = config('WIDUKIND_WEB_FULL_URL_SITEMAP', "http://widukind.cepremap.org")
    #SITEMAP_URL_SCHEME = None
    
    SEARCH_MIN = config('WIDUKIND_WEB_SEARCH_MIN', 1, cast=int)
    SEARCH_MAX = config('WIDUKIND_WEB_SEARCH_MAX', 1000, cast=int)
    
    #---Flask-Basic-Auth
    BASIC_AUTH_USERNAME = config('WIDUKIND_WEB_USERNAME', 'admin')
    BASIC_AUTH_PASSWORD = config('WIDUKIND_WEB_PASSWORD', 'admin')
    BASIC_AUTH_REALM = ''

    #---Mongo Logging Handler    
    LOGGING_MONGO_ENABLE = config('WIDUKIND_WEB_LOGGING_MONGO_ENABLE', True, cast=bool)
    LOGGING_MAIL_ENABLE = config('WIDUKIND_WEB_LOGGING_MAIL_ENABLE', False, cast=bool)

    MAIL_ADMINS = config('WIDUKIND_WEB_MAIL_ADMIN', "root@localhost.com")
    
    #---Flask-Mail
    MAIL_SERVER = config('WIDUKIND_WEB_MAIL_SERVER', "127.0.0.1")
    MAIL_PORT = config('WIDUKIND_WEB_MAIL_PORT', 25, cast=int)
    MAIL_USE_TLS = config('WIDUKIND_WEB_MAIL_USE_TLS', False, cast=bool)
    MAIL_USE_SSL = config('WIDUKIND_WEB_MAIL_USE_SSL', False, cast=bool)
    #MAIL_DEBUG : default app.debug
    MAIL_USERNAME = config('WIDUKIND_MAIL_USERNAME', None)
    MAIL_PASSWORD = config('WIDUKIND_MAIL_PASSWORD', None)
    MAIL_DEFAULT_SENDER = config('WIDUKIND_MAIL_DEFAULT_SENDER', "root@localhost.com")
    MAIL_MAX_EMAILS = None
    #MAIL_SUPPRESS_SEND : default app.testing
    MAIL_ASCII_ATTACHMENTS = False
    
class Prod(Config):
    pass

class Dev(Config):
    
    BOOTSTRAP_USE_MINIFIED = False

    MONGODB_URL = config('WIDUKIND_MONGODB_URL', 'mongodb://localhost/widukind_dev')

    DEBUG = True

    SECRET_KEY = 'dev_key'
    
    MAIL_DEBUG = True
    
    #---debugtoolbar
    """
    DEBUG_TB_ENABLED = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    DEBUG_TB_PANELS = [
        'flask_debugtoolbar.panels.versions.VersionDebugPanel',
        'flask_debugtoolbar.panels.timer.TimerDebugPanel',
        'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
        'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
        'flask_debugtoolbar.panels.template.TemplateDebugPanel',
        'flask_debugtoolbar.panels.logger.LoggingPanel',
        'flask_debugtoolbar.panels.profiler.ProfilerDebugPanel',
        #'flask.ext.mongoengine.panels.MongoDebugPanel',
    ]
    DEBUG_TB_TEMPLATE_EDITOR_ENABLED = True
    """

    
class Test(Config):

    MONGODB_URL = config('WIDUKIND_MONGODB_URL', 'mongodb://localhost/widukind_test')
    
    COUNTERS_ENABLE = False

    TESTING = True    
    
    SECRET_KEY = 'test_key'
    
    WTF_CSRF_ENABLED = False
    
    PROPAGATE_EXCEPTIONS = True
    
    CACHE_TYPE = "null"
    
    MAIL_SUPPRESS_SEND = True
    

class Custom(Config):
    pass

