# -*- coding: utf-8 -*-

from pprint import pprint
from collections import OrderedDict

from flask import (Blueprint, 
                   current_app, 
                   request, 
                   render_template,
                   render_template_string, 
                   url_for, 
                   session, 
                   flash, 
                   abort)

from werkzeug.wsgi import wrap_file
from werkzeug.datastructures import MultiDict

from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from widukind_common.tags import search_series_tags, search_datasets_tags, str_to_tags

from widukind_web import constants
from widukind_web import forms
from widukind_web import utils
from widukind_web.extensions import cache
from widukind_web import queues
from widukind_web import queries
from widukind_common.flask_utils import json_tools

bp = Blueprint('views', __name__)

def complex_queries_series(query={}):

    tags = request.args.get('tags', None)
    
    search_fields = []
    query_and = []
    
    for r in request.args.lists():
        if r[0] in ['limit', 'tags', 'provider', 'dataset']:
            continue
        elif r[0] == 'frequency':
            query['frequency'] = r[1][0]
        elif r[0].startswith('dimensions_'):
            field_name = r[0].split('dimensions_')[1]
            search_fields.append((field_name, r[1][0]))
        else:
            msg = "unknow field[%s]" % r[0]
            current_app.logger.warn(msg)

    if tags and len(tags.split()) > 0:
        tags = tags.split()
        conditions = [{"tags": {"$regex": ".*%s.*" % value.lower()}} for value in tags]
        query_and.append({"$and": conditions})
        
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
            
    print("-----complex query-----")
    pprint(query)    
    print("-----------------------")
        
    return query
    

def get_ordinal_from_period(date_str, freq=None):
    return current_app.get_ordinal_from_period(date_str, freq)

def get_period_from_ordinal(date_ordinal, freq=None):
    return current_app.get_period_from_ordinal(date_ordinal, freq)   

def convert_series_period(series_list):
    
    new_series = []
    for s in series_list:
        s['start_date'] = s["values"][0]["period"]
        s['end_date'] = s["values"][-1]["period"]
        new_series.append(s)
        
    return new_series

def datas_from_series(series):
    
    import pandas
    
    for value in series["values"]:
        yield pandas.Period(value["period"], freq=series['frequency']).to_timestamp().strftime("%Y-%m-%d"), value["value"]        

def filter_query(cursor, 
                 skip=None, limit=None, sort=None, sort_desc=None,
                 search=None, 
                 execute=False):
    '''
    Filtrer d'après des arguments request.args
    '''
    """
    Par default:
    http://127.0.0.1:8080/group/?sort=name&order=asc&limit=5&offset=0&_=1426760277239
    
    /group/?sort=name&order=asc&limit=5&offset=0
    > 1er
    http://issues.wenzhixin.net.cn/examples/bootstrap_table/data?offset=0&limit=10
    > page 2
    http://issues.wenzhixin.net.cn/examples/bootstrap_table/data?offset=10&limit=10
    
    > search
    http://127.0.0.1:8080/group/?search=2-group&sort=name&order=asc&limit=10&offset=0&_=1426761507065
    
    Pour pagination coté server, renvoyer:
        {
          "total": 800,
          "rows": [
              les datas
          ]        
    """
    #skip
    skip = skip or request.args.get('offset', default=0, type=int)
    
    #limit
    limit = limit or request.args.get('limit', default=20, type=int)
    
    #Transformer en query pymongo ?
    search = search or request.args.get('search')
    
    count = cursor.count()
    #count = cursor.count(with_limit_and_skip=True)
    #print("count : ", count)
    
    #order_by
    sort = sort or request.args.get('sort') #nom du champs
    sort_desc = sort_desc or request.args.get('order', 'asc') == 'desc'

    if skip:
        cursor = cursor.skip(skip)
        
    if limit:
        cursor = cursor.limit(limit)

    if sort:
        if sort_desc:
            cursor.sort(sort, DESCENDING)
        else:
            cursor.sort(sort, ASCENDING)
        
    if execute:
        cursor = list(cursor)
    
    return count, cursor

@bp.route('/ajax/providers', endpoint="ajax-providers-list")
def ajax_providers_list():
    query = {"enable": True}
    projection = {"_id": False, "slug": True, "name": True}
    docs = [doc for doc in queries.col_providers().find(query, projection).sort("name", ASCENDING)]
    return json_tools.json_response(docs)

