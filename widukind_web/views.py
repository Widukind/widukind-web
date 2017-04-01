# -*- coding: utf-8 -*-

from pprint import pprint
from collections import OrderedDict
from io import StringIO
import csv

from jinja2 import Markup
from flask import (Blueprint,
                   current_app,
                   request,
                   render_template,
                   render_template_string,
                   url_for,
                   session,
                   flash,
                   jsonify,
                   redirect,
                   abort)

from flask_mail import Message
from werkzeug.wsgi import wrap_file

import arrow
from slugify import slugify

from pymongo import ASCENDING, DESCENDING

from widukind_common.utils import series_archives_load
from widukind_common.flask_utils import json_tools

from widukind_web import constants
from widukind_web.extensions import cache, mail
from widukind_web import queries

bp = Blueprint('views', __name__)

def complex_queries_series(query={}):

    """
    startDate = arrow.get(request.args.get('startDate')).floor('day').datetime
    endDate = arrow.get(request.args.get('endDate')).ceil('day').datetime
    """

    search_fields = []
    query_and = []

    for r in request.args.lists():
        if r[0] in ['limit', 'tags', 'provider', 'dataset', 'search', 'period']:
            continue
        elif r[0] == 'frequency':
            query['frequency'] = r[1][0]
        elif r[0].startswith('dimensions_'):
            field_name = r[0].split('dimensions_')[1]
            search_fields.append((field_name, r[1][0]))
        else:
            msg = "unknow field[%s]" % r[0]
            current_app.logger.warn(msg)

    tags = request.args.get('tags')

    if search_fields:

        query_or_by_field = {}
        query_nor_by_field = {}

        for field, value in search_fields:
            values = value.split()
            value = [v.lower().strip() for v in values]

            dim_field = field.lower()

            for v in value:
                if v.startswith("!"):
                    if not dim_field in query_nor_by_field:
                        query_nor_by_field[dim_field] = []
                    query_nor_by_field[dim_field].append(v[1:])
                else:
                    if not dim_field in query_or_by_field:
                        query_or_by_field[dim_field] = []
                    query_or_by_field[dim_field].append(v)

        for key, values in query_or_by_field.items():
            q_or = {"$or": [
                {"dimensions.%s" % key: {"$in": values}},
            ]}
            query_and.append(q_or)

        for key, values in query_nor_by_field.items():
            q_or = {"$nor": [
                {"dimensions.%s" % key: {"$in": values}},
            ]}
            query_and.append(q_or)

    if query_and:
        query["$and"] = query_and

    if tags and len(tags.split()) > 0:
        tags = list(set(tags.split()))
        query["tags"] = {"$all": tags}
        #conditions = [{"tags": {"$regex": ".*%s.*" % value.lower()}} for value in tags]
        #query_and.append({"": conditions})
        #query_and.append({"$and": conditions})


    print("-----complex query-----")
    pprint(query)
    print("-----------------------")

    return query

def datas_from_series(series):

    import pandas

    for value in series["values"]:
        yield value["period"], pandas.Period(value["period"], freq=series['frequency']).to_timestamp().strftime("%Y-%m-%d"), value["value"]

@bp.route('/ajax/providers', endpoint="ajax-providers-list")
@cache.cached(timeout=3600) #1H
def ajax_providers_list():
    query = {"enable": True}
    projection = {"_id": False, "slug": True, "name": True}
    docs = [doc for doc in queries.col_providers().find(query, projection).sort("name", ASCENDING)]
    return json_tools.json_response(docs)

@bp.route('/ajax/providers/<provider>/datasets', endpoint="ajax-datasets-list")
def ajax_datasets_list(provider):
    """
    TODO: covered query
        provider_name + enable + dataset_code + name + slug ???
        partialfilter sur enable = True
    """
    provider_doc = queries.get_provider(provider)
    query = {'provider_name': provider_doc["name"]}

    projection = {"_id": False, "enable": True,
                  "dataset_code": True, "name": True, "slug": True}

    is_meta = request.args.get('is_meta', type=int, default=0) == 1
    if is_meta:
        projection["metadata"] = True

    docs = [doc for doc in queries.col_datasets().find(query, projection) if doc["enable"] is True]
    return json_tools.json_response(docs)

