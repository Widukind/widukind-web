# -*- coding: utf-8 -*-

from flask_moment import Moment
from flask_cache import Cache
from flask_sitemap import Sitemap
from flask_basicauth import BasicAuth
from flask_mail import Mail

moment = Moment()

cache = Cache()

sitemap = Sitemap()

auth = BasicAuth()

mail = Mail()

try:
    from flask_babelex import Babel, lazy_gettext, gettext, _
    babel = Babel()
    #_ = lambda s: s
    #gettext = lambda s: s
except:
    _ = lambda s: s
    gettext = lambda s: s
    class Babel(object):
        def __init__(self, *args, **kwargs):
            pass
        def init_app(self, app):
            pass
    babel = Babel()