@bp.route('/ajax/providers/<provider>/datasets', endpoint="ajax-datasets-list")
def ajax_datasets_list(provider):
    provider_doc = queries.get_provider(provider)
    query = {'provider_name': provider_doc["name"],
             "enable": True}
    projection = {"_id": False, "tags": False,
                  "enable": False, "lock": False,
                  "concepts": False, "codelists": False}
    
    is_meta = request.args.get('is_meta', type=int, default=0) == 1
    if not is_meta:
        projection["metadata"] = False
        
    docs = [doc for doc in queries.col_datasets().find(query, projection)]
    return json_tools.json_response(docs)

@bp.route('/ajax/datasets/<dataset>/dimensions/keys', endpoint="ajax-datasets-dimensions-keys")
def ajax_datasets_dimensions_keys(dataset):
    query = {'enable': True, 'slug': dataset}
    projection = {"_id": False, "dimension_keys": True, "concepts": True}
    doc = queries.col_datasets().find_one(query, projection)
    if not doc:
        abort(404)
    dimensions = [] 
    for key in doc["dimension_keys"]:
        if key in doc["concepts"]:            
            dimensions.append({"value": key, "text": doc["concepts"][key] })
        else:
            dimensions.append({"value": key, "text": key })
    return json_tools.json_response(dimensions)

@bp.route('/ajax/datasets/<dataset>/dimensions/all', endpoint="ajax-datasets-dimensions-all")
def ajax_datasets_dimensions_all(dataset):
    query = {'enable': True, 'slug': dataset}
    projection = {"_id": False, "dimension_keys": True, "concepts": True, "codelists": True}
    doc = queries.col_datasets().find_one(query, projection)
    if not doc:
        abort(404)
    dimensions = []
    print("dimension_keys : ", doc["dimension_keys"])
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
    query = {'enable': True, 'slug': dataset}
    projection = {"_id": False, 
                  "enable": False, "lock": False, "tags": False}
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

@bp.route('/providers', endpoint="providers")
@cache.cached(timeout=360)
def all_providers():
            
    cursor = queries.col_providers().find({"enable": True}, {'_id': False})
    
    providers = [doc for doc in cursor]
    
    counters = queries.datasets_counter(match={"enable": True})
    
    return render_template("providers.html", providers=providers, counters=counters)

@bp.route('/datasets/<slug>', endpoint="datasets")
def all_datasets_for_provider_slug(slug):

    is_ajax = request.args.get('json') or request.is_xhr

    provider = queries.col_providers().find_one({"slug": slug, "enable": True})
    if not provider:
        abort(404)

    query = {"enable": True, "provider_name": provider["name"]}

    if not is_ajax:
        datasets_count = queries.col_datasets().count(query)
        return render_template("datasets.html", 
                               provider=provider, 
                               datasets_count=datasets_count)

    projection = {
        "dimension_list": False, 
        "attribute_list": False,
        "concepts": False,
        "codelists": False,
        "tags": False,
        "notes": False,         
        "attribute_keys": False,
        "dimension_keys": False,
    }

    datasets = queries.col_datasets().find(query, 
                                   projection,
                                   sort=[('last_update', DESCENDING)])
    
    count, objects = filter_query(datasets)

    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        for dataset in objects:

            dataset['view'] = url_for('.dataset-by-slug', slug=dataset['slug'])
            dataset['series'] = url_for('.series_by_dataset_slug', slug=dataset['slug'])
            doc_href = dataset.get('doc_href', None)                        
            if doc_href and not doc_href.lower().startswith('http'):
                dataset['doc_href'] = None
                
            datas["rows"].append(dataset)

        return current_app.jsonify(datas)

