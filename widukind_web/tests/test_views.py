# -*- coding: utf-8 -*-

from flask import url_for

from widukind_web.tests.base import TestCase

class ViewsTestCase(TestCase):
    
    # nosetests -s -v widukind_web
    
    """
    TODO:
        /                              home GET,
        
        /_cepremap/admin/cache/clear   admin.cache_clear GET,
        /_cepremap/admin/logs          admin.logs GET,
        /_cepremap/admin/queries       admin.queries GET,
        /download/                     download.index GET,
        /download/byid/<objectid:id>   download.download-file-by-id GET,
        /download/dataset/<provider>/<dataset_code> download.datasets_csv GET,
        /download/list/datasets        download.fs_list_dataset GET,
        /download/list/series          download.fs_list_series GET,
        /download/list/series/<provider> download.fs_list_series GET,
        /download/list/series/<provider>/<dataset_code> download.fs_list_series GET,
        /download/series/<provider>/<dataset_code>/<key> download.series_csv GET,

        /sitemap.xml                   flask_sitemap.sitemap GET,
        /sitemap<int:page>.xml         flask_sitemap.page GET,

        /views/categories/<provider>   views.categories GET,
        /views/dataset-by-id/<objectid:id> views.dataset GET,
        /views/datasets/<provider>     views.datasets GET,
        /views/last-datasets           views.last_datasets GET,
        /views/last-series             views.last_series GET,
        /views/plot/series/<objectid:id> views.series_plot GET,
        /views/providers               views.providers GET,
        /views/search/datasets         views.search_datasets GET,,POST
        /views/search/series           views.search_series GET,,POST
        /views/series-by-id/<objectid:id> views.serie GET,
        /views/series/<provider>       views.series GET,
        /views/series/<provider>/<dataset_code> views.series_with_dataset_code GET,
        /views/series/cart/add         views.card_add GET,
        /views/series/cart/view        views.card_view GET,
        /views/slug/dataset/<slug>     views.dataset-by-slug GET,
        /views/slug/series/<slug>      views.series-by-slug GET,
        /views/tags/prefetch/series    views.tag_prefetch_series GET,    
    """
        
    def test_urls(self):
        url = url_for("home")
        response = self.client.get(url)        
        self.assert200(response)
        self.assert_template_used('index.html')
        
        