@bp.route('/ajax/datasets/<dataset>/dimensions/keys', endpoint="ajax-datasets-dimensions-keys")
def ajax_datasets_dimensions_keys(dataset):
    projection = {"_id": False, 'enable': True, "dimension_keys": True, "concepts": True}
    doc = queries.get_dataset(dataset, projection)

    dimensions = []
    for key in doc["dimension_keys"]:
        if key in doc["concepts"]:
            dimensions.append({"value": key, "text": doc["concepts"][key] })
        else:
            dimensions.append({"value": key, "text": key })
    return json_tools.json_response(dimensions)

@bp.route('/ajax/datasets/<dataset>/dimensions/all', endpoint="ajax-datasets-dimensions-all")
def ajax_datasets_dimensions_all(dataset):
    projection = {"_id": False, "enable": True, "dimension_keys": True, "concepts": True, "codelists": True}
    doc = queries.get_dataset(dataset, projection)

    dimensions = []
    for key in doc["dimension_keys"]:
        if key in doc["codelists"] and doc["codelists"][key]:
            dimensions.append({
                "key": key,
                "name": doc["concepts"].get(key) or key,
                "codes": doc["codelists"][key],
            })
    return json_tools.json_response(dimensions)

@bp.route('/ajax/dataset/<dataset>/frequencies', endpoint="ajax-datasets-frequencies")
def ajax_dataset_frequencies(dataset):
    projection = {"_id": False, "lock": False, "tags": False}
    doc = queries.get_dataset(dataset, projection)
    query = {"provider_name": doc["provider_name"],
             "dataset_code": doc["dataset_code"]}

    if "metadata" in doc and doc["metadata"].get("frequencies"):
        frequencies = doc["metadata"].get("frequencies")
    else:
        frequencies = queries.col_series().distinct("frequency", filter=query)

    freqs = []
    for freq in frequencies:
        if freq in constants.FREQUENCIES_DICT:
            freqs.append({"value": freq, "text": constants.FREQUENCIES_DICT[freq]})
        else:
            freqs.append({"value": freq, "text": freq})
    return json_tools.json_response(freqs)

@bp.route('/slug/dataset/<slug>')
@bp.route('/dataset/<slug>', endpoint="dataset-by-slug")
def dataset_with_slug(slug):

    dataset = queries.get_dataset(slug, {"_id": False})
    is_modal = request.args.get('modal', default=0, type=int)

    provider = queries.col_providers().find_one({"name": dataset['provider_name']},
                                                {"metadata": False})

    #count_series = queries.col_series().count({"provider_name": dataset['provider_name'],
    #                                           "dataset_code": dataset['dataset_code']})

    url_provider = url_for('.explorer_p', provider=provider["slug"])
    url_dataset = url_for('.explorer_d', dataset=dataset["slug"])
    url_dataset_direct = url_for('.dataset-by-slug', slug=dataset["slug"], _external=True)

    return render_template("dataset-unit-modal.html",
                           is_modal=is_modal,
                           url_provider=url_provider,
                           url_dataset=url_dataset,
                           url_dataset_direct=url_dataset_direct,
                           dataset=dataset,
                           provider=provider,
                           #count=count_series
                           )

"""
@bp.route('/series/<slug>/<int:version>', endpoint="ajax-series-archives-by-slug")
def ajax_series_archives(slug, version):

    query = {"slug": slug, "version": version}

    series = queries.col_series_archives().find_one(query)

    if not series:
        abort(404)
"""

