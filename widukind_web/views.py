# -*- coding: utf-8 -*-

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

from widukind_common.tags import search_series_tags, search_datasets_tags

from widukind_web import constants
from widukind_web import forms
from widukind_web import utils
from widukind_web.extensions import cache
from widukind_web import queues
from widukind_web import queries

bp = Blueprint('views', __name__)

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

#@cache.cached(timeout=360)

@bp.route('/providers', endpoint="providers")
def all_providers():
            
    cursor = queries.col_providers().find({"enable": True}, {'_id': False})
    
    providers = [doc for doc in cursor]
    
    counters = queries.datasets_counter(match={"enable": True})
    
    return render_template("providers.html", providers=providers, counters=counters)

@bp.route('/last-datasets', endpoint="last_datasets")
def last_datasets():

    #TODO: limit setting
    LIMIT = 20
    
    is_ajax = request.args.get('json') or request.is_xhr

    if not is_ajax:
        return render_template("last_datasets.html")
    
    query = {"enable": True}
    projection = {
        "dimension_list": False, 
        "attribute_list": False,
        "concepts": False, 
        "codelists": False, 
    }
    _object_list = queries.col_datasets().find(query, projection)
    count, object_list = filter_query(_object_list, limit=LIMIT, execute=True)
    
    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        for s in object_list:
            s['view'] = url_for('.dataset-by-slug', slug=s['slug'])
            doc_href = s.get('doc_href', None)                        
            if doc_href and not doc_href.lower().startswith('http'):
                s['doc_href'] = None            
            datas["rows"].append(s)

        # pagination client - return rows only
        return current_app.jsonify(datas["rows"])

@bp.route('/last-series', endpoint="last_series")
def last_series():
    """
    > projection sur 1 élément du champs array
    > sort sur cet élément d'un champs array
    pprint(list(db.series.find({}, projection={"key": True, "_id": False, "release_dates": {"$slice": 1}}).limit(20).sort([("release_dates.0", -1)])))
    """
    LIMIT = 20
    
    is_ajax = request.args.get('json') or request.is_xhr

    #TODO: ne charger que pour les provider et datasets enable    
    
    if not is_ajax:
        return render_template("last_series.html")

    dataset_codes = [doc["dataset_code"] for doc in queries.col_datasets().find({"enable": True}, 
                                                                        {"dataset_code": True})]
    projection = {
        "dimensions": False, 
        "attributes": False,
        #"tags": False, 
        #"release_dates": False,
        "values.revisions": False,
    }

    query = {"dataset_code": {"$in": dataset_codes}}
    _series = queries.col_series().find(query, projection)
    
    count, series = filter_query(_series, limit=LIMIT)
    
    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        series = convert_series_period(series)
        for s in series:
            s['view'] = url_for('.series-by-slug', slug=s['slug'])
            s['export_csv'] = url_for('download.series_csv',
                                      slug=s['slug'] 
                                      #provider=s['provider_name'], dataset_code=s['dataset_code'], key=s['key']
                                      )
            s['view_graphic'] = url_for('.series_plot', slug=s['slug'])
            datas["rows"].append(s)

        return current_app.jsonify(datas)

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
        "codelists": False 
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

@bp.route('/series/dataset/<slug>', endpoint="series_by_dataset_slug")
def all_series_for_dataset_slug(slug):

    is_ajax = request.args.get('json') or request.is_xhr
    
    dataset = queries.col_datasets().find_one({"enable": True,
                                       "slug": slug})
    
    if not dataset:
        abort(404)
    
    query = {"provider_name": dataset["provider_name"],
             "dataset_code": dataset["dataset_code"]}
    
    search_filter = None
    if request.args.get('filter'):
        search_filter = json.loads(request.args.get('filter'))
        if 'start_date' in search_filter:
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
        #"release_dates": False,
        #"revisions": False,
        "values.revisions": False,
        "notes": False
    }
    
    if search_filter:
        filter.update(search_filter)
        
    if not is_ajax:
        provider_doc = queries.col_providers().find_one({"name": dataset["provider_name"]})

        return render_template("series_list.html", 
                               provider=provider_doc, 
                               dataset=dataset)
    
    series = queries.col_series().find(query, projection)
    count, series = filter_query(series)
    
    if is_ajax:
        datas = {
            "total": count,
            "rows": []
        }
        series = convert_series_period(series)
        for s in series:
            s['view'] = url_for('.series-by-slug', slug=s['slug'])
            s['export_csv'] = url_for('download.series_csv', 
                                      slug=s['slug'], 
                                      #dataset_code=s['dataset_code'], key=s['key']
                                      )
            s['view_graphic'] = url_for('.series_plot', slug=s['slug'])
            #TODO: s['url_dataset'] = url_for('.dataset', id=s['_id'])
            datas["rows"].append(s)
        #pprint(datas)
        return current_app.jsonify(datas)

