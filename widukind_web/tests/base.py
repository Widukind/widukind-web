# -*- coding: utf-8 -*-

import os

from unittest import mock
from flask_testing import TestCase as BaseTestCase

class TestCase(BaseTestCase):
    
    ENVIRON = {
               
    }
    
    def _set_environ(self):
        return self.ENVIRON

    @mock.patch.dict(os.environ)
    def setUp(self):
        BaseTestCase.setUp(self)
        os.environ.update(self._set_environ())

    def create_app(self):
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app