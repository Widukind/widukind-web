# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, url_for, redirect
from pymongo import DESCENDING

from widukind_web import constants
from widukind_web.extensions import auth
from widukind_web.extensions import cache
from widukind_web import queries

bp = Blueprint('admin', __name__)

#TODO: redis cache view


@bp.route('/providers', endpoint="providers")
@auth.required
def all_providers():
    cursor = queries.col_providers().find({})
    providers = [doc for doc in cursor]
    
    datasets_counters = queries.datasets_counter()
    #series_counters = queries.series_counter()
    
    return render_template("admin/providers.html", providers=providers, 
                           datasets_counters=datasets_counters,
                           #series_counters=series_counters
                           )

@bp.route('/datasets/<slug>', endpoint="datasets")
@auth.required
def all_datasets_for_provider_slug(slug):        

    provider = queries.col_providers().find_one({"slug": slug})
    if not provider:
        abort(404)

    datasets = queries.col_datasets().find({"provider_name": provider["name"]})

    return render_template("admin/datasets.html", 
                           provider=provider, 
                           datasets=datasets)

@bp.route('/enable/provider/<slug>', endpoint="provider_enable")
@auth.required
def change_status_provider(slug):

    query = {"slug": slug}
    provider = queries.col_providers().find_one(query)
    if not provider:
        abort(404)
        
    query_update = {}
    if provider["enable"]:
        query_update["enable"] = False
    else:
        query_update["enable"] = True
        
    queries.col_providers().find_one_and_update(query, {"$set": query_update})
    
    datasets_query = {"provider_name": provider["name"]}
    queries.col_datasets().update_many(datasets_query, {"$set": query_update})
    
    return redirect(url_for(".providers"))

@bp.route('/enable/dataset/<slug>', endpoint="dataset_enable")
@auth.required
def change_status_dataset(slug):

    query = {"slug": slug}
    dataset = queries.col_datasets().find_one(query)
    if not dataset:
        abort(404)
        
    query_update = {}
    if dataset["enable"]:
        query_update["enable"] = False
    else:
        query_update["enable"] = True
        
    queries.col_datasets().find_one_and_update(query, {"$set": query_update})

    query = {"name": dataset["provider_name"]}
    provider = queries.col_providers().find_one(query)
    
    return redirect(url_for(".datasets", slug=provider["slug"]))


@bp.route('/cache/clear', endpoint="cache_clear")
@auth.required
def cache_clear():
    cache.clear()
    return redirect(url_for("home"))


@bp.route('/queries', endpoint="queries")
@auth.required
def queries_view():
    
    is_ajax = request.args.get('json') or request.is_xhr
    
    if not is_ajax:
        return render_template("admin/queries.html")
    
    col = current_app.widukind_db[constants.COL_QUERIES]
    
    tags = request.args.get('tags')
    
    q = {}

    if tags:
        tags = tags.split(",")
        q['tags'] = {"$in": tags}
    
    object_list = col.find(q).sort("created", DESCENDING)

    return current_app.jsonify(list(object_list))

@bp.route('/logs', endpoint="logs")
@auth.required
def view_logs():
    """
    {
        "_id" : ObjectId("5665a7182d4b25012092ac71"),
        "message" : "change count for BEA.datasets. old[0] - new[0]",
        "level" : "INFO",
        "timestamp" : Timestamp(1449502488, 860),
        "loggerName" : "widukind_web",
        "thread" : 74212736,
        "threadName" : "DummyThread-1",
        "method" : "upsert",
        "lineNumber" : 271,
        "module" : "wsgi",
        "fileName" : "V:\\git\\cepremap\\src\\widukind-web\\widukind_web\\wsgi.py"
    }    
    """
    is_ajax = request.args.get('json') or request.is_xhr
    
    if not is_ajax:
        return render_template("admin/logs.html")
    
    col = current_app.widukind_db[constants.COL_LOGS]
    
    object_list = col.find({})

    return current_app.jsonify(list(object_list))


        
