# -*- coding: utf-8 -*-

from wtforms.fields.html5 import SearchField 
from wtforms import fields, widgets, validators
from wtforms.validators import DataRequired
from wtforms.validators import ValidationError
from flask_wtf import Form

from bson import ObjectId 

from widukind_web import constants 
from widukind_common.utils import get_mongo_db

class QuerySetSelectField(fields.SelectFieldBase):

    widget = widgets.Select()

    def __init__(self, label='', 
                 colname=None,
                 id_attr='_id', label_attr='', 
                 query={},
                 validators=None, 
                 allow_blank=False, blank_text='---', **kwargs):
        super().__init__(label, validators, **kwargs)
        self.id_attr = id_attr
        self.label_attr = label_attr
        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self.colname = colname
        self.query = query or {}
        self.db = get_mongo_db()
        self.col = self.db[self.colname]
        self.queryset = self.db[self.colname].find(query)

    def iter_choices(self):
        if self.allow_blank:
            yield ('', self.blank_text, self.data is None)

        if self.queryset is None:
            return

        self.queryset.rewind()
        
        for obj in self.queryset:
            _id = str(obj[self.id_attr])
            
            label = self.label_attr and obj.get(self.label_attr) or _id
            
            if isinstance(self.data, list):
                selected = _id in self.data
            else:
                selected = self._is_selected(_id)
                
            yield (_id, label, selected)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                if self.queryset is None:
                    self.data = None
                    return
                query = {}
                if self.id_attr == "_id":
                    query['_id'] = ObjectId(valuelist[0])
                else:
                    query[self.id_attr] = valuelist[0]
                    
                obj = self.col.find_one(query)
                if obj:                    
                    self.data = str(obj.get(self.id_attr))
                else:
                    self.data = None

    def pre_validate(self, form):
        if not self.allow_blank or self.data is not None:
            if not self.data:
                raise ValidationError('Not a valid choice')

    def _is_selected(self, item):
        #print("_is_selected : ", item, type(item), self.data, type(self.data))
        #BIS <class 'str'> None <class 'NoneType'>
        return item == self.data

class QuerySetSelectMultipleField(QuerySetSelectField):

    widget = widgets.Select(multiple=True)

    def __init__(self, label='', 
        colname=None, 
        id_attr='_id', label_attr='', 
        query={}, 
        validators=None, 
        allow_blank=False, blank_text='---', **kwargs):
        super().__init__(label=label, colname=colname, id_attr=id_attr, label_attr=label_attr, query=query, validators=validators, allow_blank=allow_blank, blank_text=blank_text, **kwargs)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                if not self.queryset:
                    self.data = None
                    return

                query = {}
                if self.id_attr == "_id":
                    values = [ObjectId(d) for d in valuelist]
                    query['_id'] = {"$in": values}
                else:
                    query[self.id_attr] = {"$in": valuelist}
                    
                objs = self.col.find(query)
                if objs.count() > 0:                    
                    self.data = [str(obj.get(self.id_attr)) for obj in objs]
                else:
                    self.data = None

                #self.data = [obj for obj in self.queryset if str(obj['_id']) in valuelist]
                #if not len(self.data):
                #    self.data = None

    def _is_selected(self, item):
        return item in self.data if self.data else False


class SearchFormDatasets(Form):
    
    query = SearchField(validators=[DataRequired()])
    
    providers = QuerySetSelectMultipleField(colname=constants.COL_PROVIDERS, 
                                            id_attr='name',
                                            label_attr='name',
                                            allow_blank=True,
                                            #blank_text=""
                                            query={"enable": True},
                                            )
    
    limit = fields.IntegerField(default=20)
    
    sort = fields.SelectField(choices=constants.CHOICES_SORT_DATASETS, 
                              default="last_update")
    
    #TODO: DESC
        
class SearchFormSeries(SearchFormDatasets):
    
    datasets = QuerySetSelectMultipleField(colname=constants.COL_DATASETS, 
                                            id_attr='dataset_code',
                                            label_attr='dataset_code',
                                            allow_blank=True,
                                            query={"enable": True},
                                            )
    
    frequency = fields.SelectField(choices=[("All", "All")] + list(constants.FREQUENCIES), default="All")

    #TODO: start_date = fields.StringField()
    start_date = fields.HiddenField()
    
    #TODO: end_date = fields.StringField()
    end_date = fields.HiddenField()
    
    sort = fields.SelectField(choices=constants.CHOICES_SORT_SERIES, default="start_date")
        
        