@bp.route('/slug/series/<slug>', defaults={'version': -1})
@bp.route('/series/<slug>', endpoint="series-by-slug", defaults={'version': -1})
@bp.route('/series/<slug>/<int:version>', endpoint="series-by-slug-version")
def series_with_slug(slug, version):
    """
    Dans tous les cas:
    - charger la version latest
    - charger toutes les révisions antérieurs à la version latest
    """

    is_modal = request.args.get('modal', default=0, type=int)
    is_debug = request.args.get('debug')
    #_version = request.args.get('version', default="latest")
    is_latest = True
    query = {"slug": slug}

    '''Load always latest series from col series'''
    series_latest = queries.col_series().find_one(query)
    if not series_latest:
        abort(404)

    if version >= 0 and version != series_latest['version']:
        query['version'] = version
        store = queries.col_series_archives().find_one(query)
        if not store:
            abort(404)
        series = series_archives_load(store)
        is_latest = False
    else:
        series = series_latest

    provider = queries.col_providers().find_one({"name": series_latest['provider_name']},
                                                {"metadata": False})
    if not provider:
        abort(404)
    if provider["enable"] is False:
        abort(307)

    dataset = queries.col_datasets().find_one({'provider_name': series_latest['provider_name'],
                                               "dataset_code": series_latest['dataset_code']},
                                              {"metadata": False})
    if not dataset:
        abort(404)
    if dataset["enable"] is False:
        abort(307)

    if is_debug:
        '''debug mode'''
        result_provider = render_template_string("{{ provider|pprint|safe }}", provider=provider)
        result_dataset = render_template_string("{{ dataset|pprint|safe }}", dataset=dataset)
        result_series = render_template_string("{{ series|pprint|safe }}", series=series)
        return current_app.jsonify(dict(provider=result_provider,
                                        dataset=result_dataset,
                                        series=result_series))

    '''Load revisions < current version'''
    revisions = []
    if "version" in series:
        query_revisions = {"slug": slug, "version": {"$lt": series["version"]}}
        count_values = len(series['values'])
        for store in queries.col_series_archives().find(query_revisions).sort('version', DESCENDING):
            series_rev = series_archives_load(store)
            values = series_rev['values']

            empty_element = count_values - len(values)
            values.reverse()

            for i in range(empty_element):
                values.insert(0, None)

            revisions.append({
                "last_update_ds": series_rev['last_update_ds'],
                "version": series_rev['version'],
                "values": values,
                "name": series_rev["name"],
                "url": url_for('.series-by-slug-version', slug=slug, version=series_rev['version'])})
    else:
        series["version"] = 0

    if not "last_update_ds" in series:
        series["last_update_ds"] = dataset["last_update"]
        series["last_update_widu"] = dataset["last_update"]

    #view_explorer = url_for('.explorer_s', series=slug, _external=True)
    url_provider = url_for('.explorer_p', provider=provider["slug"])
    url_dataset = url_for('.explorer_d', dataset=dataset["slug"])
    url_dataset_direct = url_for('.dataset-by-slug', slug=dataset["slug"], _external=True)
    url_series = url_for('.series-by-slug-version', slug=slug, version=series["version"], _external=True)
    url_series_latest = url_for('.series-by-slug-version', slug=slug, version=series_latest["version"])
    url_series_plot = url_for('.ajax_series_plot', slug=slug)
    url_export_csv = url_for('.export-series-csv', slug=slug)

    dimension_filter = ".".join([series["dimensions"][key] for key in dataset["dimension_keys"]])

    result = render_template(
                    "series-unit-modal.html",
                    url_provider=url_provider,
                    url_dataset=url_dataset,
                    url_dataset_direct=url_dataset_direct,
                    url_series=url_series,
                    url_series_latest=url_series_latest,
                    url_series_plot=url_series_plot,
                    url_export_csv=url_export_csv,
                    series=series,
                    is_modal=is_modal,
                    provider=provider,
                    dataset=dataset,
                    is_latest=is_latest,
                    revisions=revisions,
                    #max_version=max_version,
                    #view_explorer=view_explorer,
                    dimension_filter=dimension_filter.upper(),
                    #is_reverse=is_reverse,
                    #obs_attributes_keys=list(set(obs_attributes_keys)),
                    #obs_attributes_values=list(set(obs_attributes_values)),
                    #revision_dates=list(set(revision_dates)),
                    #max_revisions=max_revisions
                    )

    return result

