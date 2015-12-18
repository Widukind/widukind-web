# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, url_for, redirect
from pymongo import DESCENDING

from widukind_web import constants
from widukind_web.extensions import auth
from widukind_web.extensions import cache

bp = Blueprint('admin', __name__)

#TODO: redis cache view

@bp.route('/cache/clear', endpoint="cache_clear")
@auth.required
def cache_clear():
    cache.clear()
    return redirect(url_for("home"))


@bp.route('/queries', endpoint="queries")
@auth.required
def queries():
    
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


        
