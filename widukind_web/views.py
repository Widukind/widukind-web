# -*- coding: utf-8 -*-

import csv
from io import StringIO
from pprint import pprint

from flask import (Blueprint, 
                   current_app, 
                   request, 
                   render_template,
                   render_template_string, 
                   url_for, 
                   session, 
                   flash, 
                   json, 
                   abort)

from werkzeug.wsgi import wrap_file
from werkzeug.datastructures import MultiDict

from pymongo import ASCENDING, DESCENDING
from bson import ObjectId
import pandas

from dlstats.utils import search_series_tags, search_datasets_tags

from widukind_web import constants
from widukind_web import forms
from widukind_web import utils
from widukind_web.extensions import cache
from widukind_web import queues

bp = Blueprint('views', __name__)

def convert_series_period(series):
    
    new_series = []
    
    for s in series:
        start_date = pandas.Period(ordinal=s['startDate'], freq=s['frequency'])
        end_date = pandas.Period(ordinal=s['endDate'], freq=s['frequency'])
        s['startDate'] = str(start_date)
        s['endDate'] = str(end_date)
        new_series.append(s)
        
    return new_series

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


@bp.route('/providers', endpoint="providers")
@cache.cached(timeout=360)
def html_providers():
            
    cursor = current_app.widukind_db[constants.COL_PROVIDERS].find({}, 
                                                                   projection={'_id': False})
    
    providers = [doc for doc in cursor]
    
    return render_template("providers.html", providers=providers)



@bp.route('/last-datasets', endpoint="last_datasets")
def last_datasets():

    LIMIT = 20
    
    is_ajax = request.args.get('json') or request.is_xhr
    
    query = {}
    
    projection = {
        "dimensionList": False, 
        "attributeList": False, 
    }

    if not is_ajax:
        return render_template("last_datasets.html")
    
    _object_list = current_app.widukind_db[constants.COL_DATASETS].find(query,
                                                                 projection=projection)
    
    count, object_list = filter_query(_object_list, limit=LIMIT, execute=True)
    
    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        for s in object_list:
            s['view'] = url_for('.dataset', id=s['_id'])
            doc_href = s.get('docHref', None)                        
            if doc_href and not doc_href.lower().startswith('http'):
                s['docHref'] = None            
            datas["rows"].append(s)

        # pagination client - return rows only
        return current_app.jsonify(datas["rows"])

@bp.route('/last-series', endpoint="last_series")
def last_series():
    """
    > projection sur 1 élément du champs array
    > sort sur cet élément d'un champs array
    pprint(list(db.series.find({}, projection={"key": True, "_id": False, "releaseDates": {"$slice": 1}}).limit(20).sort([("releaseDates.0", -1)])))
    """
    LIMIT = 20
    
    is_ajax = request.args.get('json') or request.is_xhr
    
    query = {}
    
    projection = {
        "dimensions": False, 
        "attributes": False, 
        "releaseDates": False,
        "revisions": False,
    }

    if not is_ajax:
        return render_template("last_series.html")
    
    _series = current_app.widukind_db[constants.COL_SERIES].find(query,
                                                                 projection=projection)
    
    count, series = filter_query(_series, limit=LIMIT)
    
    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        series = convert_series_period(series)
        for s in series:
            s['view'] = url_for('.serie', id=s['_id'])
            s['export_csv'] = url_for('download.series_csv', provider=s['provider'], datasetCode=s['datasetCode'], key=s['key'])
            s['view_graphic'] = url_for('.series_plot', id=s['_id'])
            datas["rows"].append(s)

        return current_app.jsonify(datas)

@bp.route('/datasets/<provider>', endpoint="datasets")
@bp.route('/datasets', endpoint="all_datasets")
def html_datasets(provider=None):        

    is_ajax = request.args.get('json') or request.is_xhr

    projection = {
        "dimensionList": False, 
        "attributeList": False, 
    }

    provider_doc = None
    if provider:
        provider_doc = current_app.widukind_db[constants.COL_PROVIDERS].find_one({"name": provider})

    if not is_ajax:    
        return render_template("datasets.html", 
                               provider=provider_doc)


    query = {}
    if provider:
        query['provider'] = provider
        
    datasets = current_app.widukind_db[constants.COL_DATASETS].find(query, 
                                                                    projection=projection,
                                                                    sort=[('lastUpdate', DESCENDING)])
    
    count, objects = filter_query(datasets)

    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        for o in objects:
            o['view'] = url_for('.dataset', id=o['_id'])
            o['series'] = url_for('.series_with_datasetCode', provider=o['provider'], datasetCode=o['datasetCode'])
            doc_href = o.get('docHref', None)                        
            if doc_href and not doc_href.lower().startswith('http'):
                o['docHref'] = None
            datas["rows"].append(o)

        return current_app.jsonify(datas)
    

