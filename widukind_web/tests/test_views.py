# -*- coding: utf-8 -*-

import unittest
from datetime import datetime
from flask import url_for

from widukind_web.tests.base import TestCase, REFERENTIEL

class ViewsTestCase(TestCase):
    
    # nosetests -s -v widukind_web.tests.test_views:ViewsTestCase
    
    def setUp(self):
        super().setUp()
        self.fixtures()
        
    def test_views_ajax_providers_list(self):
        response = self.json_get(url_for('views.ajax-providers-list'))
        self.assertOkJson(response)
        response_json = self.response_json(response)
        self.assertEquals(len(response_json["data"]), REFERENTIEL["providers"]["count"])
        self.assertEquals(response_json["data"], 
                          [{'name': 'INSEE', 'slug': 'insee'}])
        
    def test_views_ajax_datasets_list(self):
        response = self.json_get(url_for('views.ajax-datasets-list', provider="NOTEXIST"))
        self.assert_404(response)
        
        response = self.json_get(url_for('views.ajax-datasets-list', provider="insee"))
        self.assertOkJson(response)
        response_json = self.response_json(response)
        self.assertEquals(len(response_json["data"]), REFERENTIEL["datasets"]["count"])
        self.assertEquals(response_json["data"], 
                          [{'dataset_code': 'IPCH-2015-FR-COICOP', 
                            'name': 'Harmonised consumer price index - Base 2015 - France - By product (COICOP classification)', 
                            'slug': 'insee-ipch-2015-fr-coicop',
                            'enable': True}])
        
    def test_views_ajax_datasets_dimensions_keys(self):
        response = self.json_get(url_for('views.ajax-datasets-dimensions-keys', 
                                         dataset='NOTEXIST'))
        self.assert_404(response)
        
        response = self.json_get(url_for('views.ajax-datasets-dimensions-keys', 
                                         dataset='insee-ipch-2015-fr-coicop'))
        self.assertOkJson(response)
        response_json = self.response_json(response)
        self.assertEquals(response_json["data"], 
                          [{'value': 'freq', 'text': 'Frequency'}, 
                           {'value': 'produit', 'text': 'Main product groups'}, 
                           {'value': 'nature', 'text': 'Nature of the series'}])
        
    def test_views_ajax_datasets_dimensions_all(self):
        response = self.json_get(url_for('views.ajax-datasets-dimensions-all', 
                                         dataset='NOTEXIST'))
        self.assert_404(response)
        
        response = self.json_get(url_for('views.ajax-datasets-dimensions-all', 
                                         dataset='insee-ipch-2015-fr-coicop'))
        self.assertOkJson(response)
        response_json = self.response_json(response)
        self.assertEquals(len(response_json["data"]), 3)
        #dimension_keys :  ['freq', 'produit', 'nature']
        self.assertEquals(response_json["data"][0], 
                          {'name': 'Frequency', 'key': 'freq', 'codes': {'m': 'Monthly', 'a': 'Annual'}})
        self.assertEquals(response_json["data"][-1], 
                          {'name': 'Nature of the series', 'key': 'nature', 'codes': {'pond': 'Weighting', 'indice': 'Index'}})
        
    def test_views_ajax_dataset_frequencies(self):
        response = self.json_get(url_for('views.ajax-datasets-frequencies', 
                                         dataset='NOTEXIST'))
        self.assert_404(response)
        
        response = self.json_get(url_for('views.ajax-datasets-frequencies', 
                                         dataset='insee-ipch-2015-fr-coicop'))
        self.assertOkJson(response)
        response_json = self.response_json(response)
        self.assertEquals(response_json["data"],
                          [{'text': 'Monthly', 'value': 'M'}])

    def test_views_dataset_with_slug(self):
        response = self.client.get(url_for('views.dataset-by-slug', 
                                         slug='NOTEXIST'))
        self.assert_404(response)

        response = self.client.get(url_for('views.dataset-by-slug', 
                                         slug='insee-ipch-2015-fr-coicop'))
        self.assertOkHtml(response)

        for name in ['is_modal', 
                     'url_provider', 'url_dataset', 'url_dataset_direct',
                     'dataset', 'provider']:
            self.assertContext(name)
            
        self.assert_template_used("dataset-unit-modal.html")
        
        dataset = self.get_context_variable('dataset')
        self.assertEquals(dataset["slug"],
                          'insee-ipch-2015-fr-coicop')

        self.assertContext("url_provider",
                           '/views/explorer/insee')

        self.assertContext("url_dataset",
                           '/views/explorer/dataset/insee-ipch-2015-fr-coicop')

        self.assertContext("url_dataset_direct",
                           'http://localhost/views/dataset/insee-ipch-2015-fr-coicop')

    def test_views_series_with_slug(self):
        response = self.client.get(url_for('views.series-by-slug', 
                                         slug='NOTEXIST'))
        self.assert_404(response)

        response = self.client.get(url_for('views.series-by-slug', 
                                         slug='insee-ipch-2015-fr-coicop-001759971'))
        
        self.assertOkHtml(response)

        for name in ['is_modal', 
                     'url_provider', 'url_dataset', 'url_dataset_direct', 'url_series',
                     'series', 'dataset', 'provider',
                     'dimension_filter']:
            self.assertContext(name)
        """
        TODO:
                    dimension_filter=dimension_filter.upper(),
                    is_reverse=is_reverse,
                    obs_attributes_keys=list(set(obs_attributes_keys)),
                    obs_attributes_values=list(set(obs_attributes_values)),
                    revision_dates=list(set(revision_dates)),
                    max_revisions=max_revisions        
        """
            
        self.assert_template_used("series-unit-modal.html")

        self.assertContext("url_provider",
                           '/views/explorer/insee')

        self.assertContext("url_dataset",
                           '/views/explorer/dataset/insee-ipch-2015-fr-coicop')

        self.assertContext("url_dataset_direct",
                           'http://localhost/views/dataset/insee-ipch-2015-fr-coicop')
        
        self.assertContext("url_series",
                           'http://localhost/views/series/insee-ipch-2015-fr-coicop-001759971')
        
        provider = self.get_context_variable('provider')
        self.assertEquals(provider["slug"],
                          'insee')

        dataset = self.get_context_variable('dataset')
        self.assertEquals(dataset["slug"],
                          'insee-ipch-2015-fr-coicop')

        series = self.get_context_variable('series')
        self.assertEquals(series["slug"],
                          'insee-ipch-2015-fr-coicop-001759971')
        
        self.assertEquals(series["values"][0],
                          {'ordinal': 312, 
                           'value': '74.1', 
                           'attributes': {'obs-status': 'a'}, 
                           'release_date': datetime(2016, 6, 2, 0, 0), 
                           'period': '1996-01'})
        
        self.assertEquals(series["values"][-1],
                          {'ordinal': 556, 
                           'value': '100.53', 
                           'attributes': {'obs-status': 'p'}, 
                           'release_date': datetime(2016, 6, 2, 0, 0), 
                           'period': '2016-05'})        

    def test_views_ajax_plot_series(self):
        response = self.json_get(url_for('views.ajax_series_plot', 
                                         slug='NOTEXIST'))
        self.assert_404(response)

        response = self.json_get(url_for('views.ajax_series_plot', 
                                         slug='insee-ipch-2015-fr-coicop-001759971'))
        self.assertOkJson(response)
        response_json = self.response_json(response)

        self.assertEquals(response_json["meta"],
                          {'name': 'Monthly - 00 - All items - Index', 
                           'dataset_code': 'IPCH-2015-FR-COICOP', 
                           'key': '001759971', 
                           'slug': 'insee-ipch-2015-fr-coicop-001759971', 
                           'provider_name': 'INSEE'}) 

        self.assertEquals(response_json["data"][0],
                          {'period_ts': '1996-01-01', 'period': '1996-01', 'value': '74.1'})
        self.assertEquals(response_json["data"][-1],
                          {'period_ts': '2016-05-01', 'period': '2016-05', 'value': '100.53'})        

    def test_views_tree_view(self):
        response = self.json_get(url_for('views.tree_root_base'))
        self.assert_404(response)
        
        response = self.json_get(url_for('views.tree_root_base', 
                                         provider='insee'))
        self.assertOk(response)
        self.assertContentType(response, 'application/javascript')
        self.assertInContext('provider')
        self.assertInContext('categories')
        self.assertInContext('dataset_codes')
        
        self.assert_template_used("datatree_ajax.html")
        
    @unittest.skipIf(True, "TODO")
    def test_views_ajax_tag_prefetch_series(self):
        pass
        #@bp.route('/ajax/tags/prefetch/series', endpoint="ajax-tag-prefetch-series")

    @unittest.skipIf(True, "TODO")
    def test_views_datasets_last_update(self):
        pass
        #@bp.route('/datasets/last-update.html', endpoint="datasets-last-update")