@bp.route('/slug/dataset/<slug>', endpoint="dataset-by-slug")
def dataset_with_slug(slug):

    query = {"enable": True, "slug": slug}
    dataset = queries.col_datasets().find_one(query)
        
    if not dataset:
        abort(404)

    is_ajax = request.args.get('json') or request.is_xhr
    
    if is_ajax:
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
        result_dataset = render_template_string("{{ dataset|pprint }}", dataset=dataset)
        result_series = render_template_string("{{ series|pprint }}", series=series)
        return current_app.jsonify(dict(dataset=result_dataset, series=result_series))
    
    max_revisions = 0
    revision_dates = []
    for v in series["values"]:
        if "revisions" in v:
            revision_dates.extend([r["revision_date"] for r in v["revisions"]])
                
            count = len(v["revisions"])
            if count > max_revisions:
                max_revisions = count
    
    revision_dates.reverse()
    
    return render_template("series.html", 
                           series=series,
                           provider=provider,
                           dataset=dataset,
                           is_reverse=is_reverse,
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
    datas.append(["Dates", "Values"])
    for value in series["values"]:
        datas.append([value["period"], value["value"]])
    
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
    
    is_ajax = request.args.get('json') or request.is_xhr

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

        object_list = convert_series_period(object_list)

        record_query(query=kwargs, 
                     result_count=len(object_list), 
                     form=form, 
                     tags=["search", "series"])
        
        for s in object_list:
            s['view'] = url_for('.series-by-slug', slug=s['slug'])
        
        return current_app.jsonify(dict(count=len(object_list), 
                                        object_list=object_list, 
                                        query=kwargs))
        
    return render_template('search-series.html', form=form, search_type="series")


@bp.route('/tree/<provider>', defaults={'path': ''})
@bp.route('/tree/<provider>/<path:path>')
def tree(provider, path=None):
    abort(404)
    
    _provider = queries.col_providers().find_one({"slug": provider, 
                                                  "enable": True})
    if not _provider:
        abort(404)

    current_category = None
    
    query = {"provider_name": _provider["name"], "enable": True}
    all_parents = []
    parent_url = None
    
    if path:
        slug = path.split('/')[-1]
        current_category = queries.col_categories().find_one({"slug": slug})

        if current_category.get("all_parents"):
            all_parents.extend(current_category["all_parents"])
        parent_url = url_for(".tree", provider=provider, path=slug)
        
        query["parent"] = current_category["category_code"]
    else:
        query["parent"] = None
    
    categories = queries.col_categories().find(query)
    
    return render_template('tree.html', 
                           path=path,
                           provider=_provider,
                           all_parents=all_parents,
                           parent_url=parent_url,
                           categories=categories,
                           current_category=current_category,
                           query=query)
    
#@cache.memoize(360)
def _category_tree(provider):
    return utils.categories_to_dict(current_app.widukind_db, provider)

@bp.route('/categories/<provider>', endpoint="categories")
@bp.route('/categories/<provider>/<parent>', endpoint="categories-branch")
def category_tree_view(provider, parent=None):
    abort(404)
    
    is_ajax = request.args.get('json') or request.is_xhr
    
    tree = _category_tree(provider)
    
    #dataset_codes = queries.col_datasets().distinct("dataset_code", {'provider_name': provider})
    dataset_projection = {"_id": True, "dataset_code": True}
    dataset_codes = {}
    for doc in queries.col_datasets().find({'provider_name': provider}, dataset_projection):
        dataset_codes[doc['dataset_code']] = doc['_id']
    
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
    