@bp.route('/series/dataset/<slug>', endpoint="series_by_dataset_slug", methods=('GET', 'POST'))
def all_series_for_dataset_slug(slug):

    is_ajax = request.args.get('json') or request.is_xhr

    ds_projection = {"_id": False, "slug": True, "name": True,
                     "provider_name": True, "dataset_code": True}    
    dataset = queries.col_datasets().find_one({"enable": True,
                                               "slug": slug},
                                              ds_projection)
    
    if not dataset:
        abort(404)
    
    query = {"provider_name": dataset["provider_name"],
             "dataset_code": dataset["dataset_code"]}

    limit = None
    
    if request.method == 'POST':
        limit = int(request.form.get("limit", 20))
        frequency = request.form.get("frequency")
        for _key, _value in request.form.items():
            if _key.startswith("dim-"):
                dimension_key = _key.split("dim-")[1]
                dimension_values = request.form.getlist(_key)
                query["dimensions.%s" % dimension_key] = {"$in": dimension_values}

            if _key.startswith("attr-"):
                attribute_key = _key.split("attr-")[1]
                attribute_values = request.form.getlist(_key)
                query["attributes.%s" % attribute_key] = {"$in": attribute_values}
    
        if frequency:
            query["frequency"] = frequency
    
    """    
    search_filter = None
    if request.args.get('filter'):
        search_filter = json.loads(request.args.get('filter'))
        if 'start_date' in search_filter:
            # Manque la fréquence
            #pd.Period("1995", freq="A").ordinal
    """
    
    #TODO: Gérer dans tableau pour filtrage dynamique
    """
    search_tags = request.args.get('tags')
    if search_tags:
        tags = [t.strip().lower() for t in search_tags.split()]
        query["tags"] =  {"$all": tags}
    """
    #if search_filter:
    #    filter.update(search_filter)
        
    if not is_ajax:
        provider_doc = queries.col_providers().find_one({"name": dataset["provider_name"]})

        return render_template("series_list.html", 
                               provider=provider_doc, 
                               dataset=dataset)

    projection = {
        "dimensions": False, 
        "attributes": False, 
        #"values.revisions": False,
        "notes": False
    }
    
    series = queries.col_series().find(query, projection)
    count, series = filter_query(series, limit=limit)
    
    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        series = convert_series_period(series)
        for s in series:
            is_revisions = False
            for value in s["values"]:
                if value.get("revisions"):
                    is_revisions = True
                    break
            s['is_revisions'] = is_revisions
            del s["values"]
            s['view'] = url_for('.series-by-slug', slug=s['slug'])
            s['export_csv'] = url_for('download.series_csv', 
                                      slug=s['slug'], 
                                      #dataset_code=s['dataset_code'], key=s['key']
                                      )
            s['view_graphic'] = url_for('.series_plot', slug=s['slug'])
            #TODO: s['url_dataset'] = url_for('.dataset', id=s['_id'])
            if s['frequency'] in constants.FREQUENCIES_DICT:
                s['frequency'] = constants.FREQUENCIES_DICT[s['frequency']]
            
            datas["rows"].append(s)
        #pprint(datas)
        return current_app.jsonify(datas)

@bp.route('/ajax/slug/dataset/<slug>', endpoint="ajax-dataset-by-slug")
def ajax_dataset_with_slug(slug):

    query = {"enable": True, "slug": slug}
    dataset = queries.col_datasets().find_one(query)
        
    if not dataset:
        abort(404)

    provider = queries.col_providers().find_one({"name": dataset['provider_name']})

    #from flask.globals import _request_ctx_stack
    #ctx = _request_ctx_stack.top
    #jinja_env = ctx.app.jinja_env
    jinja_env = current_app.jinja_env
    jinja_env.globals.update(dict(moment=current_app.extensions['moment']))
    template = jinja_env.get_template('dataset-ajax.html')

    count_series = queries.col_series().count({"provider_name": dataset['provider_name'],
                                               "dataset_code": dataset['dataset_code']})
    
    result = template.render(dataset=dataset, 
                             provider=provider, 
                             count=count_series)
    
    return current_app.jsonify(dict(html=result))

@bp.route('/slug/dataset/<slug>', endpoint="dataset-by-slug")
def dataset_with_slug(slug):

    query = {"enable": True, "slug": slug}
    dataset = queries.col_datasets().find_one(query)
        
    if not dataset:
        abort(404)

    is_ajax = request.args.get('json') or request.is_xhr
    
    if is_ajax:
        '''debug mode'''
        result = render_template_string("{{ dataset|pprint }}", 
                                        dataset=dataset)
        return current_app.jsonify(result)
    
    provider = queries.col_providers().find_one({"name": dataset['provider_name']})

    count_series = queries.col_series().count({"provider_name": dataset['provider_name'],
                                       "dataset_code": dataset['dataset_code']})
    return render_template("dataset.html", 
                           provider=provider,
                           dataset=dataset,
                           count=count_series)