@bp.route('/ajax/plot/series/<slug>', endpoint="ajax_series_plot")
def ajax_plot_series(slug):

    series = queries.col_series().find_one({"slug": slug})

    if not series:
        abort(404)

    ds_projection = {"enable": True}
    dataset = queries.col_datasets().find_one({"provider_name": series["provider_name"],
                                               "dataset_code": series["dataset_code"]},
                                              ds_projection)
    if not dataset:
        abort(404)
    if dataset["enable"] is False:
        abort(307)

    meta = {
        "provider_name": series["provider_name"],
        "dataset_code": series["dataset_code"],
        "name": series["name"],
        "key": series["key"],
        "slug": series["slug"],
    }
    datas = []
    #datas.append(("Dates", "Values"))
    for period, period_ts, value in datas_from_series(series):
        datas.append({"period": period, "period_ts": str(period_ts), "value": value})

    return json_tools.json_response(datas, meta)

@bp.route('/tree', endpoint="tree_root_base")
def ajax_tree_view(provider=None):

    provider = provider or request.args.get('provider')
    if not provider:
        abort(404, "provider is required")

    _provider = queries.get_provider(provider)
    provider_name = _provider["name"]

    query = {"provider_name": provider_name,
             "enable": True}
    cursor = queries.col_categories().find(query, {"_id": False})
    cursor = cursor.sort([("position", 1), ("category_code", 1)])

    categories = OrderedDict([(doc["category_code"], doc ) for doc in cursor])
    ds_codes = []

    for_remove = []
    for cat in categories.values():
        if cat.get("parent"):
            parent = categories[cat.get("parent")]
            if not "children" in parent:
                parent["children"] = []
            parent["children"].append(cat)
            for_remove.append(cat["category_code"])
        if cat.get("datasets"):
            for ds in cat.get("datasets"):
                ds_codes.append(ds["dataset_code"])

    for r in for_remove:
        categories.pop(r)

    ds_query = {'provider_name': provider_name,
                "enable": True,
                "dataset_code": {"$in": list(set(ds_codes))}}
    ds_projection = {"_id": True, "dataset_code": True, "slug": True}
    cursor = queries.col_datasets().find(ds_query, ds_projection)

    dataset_codes = {}
    for doc in cursor:
        dataset_codes[doc['dataset_code']] = {
            "slug": doc['slug'],
            "url": url_for('.dataset-by-slug', slug=doc["slug"])
        }

    context = dict(
        provider=_provider,
        categories=categories,
        dataset_codes=dataset_codes
    )

    data = render_template("datatree_ajax.html", **context)
    response = current_app.response_class(data,
                            mimetype='application/javascript')
    response.status_code = 200
    response.make_conditional(request)
    return response

@bp.route('/ajax/series/cart/add', endpoint="ajax-cart-add")
def ajax_cart_add():
    slug = request.args.get('slug')
    cart = session.get("cart", [])

    if not slug in cart:
        cart.append(slug)
        msg = {"msg": "Series add to cart.", "category": "success"}
    else:
        msg = {"msg": "Series is already in the cart.", "category": "warning"}

    session["cart"] = cart
    return current_app.jsonify(dict(notify=msg, count=len(session["cart"])))

@bp.route('/ajax/series/cart/remove', endpoint="ajax-cart-remove")
def ajax_cart_remove():
    slug = request.args.get('slug')
    is_all = slug == "all"
    cart = session.get("cart", [])
    if is_all:
        cart = []
        msg = {"msg": "All series deleted in cart.", "category": "success"}
    else:
        if slug in cart:
            cart.remove(slug)
            msg = {"msg": "Series remove from cart.", "category": "success"}
        else:
            msg = {"msg": "Series not in the cart.", "category": "warning"}
    session["cart"] = cart
    return current_app.jsonify(dict(notify=msg, count=len(session["cart"])))