class ExplorerViewsTestCase(TestCase):
    
    # nosetests -s -v widukind_web.tests.test_views:ExplorerViewsTestCase
    
    def setUp(self):
        super().setUp()
        self.fixtures()

    @unittest.skipIf(True, "TODO")
    def test_views_ajax_explorer_datas(self):
        pass
        #@bp.route('/ajax/explorer/datas', endpoint="ajax-explorer-datas")

    @unittest.skipIf(True, "TODO")
    def test_views_explorer_view(self):
        pass
        #@bp.route('/explorer/dataset/<dataset>', endpoint='explorer_d')
        #@bp.route('/explorer/<provider>', endpoint="explorer_p")
        #@bp.route('/explorer/<provider>/<dataset>', endpoint='explorer_p_d')
        #@bp.route('/explorer', endpoint="explorer")
        #@bp.route('/', endpoint="home")

class CartViewsTestCase(TestCase):

    # nosetests -s -v widukind_web.tests.test_views:CartViewsTestCase
    
    def setUp(self):
        super().setUp()
        self.fixtures()

    @unittest.skipIf(True, "TODO")
    def test_views_ajax_cart_add(self):
        pass
        #@bp.route('/ajax/series/cart/add', endpoint="ajax-cart-add")
        #slug = request.args.get('slug')
        #cart = session.get("cart", [])
    
    @unittest.skipIf(True, "TODO")
    def test_views_ajax_cart_remove(self):
        pass
        #@bp.route('/ajax/series/cart/remove', endpoint="ajax-cart-remove")

    @unittest.skipIf(True, "TODO")
    def test_views_ajax_cart_view(self):
        pass
        #@bp.route('/ajax/series/cart/view', endpoint="ajax-cart-view")

class HomeViewsTestCase(TestCase):

    # nosetests -s -v widukind_web.tests.test_views:HomeViewsTestCase

    def setUp(self):
        super().setUp()
        self.fixtures()

    def test_views_index(self):
        #TODO: @cache.cached(timeout=3600) #1H
        #TODO: content_encoding', 'content_language
        response = self.client.get(url_for('home'))
        self.assertOkHtml(response)
        #self.assert_template_used("layout.html")
        self.assert_template_used("index.html")
        #self.assert_template_used("navbar.html")

    @unittest.skipIf(True, "TODO")
    def test_views_contact_form(self):
        pass
        #@bp_or_app.route('/contact', endpoint="contact", methods=['GET', 'POST'])

    @unittest.skipIf(True, "TODO")
    def test_views_atom_feed(self):
        pass
        #@bp_or_app.route('/rss.xml', endpoint="rss")