@bp.route('/dataset/<provider_name>/<dataset_code>', endpoint="dataset-by-code")
def dataset_with_code(provider_name, dataset_code):

    query = {"enable": True, 
             "provider_name": provider_name,
             "dataset_code": dataset_code}
    dataset = queries.col_datasets().find_one(query)
        
    if not dataset:
        abort(404)

    provider = queries.col_providers().find_one({"name": dataset['provider_name']})

    count_series = queries.col_series().count({"provider_name": dataset['provider_name'],
                                       "dataset_code": dataset['dataset_code']})
    return render_template("dataset.html", 
                           provider=provider,
                           dataset=dataset,
                           count=count_series)

@bp.route('/slug/series/<slug>', endpoint="series-by-slug")
def series_with_slug(slug):
    
    is_reverse = request.args.get('reverse')

    query = {"slug": slug}    
    series = queries.col_series().find_one(query)

    if not series:
        abort(404)
        
    provider = queries.col_providers().find_one({"enable": True,
                                                 "name": series['provider_name']})
    if not provider:
        abort(404)

    dataset = queries.col_datasets().find_one({"enable": True,
                                               'provider_name': series['provider_name'],
                                               "dataset_code": series['dataset_code']})
    if not dataset:
        abort(404)

    is_ajax = request.args.get('json') or request.is_xhr
    
    if is_ajax:
        '''debug mode'''
        result_dataset = render_template_string("{{ dataset|pprint }}", dataset=dataset)
        result_series = render_template_string("{{ series|pprint }}", series=series)
        return current_app.jsonify(dict(dataset=result_dataset, series=result_series))
    
    
    """
    Faire un tableau de date:
        1ère ligne: current, dataset.last_udpate
        lignes suivantes: chaque révisions
    """
    
    
    
    max_revisions = 0
    revision_dates = []
    obs_attributes_keys = []
    obs_attributes_values = []
    
    for v in series["values"]:
        
        if "revisions" in v:
            for r in v["revisions"]:
                if not r["revision_date"] in revision_dates:
                    revision_dates.append(r["revision_date"])

            count = len(v["revisions"])
            if count > max_revisions:
                max_revisions = count
        
        if v.get("attributes"):
            for key, attr in v["attributes"].items():
                obs_attributes_keys.append(key)
                obs_attributes_values.append(attr)       
    
    revision_dates.reverse()
    #pprint(revision_dates)
    """
    Essai tableau de rev avec series_essai_rev.html
    > trous dans les period    
    '2008-10-01 00:00:00': [{'attributes': None,
                              'period': '1980',
                              'value': '-83.25'},
                             {'attributes': None,
                              'period': '1982',
                              'value': '-157.75'},]
                              
    revision_dates = OrderedDict()
    revision_dates[str(dataset["last_update"])] = []
    for v in series["values"]:
        
        revision_dates[str(dataset["last_update"])].append({
            "value": v["value"],
            "period": v["period"],
            "attributes": v.get("attributes", {})
        })
        
        if "revisions" in v:
            for r in v["revisions"]:
                if not str(r["revision_date"]) in revision_dates:
                    revision_dates[str(r["revision_date"])] = []
                #if not r["revision_date"] in revision_dates:
                #    revision_dates.append(r["revision_date"])
                revision_dates[str(r["revision_date"])].append({
                    "value": r["value"],
                    "period": v["period"],
                    "attributes": r.get("attributes", {})
                })
                
            count = len(v["revisions"])
            if count > max_revisions:
                max_revisions = count
        else:
            for rk, vk in revision_dates.items():
                if rk == str(dataset["last_update"]):
                    continue
                vk.append({
                    "value": v["value"],
                    "period": v["period"],
                    "attributes": v.get("attributes", {})
                })
        
        if v.get("attributes"):
            for key, attr in v["attributes"].items():
                obs_attributes_keys.append(key)
                obs_attributes_values.append(attr)       
    """
    
    
    dimension_filter = ".".join([series["dimensions"][key] for key in dataset["dimension_keys"]])
    
    return render_template("series.html", 
                           series=series,
                           provider=provider,
                           dataset=dataset,
                           dimension_filter=dimension_filter.upper(),
                           is_reverse=is_reverse,
                           obs_attributes_keys=list(set(obs_attributes_keys)),
                           obs_attributes_values=list(set(obs_attributes_values)),
                           revision_dates=list(set(revision_dates)),
                           max_revisions=max_revisions)
    