@bp.route('/ajax/series/cart/view', endpoint="ajax-cart-view")
def ajax_cart_view():

    is_ajax = request.args.get('json') #or request.is_xhr

    if not is_ajax:
        return render_template("series-cart.html")

    datas = {"rows": None, "total": 0}

    projection = {
        "dimensions": False,
        "attributes": False,
        "release_dates": False,
        "revisions": False,
        "values": False,
    }
    cart = session.get("cart", None)

    if cart:
        series_slug = [c for c in cart]
        series = queries.col_series().find({"slug": {"$in": series_slug}},
                                                    projection=projection)

        docs = list(series)
        for s in docs:
            if not "version" in s:
                s["version"] = 0
            s['view'] = url_for('.series-by-slug', slug=s['slug'], modal=1)

            dataset_slug = slugify("%s-%s" % (s["provider_name"],
                                              s["dataset_code"]),
                            word_boundary=False, save_order=True)

            s['view_dataset'] = url_for('.dataset-by-slug', slug=dataset_slug, modal=1)
            s['dataset_slug'] = dataset_slug
            s['export_csv'] = url_for('.export-series-csv', slug=s['slug'])
            s['url_series_plot'] = url_for('.ajax_series_plot', slug=s['slug'])
            s['url_cart_remove'] = url_for('.ajax-cart-remove', slug=s['slug'])
            s['frequency_txt'] = s['frequency']
            if s['frequency'] in constants.FREQUENCIES_DICT:
                s['frequency_txt'] = constants.FREQUENCIES_DICT[s['frequency']]

        datas["rows"] = docs

    return current_app.jsonify(datas["rows"])

@bp.route('/ajax/tags/prefetch/series', endpoint="ajax-tag-prefetch-series")
def ajax_tag_prefetch_series():

    provider = request.args.get('provider')
    if not provider:
        abort(400, "provider is required")
    dataset = request.args.get('dataset')
    limit = request.args.get('limit', default=200, type=int)
    count = request.args.get('count', default=0, type=int)

    col = current_app.widukind_db[constants.COL_TAGS]

    #TODO: renvoyer aussi count pour tag(count)
    query = OrderedDict()
    query["provider_name"] = {"$in": [provider.upper()]}
    if dataset:
        query["datasets"] = {"$in": [dataset]}
    if count:
        query["count"] = {"$gte": count}

    projection = {"_id": False, "name": True, "count": True, "count_datasets": True, "count_series": True}
    docs = col.find(query, projection=projection).sort("count", DESCENDING).limit(limit)
    return current_app.jsonify(list(docs))

