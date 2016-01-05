# -*- coding: utf-8 -*-

import time

from flask import Blueprint, current_app, request, render_template, abort, url_for, redirect

from werkzeug.wsgi import wrap_file

from bson import ObjectId
import gridfs

from widukind_common.tasks import export_files

from widukind_web import constants

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

def fs_list(limit=10, provider=None, dataset_code=None, doc_type=None):
    
    query = {}
    if provider:
        query = {"metadata.provider": provider}
    if dataset_code:
        query = {"metadata.dataset_code": dataset_code}
    if doc_type:
        query = {"metadata.doc_type": doc_type}
        
    recents = current_app.widukind_fs.find(query).sort("uploadDate", -1).limit(limit)
    
    return render_template("download/files.html", files=recents)

@bp.route('/', methods=['GET'])
def index():
    return redirect(url_for("download.fs_list_dataset"))

@bp.route('/list/datasets')
def fs_list_dataset():
    limit = request.args.get('limit', default=20, type=int)
    if limit > 100: limit = 100
    
    return fs_list(limit=limit, 
                   provider=None, 
                   dataset_code=None, 
                   doc_type="dataset")            
        
@bp.route('/list/series/<provider>/<dataset_code>')
@bp.route('/list/series/<provider>')
@bp.route('/list/series')
def fs_list_series(provider=None, dataset_code=None):
    limit = request.args.get('limit', default=20, type=int)
    if limit > 100: limit = 100
    
    return fs_list(limit=limit, 
                   provider=provider, 
                   dataset_code=dataset_code, 
                   doc_type="series")            

def common_download_get(provider_name=None, dataset_code=None, key=None, prefix=None):
    
    filename = export_files.generate_filename_csv(provider_name=provider_name, 
                                                  dataset_code=dataset_code, 
                                                  key=key, 
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
        id = export_func(**export_kwargs)
        end = time.time() - start
        current_app.logger.info("CSV file [%s] created in [%.3f] seconds" % (filename, end))
        try:
            fileobj = current_app.widukind_fs.get(id)
            return fileobj
        except:        
            #TODO: erreur plus précise
            abort(404)
    
@bp.route('/byid/<objectid:id>', endpoint="download-file-by-id")
def download_file(id):
    try:
        fileobj = current_app.widukind_fs.get(id) #ObjectId(id)
    except gridfs.errors.NoFile:
        abort(404)
    
    return send_file(fileobj)

@bp.route('/dataset/<provider>/<dataset_code>', endpoint="datasets_csv")
def download_dataset(provider=None, dataset_code=None):

    query = {'provider_name': provider, "dataset_code": dataset_code}
    exist =  current_app.widukind_db[constants.COL_DATASETS].count(query) == 1
    if not exist:
        current_app.logger.error("download csv for not existant dataset[%(dataset_code)s] - provider[%(provider)s]" % query)
        abort(404)

    filename, fileobj = common_download_get(provider_name=provider, 
                                            dataset_code=dataset_code, 
                                            prefix="dataset")
    if not fileobj:
        fileobj = common_download_create(filename=filename, 
                                         export_func=export_files.export_file_csv_dataset_unit,
                                         provider=provider, 
                                         dataset_code=dataset_code)
        
    return send_file(fileobj)

@bp.route('/series/<provider>/<dataset_code>/<key>', endpoint="series_csv")
def download_series(provider=None, dataset_code=None, key=None):

    query = {'provider_name': provider, "dataset_code": dataset_code, "key": key}
    exist =  current_app.widukind_db[constants.COL_SERIES].count(query) == 1
    if not exist:
        current_app.logger.error("download csv for not existant serie[%(key)s] - dataset[%(dataset_code)s] - provider[%(provider)s]" % query)
        abort(404)

    filename, fileobj = common_download_get(provider_name=provider, 
                                            dataset_code=dataset_code, 
                                            prefix="series")
    if not fileobj:
        fileobj = common_download_create(filename=filename, 
                                         export_func=export_files.export_file_csv_series_unit,
                                         provider=provider, 
                                         dataset_code=dataset_code,
                                         key=key)
    
    return send_file(fileobj)