def send_file_csv(fileobj, mimetype=None, content_length=0):

    data = wrap_file(request.environ, fileobj, buffer_size=1024*256)
    response = current_app.response_class(
                        data,
                        mimetype=mimetype,
                        #direct_passthrough=True
                        )
    response.status_code = 200    
    #response.content_length = content_length
    response.make_conditional(request)
    return response

#@cache.memoize(360)
@bp.route('/plot/series/<slug>', endpoint="series_plot")
def plot_series(slug):
    
    is_ajax = request.args.get('json') or request.is_xhr

    tmpl = "series_plot.html"
    if is_ajax:
        tmpl = "series_plot_ajax.html"

    series = queries.col_series().find_one({"slug": slug})

    if not series:
        abort(404)

    dataset = queries.col_datasets().find_one({"enable": True,
                                               "provider_name": series["provider_name"],
                                               "dataset_code": series["dataset_code"]})    
    if not dataset:
        abort(404)

    datas = []    
    datas.append(("Dates", "Values"))
    for period, value in datas_from_series(series):
        datas.append((period, value))
    
    return render_template(tmpl,
                           is_ajax=is_ajax, 
                           datas=datas,
                           series=series)

def get_search_form(form_klass):
    if request.json:
        return form_klass(MultiDict(request.json))
    else:
        return form_klass()
    
def get_search_datas(form, search_type="datasets"):

    providers = None
    datasets = None
    frequency = None
    limit = None
    sort = None
    sort_desc = False

    start_date = None
    end_date = None

    query = form.query.data.strip()

    if form.sort.data:
        sort = form.sort.data

    #TODO:            
    #if form_sort_desc.data:
    #    sort_desc = form_sort_desc.data
    
    if form.limit.data:
        limit = int(form.limit.data)
        
    if search_type == "series":
        
        if form.datasets.data:
            datasets = form.datasets.data
        
        frequency_data = form.frequency.data
        if frequency_data and frequency_data not in ["", "All"]:
            frequency = frequency_data        
        
        if form.start_date.data:
            start_date = form.start_date.data

        if form.end_date.data:
            end_date = form.end_date.data
    
    providers_data = form.providers.data
    if providers_data:
        providers = providers_data
        
    kwargs = {}
    
    if providers:
        #str or array if multiple choices
        kwargs["provider_name"] = providers
    
    if limit:
        kwargs["limit"] = limit
    
    #if sort:
    #    kwargs["sort"] = sort
    
    if search_type == "series":

        if datasets:
            #str or array if multiple choices
            kwargs["dataset_code"] = datasets
        
        if frequency:
            kwargs["frequency"] = frequency
            
        if start_date: 
            kwargs["start_date"] = start_date
        
        if end_date: 
            kwargs["end_date"] = end_date
    
    if query:
        kwargs["search_tags"] = query

    return kwargs


def record_query(query=None, result_count=0, form=None, tags=[]):
    if not queues.RECORD_QUERY:
        return

    queues.RECORD_QUERY.put({
         "created": utils.utcnow(),
         "tags": tags,
         "remote_addr": request.remote_addr,
         "remote_user": request.remote_user,
         "query": query,
         "query_string": form.query.data.strip(),        
         "result_count": result_count,
    })

@bp.route('/search/datasets', methods=('GET', 'POST'), endpoint="search_datasets")
def search_in_datasets():

    form = get_search_form(forms.SearchFormDatasets)
    
    if form.validate_on_submit():
        
        projection = {
            "dimension_list": False, 
            "attribute_list": False,
            "concepts": False,
            "codelists": False 
        }
        
        kwargs = get_search_datas(form, search_type="datasets")
    
        object_list, _query = search_datasets_tags(current_app.widukind_db,
                                                   projection=projection, 
                                                   **kwargs)

        object_list = list(object_list)
        
        record_query(query=kwargs, 
                     result_count=len(object_list), 
                     form=form, 
                     tags=["search", "datasets"])

        for s in object_list:
            s['view'] = url_for('.dataset-by-slug', slug=s['slug'])
        
        return current_app.jsonify(dict(count=len(object_list), object_list=object_list, query=kwargs))
        
    return render_template('search-datasets.html', form=form, search_type="datasets")