@bp.route('/ajax/explorer/datas', endpoint="ajax-explorer-datas")
def ajax_explorer_datas():

    limit = request.args.get('limit', default=100, type=int)
    if limit > 1000:
        limit = 1000

    #7 669 115 octets pour 1000 series

    projection = {
        "_id": False,
        "dimensions": False,
        "attributes": False,
        "values.revisions": False,
        "notes": False,
        "tags": False
    }

    query = OrderedDict()
    provider_slug = request.args.get('provider')
    dataset_slug = request.args.get('dataset')
    #series_slug = request.args.get('series')
    search = request.args.get('search')

    is_eurostat = False
    if dataset_slug:
        dataset = queries.get_dataset(dataset_slug)
        query["provider_name"] = dataset["provider_name"]
        #query["dataset_code"] = dataset["dataset_code"]
        if dataset["provider_name"] == "EUROSTAT":
            is_eurostat = True
    elif provider_slug:
        provider = queries.get_provider(provider_slug)
        query["provider_name"] = provider["name"]
        if provider["name"] == "EUROSTAT":
            is_eurostat = True

    if search:
        query["$text"] = {"$search": search.strip()}
        projection['score'] = {'$meta': 'textScore'}

    disabled_datasets = []
    if dataset_slug:
        query["dataset_code"] = dataset["dataset_code"]
    else:
        ds_enabled_query = {"enable": False}
        if "provider_name" in query:
            ds_enabled_query["provider_name"] = query["provider_name"]
        disabled_datasets = [doc["dataset_code"] for doc in queries.col_datasets().find(ds_enabled_query,
                                                                                        {"dataset_code": True})]

    query = complex_queries_series(query)
    cursor = queries.col_series().find(dict(query), projection)

    if search:
        cursor = cursor.sort([('score', {'$meta': 'textScore'})])

    #else:
    #    query = {"slug": series_slug}
    #    cursor = queries.col_series().find(dict(query), projection)

    if limit:
        cursor = cursor.limit(limit)

    if is_eurostat:
        count = 0
    else:
        count = cursor.count()

    series_list = [doc for doc in cursor]

    rows = []

    for s in series_list:
        if disabled_datasets and s["dataset_code"] in disabled_datasets:
            continue

        if not "version" in s:
            s["version"] = 0

        s['start_date'] = s["values"][0]["period"]
        s['end_date'] = s["values"][-1]["period"]
        values = [{"period": v["period"], "value": v["value"]} for v in s['values']]
        del s["values"]
        s["values"] = values

        s['view'] = url_for('.series-by-slug', slug=s['slug'], modal=1)

        dataset_slug = slugify("%s-%s" % (s["provider_name"],
                                          s["dataset_code"]),
                        word_boundary=False, save_order=True)

        s['view_dataset'] = url_for('.dataset-by-slug', slug=dataset_slug, modal=1)

        #s["view_explorer"] = url_for('.explorer_s', series=s['slug'], _external=True)

        s['dataset_slug'] = dataset_slug
        s['export_csv'] = url_for('.export-series-csv', slug=s['slug'])
        s['url_series_plot'] = url_for('.ajax_series_plot', slug=s['slug'])
        s['url_cart_add'] = url_for('.ajax-cart-add', slug=s['slug'])
        #TODO: s['url_dataset'] = url_for('.dataset', id=s['_id'])
        s['frequency_txt'] = s['frequency']
        if s['frequency'] in constants.FREQUENCIES_DICT:
            s['frequency_txt'] = constants.FREQUENCIES_DICT[s['frequency']]

        rows.append(s)

    return json_tools.json_response(rows, {"total": count})

@bp.route('/explorer/dataset/<dataset>', endpoint='explorer_d')
@bp.route('/explorer/<provider>', endpoint="explorer_p")
@bp.route('/explorer/<provider>/<dataset>', endpoint='explorer_p_d')
@bp.route('/explorer', endpoint="explorer")
@bp.route('/', endpoint="home")
def explorer_view(provider=None, dataset=None, series=None):
    """
    http://127.0.0.1:8081/views/explorer/dataset/insee-cna-2005-ere-a88
    http://127.0.0.1:8081/views/explorer/insee
    http://127.0.0.1:8081/views/explorer/insee/insee-cna-2005-ere-a88
    http://127.0.0.1:8081/views/explorer
    http://127.0.0.1:8081/views
    """

    if not dataset and not provider:
        provider = current_app.config.get('DEFAULT_PROVIDER', None)
        dataset = current_app.config.get('DEFAULT_DATASET', None)

    if dataset:
        doc = queries.get_dataset(dataset)
        # provider_doc = queries.col_providers().find_one({"name": doc["provider_name"]},{"slug": True})
        provider = doc["provider_name"].lower()
    elif provider:
        provider_doc = queries.get_provider(provider, {"slug": True, "name": True, "enable": True})
        dataset_doc = queries.col_datasets().find_one(
            {"provider_name": provider_doc["name"], "enable": True},
            {"slug": True},
            )
        dataset = dataset_doc["slug"]

    ctx = {
        "selectedProvider": provider,
        "selectedDataset": dataset,
    }
    return render_template("explorer.html", **ctx)

def send_file_csv(fileobj, mimetype=None, content_length=0):

    data = wrap_file(request.environ, fileobj, buffer_size=1024*256)
    response = current_app.response_class(
                        data,
                        mimetype=mimetype,
                        )
    response.status_code = 200
    response.make_conditional(request)
    return response

