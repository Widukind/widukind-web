# -*- coding: utf-8 -*-

import time

from flask import Blueprint, current_app, request, render_template, abort, url_for, redirect
from werkzeug.wsgi import wrap_file
import gridfs

from widukind_common.tasks import export_files
from widukind_web import constants
from widukind_web import queries

bp = Blueprint('download', __name__)

def send_file(fileobj, version=-1, mimetype=None, filename=None, cache_for=31536000):
    """
    #pour fs.get_version(filename=filename, version=version)
    version=-1,
    
    #number of seconds 
    cache_for=31536000        
    
    #date de création ?
    fileobj.upload_date
    """        
    
    #print("filename: ", fileobj.filename)
    #print("metadata : ", fileobj.metadata)
    
    filename = filename or fileobj.filename
            
    data = wrap_file(request.environ, fileobj, buffer_size=1024 * 256)
    response = current_app.response_class(
                        data,
                        mimetype=mimetype or fileobj.content_type,
                        direct_passthrough=True)    
    response.headers["Content-disposition"] = "attachment; filename=%s" % filename
    response.content_length = fileobj.length
    response.last_modified = fileobj.upload_date
    response.set_etag(fileobj.md5)
    """
    response.cache_control.max_age = cache_for
    response.cache_control.s_max_age = cache_for
    response.cache_control.public = True
    """        
    response.make_conditional(request)
    return response        

def fs_list(limit=10, 
            provider=None, dataset_code=None,  
            slug=None, 
            doc_type=None):
    
    query = {}
    if provider:
        query = {"metadata.provider_name": provider}
    if dataset_code:
        query = {"metadata.dataset_code": dataset_code}
    if slug:
        query = {"metadata.slug": slug}
    if doc_type:
        query = {"metadata.doc_type": doc_type}
        
    recents = current_app.widukind_fs.find(query).sort("uploadDate", -1).limit(limit)
    
    return render_template("download/files.html", files=recents, doc_type=doc_type)

@bp.route('/', methods=['GET'])
def index():
    return redirect(url_for("download.fs_list_dataset"))

@bp.route('/list/datasets/<provider>')
@bp.route('/list/datasets')
def fs_list_dataset(provider=None):
    
    limit = request.args.get('limit', default=20, type=int)
    if limit > 100: limit = 100
    
    if provider:
        doc = queries.col_providers().find_one({"slug": provider},
                                               {"name": True, "enable": True})
        if not doc:
            current_app.logger.error("provider[%s] not found" % provider)
            abort(404)
            
        if doc["enable"] is False:
            current_app.logger.error("disable provider[%s]" % provider)
            abort(307)
    
    return fs_list(limit=limit,
                   slug=provider,
                   #provider=provider, 
                   #dataset_code=None, 
                   doc_type="dataset")            
        
@bp.route('/list/series/<provider>/<dataset>')
@bp.route('/list/series/<provider>')
@bp.route('/list/series')
def fs_list_series(provider=None, dataset=None):
    limit = request.args.get('limit', default=20, type=int)
    if limit > 100: limit = 100

    slug = None

    if provider:
        slug = provider
        
        doc = queries.col_providers().find_one({"slug": provider},
                                               {"slug": True, "name": True, 
                                                "enable": True})
        if not doc:
            current_app.logger.error("provider[%s] not found" % provider)
            abort(404)
            
        if doc["enable"] is False:
            current_app.logger.error("disable provider[%s]" % provider)
            abort(307)

    if dataset:
        slug = dataset
        
        doc = queries.col_datasets().find_one({"slug": dataset},
                                               {"provider_name": True,
                                                "name": True, "slug": True, 
                                                "enable": True})
        if not doc:
            current_app.logger.error("dataset[%s] not found" % dataset)
            abort(404)
            
        if doc["enable"] is False:
            current_app.logger.error("disable dataset[%s]" % dataset)
            abort(307)
    
    return fs_list(limit=limit, 
                   slug=slug, 
                   doc_type="series")            

def common_download_get(provider_name=None, 
                        dataset_code=None, 
                        key=None,
                        slug=None,
                        prefix=None):
    
    filename = export_files.generate_filename_csv(provider_name=provider_name, 
                                                  dataset_code=dataset_code, 
                                                  key=key,
                                                  slug=slug, 
                                                  prefix=prefix)
    try:
        fileobj = current_app.widukind_fs.get_last_version(filename)
        return filename, fileobj
    except gridfs.errors.NoFile:
        return filename, None

def common_download_create(filename=None,
                           export_func=None,
                           **export_kwargs):
    
        start = time.time()
        current_app.logger.warn("CSV %s not found. Creating..." % filename)
        _id = export_func(**export_kwargs)
        end = time.time() - start
        
        current_app.logger.info("CSV file [%s] created in [%.3f] seconds" % (filename, end))
        try:
            fileobj = current_app.widukind_fs.get(_id)
            return fileobj
        except:        
            #TODO: erreur plus précise
            abort(404)
    
@bp.route('/byid/<objectid:unid>', endpoint="download-file-by-id")
def download_file(unid):
    try:
        fileobj = current_app.widukind_fs.get(unid)
    except gridfs.errors.NoFile:
        abort(404)
    
    return send_file(fileobj)

@bp.route('/dataset/<slug>', endpoint="datasets_csv")
def download_dataset(slug):

    query = {"slug": slug}
    projection = {"enable": True, "dataset_code": True, "provider_name": True}
    doc =  current_app.widukind_db[constants.COL_DATASETS].find_one(query, projection)
    if not doc:
        current_app.logger.error("dataset[%s] not found" % slug)
        abort(404)
        
    if doc["enable"] is False:
        current_app.logger.error("disable dataset[%s]" % slug)
        abort(307)

    filename, fileobj = common_download_get(slug=slug, 
                                            prefix="dataset")
    if not fileobj:
        fileobj = common_download_create(filename=filename, 
                                         export_func=export_files.export_file_csv_dataset_unit,
                                         slug=slug)
        
    return send_file(fileobj)

@bp.route('/series/<slug>', endpoint="series_csv")
def download_series(slug):
    
    query = {"slug": slug}    
    series = queries.col_series().find_one(query)

    if not series:
        abort(404)

    provider_name = series['provider_name']
    dataset_code = series['dataset_code']
        
    dataset = queries.col_datasets().find_one({"enable": True,
                                               'provider_name': provider_name,
                                               "dataset_code": dataset_code})
    if not dataset:
        abort(404)

    filename, fileobj = common_download_get(slug=slug, prefix="series")
    
    if not fileobj:
        fileobj = common_download_create(filename=filename, 
                                         export_func=export_files.export_file_csv_series_unit,
                                         provider=provider_name, 
                                         dataset_code=dataset_code,
                                         key=series["key"],
                                         slug=slug)
    
    return send_file(fileobj)