@bp.route('/series/<provider>/<datasetCode>', endpoint="series_with_datasetCode")
@bp.route('/series/<provider>', endpoint="series")
@bp.route('/series', endpoint="all_series")
def html_series(provider=None, datasetCode=None):

    is_ajax = request.args.get('json') or request.is_xhr
    
    query = {}
    if provider: query['provider'] = provider
    if datasetCode: query['datasetCode'] = datasetCode
    
    search_filter = None
    if request.args.get('filter'):
        search_filter = json.loads(request.args.get('filter'))
        if 'startDate' in search_filter:
            """
            > Manque la fréquence
            pd.Period("1995", freq="A").ordinal
            """
        
    #print("search_filter : ", search_filter, type(search_filter))
    
    search_tags = request.args.get('tags')
    if search_tags:
        tags = [t.strip().lower() for t in search_tags.split()]
        query["tags"] =  {"$all": tags}
    
    projection = {
        "dimensions": False, 
        "attributes": False, 
        "releaseDates": False,
        "revisions": False,
        "values": False,
        "dimensions": False,
        "notes": False
    }
    
    if search_filter:
        filter.update(search_filter)
        
    #print("query : ", query)

    if not is_ajax:
        dataset = None
        if datasetCode:
            dataset = current_app.widukind_db[constants.COL_DATASETS].find_one(query)
        
        provider_doc = None 
        if provider: 
            provider_doc = current_app.widukind_db[constants.COL_PROVIDERS].find_one({"name": provider})
        
        return render_template("series.html", 
                               provider=provider_doc, 
                               dataset=dataset)
    
    series = current_app.widukind_db[constants.COL_SERIES].find(query,
                                                                projection=projection)
    
    count, series = filter_query(series)
    
    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        series = convert_series_period(series)
        for s in series:
            s['view'] = url_for('.serie', id=s['_id'])
            s['export_csv'] = url_for('download.series_csv', provider=s['provider'], datasetCode=s['datasetCode'], key=s['key'])
            #s['export_csv'] = url_for('download.series_csv', provider=s['provider'], datasetCode=s['datasetCode'], key=s['key'])
            s['view_graphic'] = url_for('.series_plot', id=s['_id'])
            #TODO: s['url_dataset'] = url_for('.dataset', id=s['_id'])
            datas["rows"].append(s)
        return current_app.jsonify(datas)


@bp.route('/dataset/<objectid:id>', endpoint="dataset")
def html_dataset_by_id(id):
    
    dataset = current_app.widukind_db[constants.COL_DATASETS].find_one({"_id": id})
    
    if not dataset:
        abort(404)

    is_ajax = request.args.get('json') or request.is_xhr
    
    if is_ajax:
        result = render_template_string("{{ dataset|pprint }}", dataset=dataset)
        return current_app.jsonify(result)
    
    provider = current_app.widukind_db[constants.COL_PROVIDERS].find_one({"name": dataset['provider']})

    count_series = current_app.widukind_db[constants.COL_SERIES].count({"provider": dataset['provider'],
                                                                        "datasetCode": dataset['datasetCode']})
    return render_template("dataset.html", 
                           id=id, 
                           provider=provider,
                           dataset=dataset,
                           count=count_series)
    
@bp.route('/serie/<objectid:id>', endpoint="serie")
def html_serie_by_id(id):

    serie = current_app.widukind_db[constants.COL_SERIES].find_one({"_id": id})

    if not serie:
        abort(404)
        
    provider = current_app.widukind_db[constants.COL_PROVIDERS].find_one({"name": serie['provider']})

    dataset = current_app.widukind_db[constants.COL_DATASETS].find_one({"provider": serie['provider'],
                                                                        "datasetCode": serie['datasetCode']})

    is_ajax = request.args.get('json') or request.is_xhr
    
    if is_ajax:
        result_dataset = render_template_string("{{ dataset|pprint }}", dataset=dataset)
        result_series = render_template_string("{{ serie|pprint }}", serie=serie)
        return current_app.jsonify(dict(dataset=result_dataset, serie=result_series))
    
    frequency = serie['frequency']
    start_date = pandas.Period(ordinal=serie['startDate'], freq=frequency)
    periods = [str(start_date)]
    for i in range(1, len(serie['values'])):
        start_date +=1
        periods.append(str(start_date))

    values = [z for z in zip(periods, serie['values'])]
    
    dimensions = []
    dimensionList = dataset['dimensionList']
    for d, value in serie['dimensions'].items():
        if not d in dimensionList:
            #TODO: log
            continue
        dim_value = dict(dimensionList[d])[value]
        dimensions.append((dim_value, value))

    attributes = []
    """
    attributeList = dataset['attributeList']
    for d, value in serie['attributes'].items():
        if not d in attributeList:            
            #TODO: log
            continue
        for v in value:
            if v and len(v.strip()) > 0:
                attr_value = dict(attributeList[d])[v]
                attributes.append((attr_value, v))
            else:
                attributes.append((None, None))
    """
    # [..., (None, None), ('provisional', 'p')]
    # Eurostat - series key: A.CLV05_MEUR.N111G.CH
        
    return render_template("serie.html", 
                           id=id, 
                           serie=serie,
                           periods=periods,
                           values=values,
                           dimensions=dimensions,
                           attributes=attributes,
                           provider=provider,
                           dataset=dataset)
    