@bp.route('/export/series', endpoint="export-series-csv-base")
@bp.route('/export/series/<slug>', endpoint="export-series-csv")
def export_series_csv(slug=None):
    """
    http://127.0.0.1:8081/views/export/series/insee-ipch-2015-fr-coicop-001759971
    http://127.0.0.1:8081/views/export/series/insee-ipch-2015-fr-coicop-001759971+insee-ipch-2015-fr-coicop-001762151
    http://127.0.0.1:8081/views/export/series/insee-ipch-2015-fr-coicop-001759971+bis-cbs-q-s-5a-4b-f-b-a-a-lc1-a-1c
    """

    if not slug:
        slug = request.args.get('slug')

    if not slug:
        abort(404, "slug is required parameter")

    if "+" in slug:
        query = {'slug': {"$in": slug.split("+")}}
    else:
        query = {'slug': slug}

    series_list = [doc for doc in queries.col_series().find(query, {"tags": False, "notes": False})]

    #ds_slugs = []
    #for doc in series_list:
    #    dataset_slug = slugify("%s-%s" % (doc["provider_name"], doc["dataset_code"]), word_boundary=False, save_order=True)
    #    ds_slugs.append(dataset_slug)
    #    doc["dataset_slug"] = dataset_slug

    #datasets = {ds['slug']: ds for ds in queries.col_datasets().find({"slug": {"$in": ds_slugs}})}

    fp = StringIO()
    writer = csv.writer(fp, quoting=csv.QUOTE_NONNUMERIC)

    headers = ["provider", "dataset_code", "key", "slug", "name", "frequency", "period", "value"]
    values = []
    for doc in series_list:
        #dataset_slug = doc["dataset_slug"]
        if not "version" in doc:
            doc["version"] = 0
        provider_name = doc["provider_name"]
        dataset_code = doc["dataset_code"]
        key = doc["key"]
        slug = doc["slug"]
        name = doc["name"]
        frequency = doc["frequency"]

        """
        _dimensions = []
        for dim, dim_key in doc["dimensions"].items():
            dim_title = datasets[dataset_slug]["concepts"].get(dim, dim)
            dim_value = datasets[dataset_slug]["codelists"].get(dim, {}).get(dim_key, dim_key)
            if not dim_title in headers:
                headers.append(dim_title)
            _dimensions.append(dim_value)
        """

        for val in doc['values']:
            values.append([
                provider_name,
                dataset_code,
                key,
                slug,
                name,
                frequency,
                val["period"],
                val["value"],
            ]# + _dimensions
            )


    writer.writerow(headers)
    writer.writerows(values)

    fp.seek(0)

    return send_file_csv(fp, mimetype='text/csv')


@bp.route('/datasets/last-update.html', endpoint="datasets-last-update")
def datasets_last_update():

    is_ajax = request.args.get('json') or request.is_xhr
    if not is_ajax:
        return render_template("datasets-last-update.html")

    query = {
        "$or": [{"count_inserts": {"$gt": 0}}, {"count_updates": {"$gt": 0}}]
    }

    startDate = arrow.utcnow().replace(days=-1).floor("second")
    query["created"] = {"$gte": startDate.datetime}

    limit = request.args.get('limit', default=0, type=int)

    cursor = queries.col_stats_run().find(query)
    if limit:
        cursor = cursor.limit(limit)
    count = cursor.count()
    cursor = cursor.sort("created", -1)
    rows = [doc for doc in cursor]
    for row in rows:
        slug = slugify("%s-%s" % (row["provider_name"], row["dataset_code"]),
                        word_boundary=False, save_order=True)
        row["view"] = url_for(".explorer_d", dataset=slug)

    return json_tools.json_response(rows, {"total": count})