@bp.route('/search/series', methods=('GET', 'POST'), endpoint="search_series")
def search_in_series():
    
    form = get_search_form(forms.SearchFormSeries)
    
    if form.validate_on_submit():
        
        projection = {
            "dimensions": False, 
            "attributes": False, 
            #"release_dates": False,
            #"revisions": False,
            #"values": False
            "values.revisions": False,
        }
        
        kwargs = get_search_datas(form, search_type="series")
        
        object_list, _query = search_series_tags(current_app.widukind_db,
                                                 projection=projection, 
                                                 **kwargs)

        #result_count = object_list.count() # max limit
        result_count = object_list.count(True) # max count real
        object_list = convert_series_period(object_list)

        record_query(query=kwargs, 
                     result_count=result_count, 
                     form=form, 
                     tags=["search", "series"])
        
        for s in object_list:
            s['view'] = url_for('.series-by-slug', slug=s['slug'])
        
        return current_app.jsonify(dict(count=len(object_list), 
                                        object_list=object_list, 
                                        query=kwargs))
        
    return render_template('search-series.html', 
                           form=form, 
                           search_type="series")

#TODO: @cache.cached(360)
@bp.route('/tree/<provider>', endpoint="tree_root")
def tree_view(provider):
    
    _provider = queries.col_providers().find_one({"slug": provider, 
                                                  "enable": True})
    if not _provider:
        abort(404)
        
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
            "url": url_for('views.ajax-dataset-by-slug', slug=doc["slug"])
        }

    return render_template('categories.html', 
                           provider=_provider,
                           categories=categories,
                           dataset_codes=dataset_codes)

@bp.route('/series/cart/add', endpoint="card_add")#, methods=('POST',))
def ajax_add_cart():
    _id = request.args.get('id')
    cart = session.get("cart", [])
    if not _id in cart:
        cart.append(_id)
        flash("Series add to cart.", "success")
    else:
        flash("Series is already in the cart.", "warning")
        
    session["cart"] = cart
    return current_app.jsonify(dict(count=len(session["cart"])))
        
@bp.route('/series/cart/view', endpoint="card_view")
def ajax_view_cart():

    datas = {"rows": [], "total": 0}
    
    projection = {
        "dimensions": False, 
        "attributes": False, 
        "release_dates": False,
        "revisions": False,
        "values": False,
    }
    cart = session.get("cart", None)
    
    if cart:
        series_ids = [ObjectId(c) for c in cart]
        series = queries.col_series().find({"_id": {"$in": series_ids}},
                                                                    projection=projection)
        
        series = convert_series_period(series)
        for s in series:
            s['view'] = url_for('.series-by-slug', slug=s['slug'])
            datas["rows"].append(s)
        
        #datas["total"] = len(datas["rows"])
        #pprint(datas)
    return current_app.jsonify(datas["rows"])
        
@bp.route('/tags/prefetch/series', endpoint="tag_prefetch_series")
@cache.cached(timeout=120)
def tag_prefetch_series():
    """
    TODO: notion de selection provider ?
    
    View pour tagsinput et typehead - voir TODO.rst
    
    Même chose avec:
        - provider
        - provider/dataset pour series
    
    >>> len(db.tags.series.distinct("name", {"count": {"$gte": 20}}))
    576
    >>> len(db.tags.series.distinct("name", {"count": {"$gte": 10}}))
    615
    >>> len(db.tags.series.distinct("name", {"count": {"$gte": 50}}))
    460
    >>> len(db.tags.series.distinct("name", {"count": {"$gte": 5}}))
    666
    >>> len(db.tags.series.distinct("name", {"count": {"$gte": 4}}))
    676
    >>> len(db.tags.series.distinct("name", {"count": {"$gte": 3}}))
    699
    >>> len(db.tags.series.distinct("name", {"count": {"$gte": 2}}))
    712    
    """
    
    provider = request.args.get('provider_name')
    limit = request.args.get('limit', default=200, type=int)
    count = request.args.get('count', default=10, type=int)
    
    col = current_app.widukind_db[constants.COL_TAGS_SERIES]
    
    query = {"count": {"$gte": count}}
    if provider:
        query["providers.name"] = {"$in": [provider]}
    
    tags = col.distinct("name", query)
    return current_app.jsonify(tags)
    
    projection = {"_id": False, "providers": False}
    query = {}
    docs = col.find(query, projection=projection).sort("count", DESCENDING).limit(limit)
    tags = [doc['name'] for doc in docs]
    return current_app.jsonify(tags)
    