def datas_from_series(series):
    sd = pandas.Period(ordinal=series['startDate'],
                       freq=series['frequency'])

    periods = []
    for i in range(0, len(series['values'])):
        sd +=1
        periods.append(str(sd.to_timestamp().strftime("%Y-%m-%d")))

    values = []
    for v in series['values']:
        values.append(v)

    return periods, values        

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


@bp.route('/plot/series/<objectid:id>', endpoint="series_plot")
def plot_series(id):

    tmpl = "series_plot.html"
    if request.is_xhr:
        tmpl = "series_plot_ajax.html"
    
    series = current_app.widukind_db[constants.COL_SERIES].find_one({"_id": id})

    if not series:
        abort(404)

    periods, values = datas_from_series(series)

    datas = []
    datas.append(["Dates", "Values"])
    for i, v in enumerate(values):
        v = v.replace("NAN", "0")
        datas.append([periods[i], v])
    
    return render_template(tmpl, 
                           datas=datas,
                           series=series)

def get_search_form(form_klass):
    if request.json:
        return form_klass(MultiDict(request.json))
    else:
        return form_klass()
    
def get_search_datas(form, search_type="datasets"):

    providers = None
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
        kwargs["provider_name"] = providers
    
    if limit:
        kwargs["limit"] = limit
    
    if sort:
        kwargs["sort"] = sort
    
    if search_type == "series":
        
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

    is_ajax = request.args.get('json') or request.is_xhr
    
    form = get_search_form(forms.SearchFormDatasets)
    
    if form.validate_on_submit():
        
        projection = {
            "dimensionList": False, 
            "attributeList": False, 
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
            s['view'] = url_for('.dataset', id=s['_id'])
        
        return current_app.jsonify(dict(count=len(object_list), object_list=object_list, query=kwargs))
        
    return render_template('search-datasets.html', form=form, search_type="datasets")

@bp.route('/search/series', methods=('GET', 'POST'), endpoint="search_series")
def search_in_series():
    
    is_ajax = request.args.get('json') or request.is_xhr

    form = get_search_form(forms.SearchFormSeries)
    
    if form.validate_on_submit():
        
        projection = {
            "dimensions": False, 
            "attributes": False, 
            "releaseDates": False,
            "revisions": False,
            "values": False
        }
        
        kwargs = get_search_datas(form, search_type="series")
        
        object_list, _query = search_series_tags(current_app.widukind_db,
                                         projection=projection, 
                                         **kwargs)

        object_list = convert_series_period(object_list)

        record_query(query=kwargs, 
                     result_count=len(object_list), 
                     form=form, 
                     tags=["search", "series"])
        
        for s in object_list:
            s['view'] = url_for('.serie', id=s['_id'])
        
        return current_app.jsonify(dict(count=len(object_list), object_list=object_list, query=kwargs))
        
    return render_template('search-series.html', form=form, search_type="series")

@cache.memoize(360)
def _category_tree(provider):
    return utils.categories_to_dict(current_app.widukind_db, provider)

@bp.route('/categories/<provider>', endpoint="categories")
def category_tree_view(provider):
    
    is_ajax = request.args.get('json') or request.is_xhr
    
    tree = _category_tree(provider)
    
    #dataset_codes = current_app.widukind_db[constants.COL_DATASETS].distinct("datasetCode", {"provider": provider})
    dataset_projection = {"_id": True, "datasetCode": True}
    dataset_codes = {}
    for doc in current_app.widukind_db[constants.COL_DATASETS].find({"provider": provider}, 
                                                                    dataset_projection):
        dataset_codes[doc['datasetCode']] = doc['_id']
    
    if is_ajax:
        return current_app.jsonify(tree)
    
    return render_template('categories.html', tree=tree, dataset_codes=dataset_codes)

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
        "releaseDates": False,
        "revisions": False,
        "values": False,
    }
    cart = session.get("cart", None)
    
    if cart:
        series_ids = [ObjectId(c) for c in cart]
        series = current_app.widukind_db[constants.COL_SERIES].find({"_id": {"$in": series_ids}},
                                                                    projection=projection)
        
        series = convert_series_period(series)
        for s in series:
            s['view'] = url_for('.serie', id=s['_id'])
            datas["rows"].append(s)
        
        #datas["total"] = len(datas["rows"])
        #pprint(datas)
    return current_app.jsonify(datas["rows"])
        
@bp.route('/tags/prefetch/series', endpoint="tag_prefetch_series")
@cache.cached(timeout=120)
def tag_prefetch_series():
    """
    TODO: notion de selection provider ?
    
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
    
    
    
    provider = request.args.get('provider')
    limit = request.args.get('limit', default=200, type=int)
    
    col = current_app.widukind_db[constants.COL_TAGS_SERIES]
    
    query = {"count": {"$gte": 5}}
    if provider:
        query["providers.name"] = {"$in": [provider]}
    
    tags = col.distinct("name", query)
    return current_app.jsonify(tags)
    
    projection = {"_id": False, "providers": False}
    query = {}
    docs = col.find(query, projection=projection).sort("count", DESCENDING).limit(limit)
    tags = [doc['name'] for doc in docs]
    #print(tags)
    return current_app.jsonify(tags)
    