def home_views(bp_or_app):

    @bp_or_app.route('/', endpoint="home")
    def index():

        cursor = queries.col_providers().find({}, {"metadata": False})
        providers = [doc for doc in cursor]

        total_datasets = 0
        total_series = 0
        datas = {}
        for provider in providers:
            #provider["count_datasets"] = queries.col_datasets().count({"provider_name": provider["name"]})
            #provider["count_series"] = queries.col_series().count({"provider_name": provider["name"]})
            datas[provider["slug"]] = provider
            #total_datasets += provider["count_datasets"]
            #total_series += provider["count_series"]

        return render_template("index.html",
                               providers=datas,
                               total_datasets=total_datasets,
                               total_series=total_series
                               )

    @bp_or_app.route('/contact', endpoint="contact", methods=['GET', 'POST'])
    def contact_form():
        is_modal = request.args.get('modal', default=0, type=int)

        if request.method == "GET":
            return render_template("contact.html", is_modal=is_modal)

        field_src = request.args
        if request.method == "POST":
            field_src = request.form

        msg = {"msg": "Your message has been registred.", "category": "success"}
        try:
            contact = dict(
                user_agent = str(request.user_agent),
                remote_addr = request.remote_addr,
                created = arrow.utcnow().datetime,
                fullName = field_src.get('fullName'),
                companyName = field_src.get('companyName'),
                subject = field_src.get('subject'),
                email = field_src.get('email'),
                message = Markup.escape(field_src.get('message'))
            )
            queries.col_contact().insert(contact)
            #flash("Your message has been registred.", "success")
            message = Message("DB.nomics - new contact from [%s]" % contact['email'],
                              sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                              recipients=[current_app.config.get('MAIL_ADMINS')])
            message.html = '<a href="%s">Admin contacts</a>' % url_for('admin.contacts', _external=True)
            try:
                mail.send(message)
            except Exception as err:
                current_app.logger.fatal(str(err))

        except Exception as err:
            #flash("Sorry, An unexpected error has occurred. Your message has not registred.", "error")
            msg = {"msg": "Sorry, An unexpected error has occurred. Your message has not registred.", "category": "error"}
            current_app.logger.fatal(str(err))

        return jsonify({"notify": msg, "redirect": url_for('home', _external=True)})

    @bp_or_app.route('/rss.xml', endpoint="rss")
    def atom_feed():
        from werkzeug.contrib.atom import AtomFeed
        now = arrow.utcnow().datetime
        feed = AtomFeed("DB.nomics",
                        feed_url=request.url,
                        #url=request.host_url,
                        #updated=now,
                        subtitle="Updated datasets - Last 24 hours"
                        )

        query = {
            "$or": [{"count_inserts": {"$gt": 0}}, {"count_updates": {"$gt": 0}}]
        }

        startDate = arrow.utcnow().replace(days=-1).floor("second")
        query["created"] = {"$gte": startDate.datetime}

        limit = request.args.get('limit', default=0, type=int)

        cursor = queries.col_stats_run().find(query)
        if limit:
            cursor = cursor.limit(limit)

        cursor = cursor.sort("created", -1)
        rows = [doc for doc in cursor]

        slugs = []

        for row in rows:
            slug = slugify("%s-%s" % (row["provider_name"], row["dataset_code"]),
                            word_boundary=False, save_order=True)
            slugs.append((row, slug))

        query_dataset = {"slug": {"$in": [s[1] for s in slugs]}}
        projection = {"metadata": False, "concepts": False, "codelists": False}
        datasets = {doc["slug"]: doc for doc in queries.col_datasets().find(query_dataset, projection)}

        for row, slug in slugs:
            dataset = datasets.get(slug)
            if not dataset["enable"]:
                continue

            url = url_for("views.explorer_d", dataset=slug, _external=True)
            #content = """
            #<p>Updated date from provider : %(last_update)s</p>
            #"""

            feed.add(title="%s - %s" % (row["provider_name"], row["dataset_code"]),
                     summary=dataset["name"],
                     #content=content % dataset,
                     #content_type="html",
                     url=url,
                     id=slug,
                     updated=row["created"], #dataset["last_update"],
                     published=dataset["download_last"]
                     )

        return feed.get_response()