def _search_series(provider_name=None, dataset_code=None, 
                   frequency=None, projection=None, 
                   search_tags=None,
                   start_date=None, end_date=None,
                   sort=None, sort_desc=False,                        
                   skip=None, limit=None):
    
    '''Convert search tag to lower case and strip tag'''
    
    import pandas
    import re

    query = {}
    
    if search_tags:
        tags = str_to_tags(search_tags)
        # Add OR, NOT
        tags_regexp = [re.compile('.*%s.*' % e, re.IGNORECASE) for e in tags]
        #  AND implementation
        query = {"tags": {"$all": tags_regexp}}
    
    if provider_name:
        query['provider_name'] = provider_name
        
    if frequency:
        query['frequency'] = frequency
                    
    if dataset_code:
        query['dataset_code'] = dataset_code

    try:
        if start_date:
            ordinal_start_date = pandas.Period(start_date).ordinal
            query["start_date"] = {"$gte": ordinal_start_date}
    except Exception as err:
        current_app.logger.error(err)
    
    try:
        if end_date:
            query["end_date"] = {"$lte": pandas.Period(end_date).ordinal}
    except Exception as err:
        current_app.logger.error(err)
        
    cursor = queries.col_series().find(query, projection)
    
    skip = skip or request.args.get('offset', default=0, type=int)

    if skip:
        cursor = cursor.skip(skip)
    
    if limit:
        cursor = cursor.limit(limit)
    
    if sort:
        sort_direction = ASCENDING
        if sort_desc:
            sort_direction = DESCENDING
        cursor = cursor.sort(sort, sort_direction)
    
    return cursor, query


@bp.route('/ajax/datasets', endpoint="ajax-datasets")
def ajax_datasets_list2():
    
    provider =  request.args.get('provider')

    query = {"enable": True}
    if provider:
        query["provider_name"] = provider
        
    projection = {
        "_id": False,
        "provider_name": True,
        "dataset_code": True, 
        "name": True,
    }

    datasets = queries.col_datasets().find(query, projection,
                                           sort=[('name', ASCENDING)])
    
    datas = [(d["dataset_code"], d["name"]) for d in datasets]
    
    return current_app.jsonify(datas)
    
@bp.route('/series/all', endpoint="series-all", methods=('GET',))
def all_series():

    limit = request.args.get('limit', default=100, type=int)
    
    projection = {
        "dimensions": False, 
        "attributes": False, 
        #"values": False,
        "values.revisions": False,
        "notes": False,
        "tags": False
    }
    
    query = {}
    provider_slug = request.args.get('provider')
    dataset_slug = request.args.get('dataset')
    
    if dataset_slug:
        dataset = queries.get_dataset(dataset_slug)
        query["provider_name"] = dataset["provider_name"]
        query["dataset_code"] = dataset["dataset_code"]
    elif provider_slug:
        provider = queries.get_provider(provider_slug)
        query["provider_name"] = provider["name"]
    
    query = complex_queries_series(query)
    cursor = queries.col_series().find(query, projection).limit(limit)
    #cursor.limit(limit)
    count = cursor.count()
    
    series_list = convert_series_period(cursor)

    rows = []
    
    for s in series_list:
        del s["values"]
        s['view'] = url_for('.series-by-slug', slug=s['slug'])
        s['export_csv'] = url_for('download.series_csv', slug=s['slug'])
        s['view_graphic'] = url_for('.series_plot', slug=s['slug'])
        #TODO: s['url_dataset'] = url_for('.dataset', id=s['_id'])
        if s['frequency'] in constants.FREQUENCIES_DICT:
            s['frequency'] = constants.FREQUENCIES_DICT[s['frequency']]
        
        rows.append(s)

    return json_tools.json_response(rows, {"total": count})
    #return current_app.jsonify(datas)

@bp.route('/', endpoint="home")
def home():
    return render_template("series-home.html")
