
var selectedProvider;
var selectedDataset;
var selectedTags = [];
var bestTags;
var loaded_tags = null;
var providers_by_slug = {};
var datasets_by_slug = {};
var datasets_by_slug_dscode = {};
var cartSeries = [];
var search;
var dimension_filter = [];
var full_dimension_filter = {};
var is_filter = false;
var api_no_select_text = "Select an provider and an dataset for completed URL !";
var api_no_select_dim_text = "Select one or more dimensions !";
var count_series = 0;
var dimensionFields = [];
var loaded_datatree = null;
var searchableTree;
var cartCount = 0;
var limit = 0;

var widukind_options = {
    url_tags: null,
    url_tree: null,
    url_explorer: null,
    url_providers: null,
    url_cart_view: null,
    url_cart_remove: null,
    url_export_csv: null,
    url_api_sdmx: null,
    url_api_json: null,
    url_api_html: null,
};

var chosen_default_options = {
   search_contains: true,
   allow_single_deselect: true,
};

function AdminQueriesResponseHandler(res){
	_.forEach(res, function(item){
		var tags = item.tags;
		item.tags = tags.join(", ");
		
		var query = [];
		query.push("search: " + item.query.search_tags);		
		if (item.query.provider_name){
			//console.log(item.query.provider_name);
			query.push("providers: " + item.query.provider_name );
			//query.push("providers: " + item.query.provider_name.join(',') );
		}
		query.push("limit: " + item.query.limit);
		query.push("sort: " + item.query.sort);
		item.query = query.join(" - ");		
	});
	return res;
}

function AdminQueriesLinkFormatter(value, row){
    return '<a href="' + row.view + '" title="Show detail">Show</a>';
}

function Provider(data) {
    this.id = data.slug;
    this.text = data.name;
}

function Dataset(data) {
    this.id = data.slug;
    this.text = data.dataset_code + ' - ' + data.name;
    this.dataset_code = data.dataset_code;
}

function local_treeview(tree, callback){
	
	if (searchableTree){
	   searchableTree.treeview('remove');
	}
	
	searchableTree = $('#tree-tree').treeview({
    	data: tree,
    	enableLinks: false,
    	showTags: false,
    	onhoverColor: 'none',
    	expandIcon: 'fa fa-plus-circle',
    	onNodeSelected: function(event, data) {
    		if (data.href) {
    			selectedDataset = _.last(data.href.split('/'));
    			return callback();
    		} else {
    			$('#tree-tree').treeview('toggleNodeExpanded', [ data.nodeId, { silent: false } ]);
    		}
    	}
    });

    $('#tree_btn_search').on('click', function(e){
        var pattern = $('#tree_search').val();
        var options = {
          ignoreCase: true,
          exactMatch: false,
          revealResults: true
        };
        var results = searchableTree.treeview('search', [ pattern, options ]);
    });

    $('#tree_btn_clear').on('click', function (e) {
      searchableTree.treeview('clearSearch');
      $('#tree_search').val('');
      searchableTree.treeview('collapseAll', { silent: true });
      //$('#search-output').html('');
    });

    $('#tree-tree').on('nodeSelected', function(event, data) {
   		if (! data.nodes){
   			//TODO: $('#selectedCategory').text(data.text);
   			$('#sidebarnav a[href="#tab-form"]').tab('show');
   			$('html, body').animate({ scrollTop: 0 }, 0); //go to top page
   			
   			// set selected dataset in select field
   			$.each($('#dataset option'), function(i, item) {
   				var _item = $(this);  
   				if (_item.val() === selectedDataset){
   					$(this).prop('selected', true);
   					$("#dataset").trigger("chosen:updated");
   					$("#selectedDataset").text(selectedDataset);
   					return;
   				}
   			});
   		}
    });
}


function ajax(uri, method, data, new_options, callback_error) {
	
    var options_default = {
        timeout: 120 * 1000, //120 seconds
        cache: true,
        //accepts: "application/json",
        //contentType: "application/json",
        dataType: 'json',
    };
	
	var options = $.extend(true, {}, options_default, new_options);
	
    var request = {
        url: uri,
        type: method,
        timeout: options.timeout,
        //contentType: options.contentType,
        //accepts: options.accepts,
        cache: options.cache,
        dataType: options.dataType,
        data: data,
        //traditional: true,
        error: function(jqXHR, textStatus, errorThrown) {
        	//TODO: ecrire erreur dans champs status
        	//if(textStatus === 'timeout')
        	if (callback_error){
        		callback_error(jqXHR, textStatus, uri, method, data, options);
        	} else {
        		console.log("ajax error : ", jqXHR, textStatus);
        	}
        }
    };
    return $.ajax(request);
}

function debug_dataset(options) {
	
    $(options.button_id).click(function(e){
        e.preventDefault();
        if ($(options.parent_id).is(":visible")) {
        	$(options.parent_id).toggle();	
        } else {
 		   	$.ajax({
		        url: options.url,
		        cache: false,
		        complete: function(jqXHR, textStatus){
		            if (textStatus == "success"){
		            	$(options.target_id).text(jqXHR.responseJSON);
		            }
		        }
		   	});
 		   $(options.parent_id).toggle();
        }
    });
}

function debug_series(options) {

	$(options.button_id).click(function(e){
	    e.preventDefault();
	    if ( $(options.parent_id).is(":visible") ) {
	    	$(options.parent_id).toggle();	
	    } else {
		   	$.ajax({
		        url: options.url,
		        cache: false,
		        success: function(result) {
		        	$(options.target_series_id).text(result.series);
		        	$(options.target_dataset_id).text(result.dataset);
                    $(options.target_provider_id).text(result.provider);
		        }
		   	});
		   $(options.parent_id).toggle();
	    }
	});
}

function writeGraph(data, target){
    var datas = [];
    var options = {
        labels: ['Period', 'Value'],
        title: data.meta.name,
        titleHeight: 24,
        includeZero: true,
        showRangeSelector: true
    };
    
    _.each(data.data, function(item){
        datas.push([new Date(item.period_ts), parseFloat(item.value)]);
    });
    
    new Dygraph(target, datas, options);
}

function loadGraph(url){
    
    ajax(url, 'GET').done(function(data) {

        var dialog = bootbox.alert({
            title: data.meta.provider_name + ' - ' + data.meta.dataset_code + ' - ' + data.meta.key,
            backdrop: true,
            size: 'large',
            closeButton: false,
            message: '<div id="graphdiv" style="width:100%; background-color: white;"></div>'
        }).on('shown.bs.modal', function () {
            writeGraph(data, "graphdiv");
        });
    });

}

function revisionsDiff(){
	//Parcours tableau revisions pour faire ressortir diff
	$("#seriesRevisions > tbody > tr").each(function(i, item){ 
		  var line = $(item).find("span.revision");
		  var period = $(line).eq(0).text();
		  var current_value = $(line).eq(1).text();
		  var value = $(line).eq(2).text();
		  if (current_value!==value){
		    console.log(i, period, current_value, value, current_value===value);
		  }
		  //TODO: attributes
	});	
}

function onLoadSeries(){
    $('#sidebarnav-series a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        e.preventDefault();
        var href = $(e.target).attr('href');

        if ( href == "#tab-modal-graph" ){
            var url = $(this).attr("data-series-plot-url");
            ajax(url, 'GET').done(function(data) {
                writeGraph(data, "graphdiv-modal");
            });
        }
    });
    //$('#seriesIdentity').bootstrapTable();
    $('#seriesRevisions').bootstrapTable();
    $('#seriesDatas').bootstrapTable();
}

function onShownModal(){

	var dialog = this;
	
    onLoadSeries();
    
    flask_moment_render_all();
    
    $('[data-toggle="tooltip"]').tooltip({
        placement: 'auto left',
    });
    
    $('#modal-detail .modal_show').on('click', function(e){
    	e.preventDefault();
    	$(dialog).modal('hide');
        var title = $(this).attr("data-title");
        var url = $(this).attr("data-url");
        ajax(url, 'GET', {}, {dataType: 'html', accepts: 'text/html'}).done(function(data) {
            var dialog = bootbox.alert({
                title: title,
                backdrop: true,
                size: 'large',
                closeButton: false,
                message: data
            }).on('shown.bs.modal', onShownModal);
        });
    });
}

function modal_show(e){
    e.preventDefault();
    var title = $(this).attr("data-title");
    var url = $(this).attr("data-url");
    ajax(url, 'GET', {}, {dataType: 'html', accepts: 'text/html'}).done(function(data) {
        var dialog = bootbox.alert({
            title: title,
            backdrop: true,
            size: 'large',
            closeButton: false,
            message: data
        }).on('shown.bs.modal', onShownModal);
    });
}    

function add_cart(e){
    e.preventDefault();
    var url = $(this).attr("data-cart-add-url");
    var slug = $(this).attr("data-series-slug");
    ajax(url, 'GET').done(function(data) {
        $("#cart_count").text(data.count);
        cartCount = data.count;
        toastr[data.notify.category](data.notify.msg, {timeOut: 2000});
    });
}

function show_graph(e){
    e.preventDefault();
    var url = $(this).attr("data-series-plot-url");
    loadGraph(url);
}

function createdFormatter(value, row) {
    return new String(moment(value).format('L')) + " (" + new String((moment(value).fromNow())) + ")";
}

function seriesKeyLinkFormatter(value, row){
    return '<small><a class="modal_show" data-url="'+ row.view +'" href="javascript:void(0)" title="Show detail">' + row.key +'</a></small>';
    //return '<small>' + value + '</small>';
  ////<a title="View series" data-title="View series" type="button" class="btn btn-default modal_show" href="javascript:void(0)" data-url="{{view}}"><i class="fa fa-eye"></i></a>
}

function seriesButtonFormatter(value, row, line){
    return Mustache.render(template_table_buttons, row)
}

function seriesButtonFormatterLight(value, row, line){
    return Mustache.render(template_table_buttons_light, row)
}

function providerFormatter(value, row){
    return '<small>' + value +'</small>';
}

function datasetCodeLinkFormatter(value, row){
    return '<small>' + value + '</small>';
    //return '<small><a class="modal_show" data-title="Dataset" data-url="' + row.view_dataset +'" data-dataset-slug="' + row.dataset_slug + '" href="javascript:void(0)" title="Show dataset">' + value +'</a></small>';
}

function periodFormatter(value, row){
    return '<span class="label label-default">' + row.start_date + ' -> ' + row.end_date + '</span>';
}

function frequencyFormatter(value, row){
    return '<span class="label label-default">' + row.frequency_txt + '</span>';
}

function nameFormatter(value, row){
    return '<small>' + value + '</small>'
}

function detailFormatter(index, row) {
    var o = {meta: {index: index}, row: row};
    return Mustache.render(template_detail, o);
};

function menusite_toogle(){
    var site_left = $('#site-left');
    var site_content = $('#site-content');
    
    if (site_left.is(':visible')) {
        site_left.hide();
        site_content.removeClass('col-md-9');
        site_content.addClass('col-md-12');
    } else {
        site_content.removeClass('col-md-12');
        site_content.addClass('col-md-9');
        site_left.show();
    }
}

function refresh_selectedTags(){
    $('#selectedTags').empty();
    if (! _.isEmpty(selectedTags)){
        var result = Mustache.render(template_tags_selected, {tags: selectedTags});
    } else {
        var result = "None";
    }
    $('#selectedTags').html(result);
}

function get_sdmx_link(){
		var api_sdmx = [widukind_options.url_api_sdmx];
		api_sdmx.push(providers_by_slug[selectedProvider]);
		api_sdmx.push("data");
		api_sdmx.push(datasets_by_slug_dscode[selectedDataset]);
		if (is_filter){
			api_sdmx.push(dimension_filter.join('.').toUpperCase());
		} else {
			api_sdmx.push('all');
		}
		return api_sdmx.join('/');
}

function get_json_link(){
		var api_json = [widukind_options.url_api_json];
		api_json.push("datasets");
		api_json.push(selectedDataset);
		api_json.push("values");
		api_json = api_json.join('/');
		if (is_filter){
			api_json = api_json + '?' + $.param(full_dimension_filter);
		}
		return api_json;
}

function get_html_link(){
	/*
	{#
	//http://widukind-api-dev.cepremap.org/api/v1/html/datasets/insee-ipch-2015-fr-coicop/values?frequency=M&produit=10
	//http://widukind-api-dev.cepremap.org/api/v1/html/datasets/insee-ipch-2015-fr-coicop/values?frequency=m
	//http://widukind-api-dev.cepremap.org/api/v1/html/datasets/bis-pp-ls/values?reference-area=fr+au&frequency=Q
	//http://widukind-api-dev.cepremap.org/api/v1/html/datasets/bis-pp-ls/Q/values?reference-area=fr+au
	var api_html = [widukind_options.url_api_html];
	api_html.push("datasets");
	api_html.push(selectedDataset);
	api_html.push("values");
	api_html = api_html.join('/');
	if (is_filter){
		api_html = api_html + '?' + $.param(full_dimension_filter);
	}
	$("#htmlURL").attr('href', api_html);
	$("#htmlURL").text(api_html);
	#}
	*/
}

function api_display_sdmx(){
	var message;
	
	if (! _.isEmpty(selectedDataset) && count_series < 1000) {
		var _message = [];
		var _msg = get_sdmx_link();
		_message.push('<div class="form-group"><div class="input-group margin-bottom-sm">');
		_message.push('<input class="form-control" type="text" id="sdmxLink" value="' + _msg + '"/>');
		_message.push('<span id="clip_btn" title="Copy to clipboard" class="input-group-addon" data-clipboard-target="#sdmxLink"><i class="fa fa-clipboard fa-fw"></i></span>');
		_message.push('</div>');
		_message.push('<span class="text-primary text-right help-block"><small>Click to icon for copy url in clipboard.<small></span>');
		_message.push('</div>');
		message = _message.join('');
		new Clipboard('#clip_btn');
		
	} else {
		if (_.isEmpty(selectedDataset)){
			message = '<span class="text-danger">Selected dataset is required !</span>';
		} else {
			message = '<span class="text-warning">Too many data</span> Select an provider and an dataset for completed URL !';
		}
	}
	bootbox.alert({
		title: "SDMX Api link",
		backdrop: true,
		closeButton: false,
		message: message
	});		    	
}

function api_display_json(){
	var message;
	
	if (! _.isEmpty(selectedDataset) && count_series < 1000) {
		var _message = [];
		var _msg = get_json_link();
		_message.push('<div class="form-group"><div class="input-group margin-bottom-sm">');
		_message.push('<input class="form-control" type="text" id="jsonLink" value="' + _msg + '"/>');
		_message.push('<span id="clip_btn" title="Copy to clipboard" class="input-group-addon" data-clipboard-target="#jsonLink"><i class="fa fa-clipboard fa-fw"></i></span>');
		_message.push('</div>');
		_message.push('<span class="text-primary text-right help-block"><small>Click to icon for copy url in clipboard.<small></span>');
		_message.push('</div>');
		message = _message.join('');
		new Clipboard('#clip_btn');
		
	} else {
		if (_.isEmpty(selectedDataset)){
			message = '<span class="text-danger">Selected dataset is required !</span>';
		} else {
			message = '<span class="text-warning">Too many data</span> Select an provider and an dataset for completed URL !';
		}
	}
	bootbox.alert({
		title: "JSON Api link",
		backdrop: true,
		closeButton: false,
		message: message
	});		    	
}

function on_ready_explorer(){
	
	limit = $('#limit').val();
	
	var $table = $('#series-list').bootstrapTable({
		formatShowingRows: function(){
			return '';	
		}
	});
	/*
    FIXME: bypass buttons click
    .on('click-row.bs.table', function(e, row, element){
        console.log("event : ", e);
        e.preventDefault();
        //$(element).toggleClass("active-row");
        ajax(row.view, 'GET', {}, {dataType: 'html', accepts: 'text/html'}).done(function(data) {
            var dialog = bootbox.alert({
                title: row.name,
                backdrop: true,
                size: 'large',
                closeButton: false,
                message: data
            }).on('shown.bs.modal', function () {
                flask_moment_render_all();
            });
        });
    });
    */    	
	
    var $search_form = $('#form-search').formValidation({
        framework: 'bootstrap',
        excluded: [':disabled'],
        icon: {
            valid: 'glyphicon glyphicon-ok',
            invalid: 'glyphicon glyphicon-remove',
            validating: 'glyphicon glyphicon-refresh'
        },
        fields: {
            search: {
                validators: {
                    notEmpty: {
                        message: 'The query is required'
                    },
                    stringLength: {
                        min: 3,
                        message: 'The name must be more than 3 characters long'
                    },
                }
            },
        }
    })
   	.on('err.field.fv', function(e, data) {
   		data.fv.disableSubmitButtons(false);
   	})
   	.on('success.field.fv', function(e, data) {
   		data.fv.disableSubmitButtons(false);
   	})
    .on('success.form.fv', function(e) {
        e.preventDefault();
        //console.log("event e : ", e);
		//console.log("success.form - search val : ", $('#search').val());
		search = $('#search').val();
		loadData();
		$('#sidebarnav a[href="#tab-form"]').tab('show');
		$('#selectedSearch').text(search);
    });

	$('#form-search').on('reset', function (e) {
		$('#selectedSearch').text("None");
		$('#search').empty();
		search = null;
		loadData();
		$('#sidebarnav a[href="#tab-form"]').tab('show');
	});

    /*
	$('#search_btn_search').click(function (e) {
		e.preventDefault();
		console.log("search val : ", $('#search').val());
		return false;
	});
	*/
	
    $('#form-explorer').formValidation({
        framework: 'bootstrap',
        excluded: [':disabled'],
        icon: {
            valid: 'glyphicon glyphicon-ok',
            invalid: 'glyphicon glyphicon-remove',
            validating: 'glyphicon glyphicon-refresh'
        },
        
    });	
    
    $('#form-settings').formValidation({
        framework: 'bootstrap',
        icon: {
            valid: 'glyphicon glyphicon-ok',
            invalid: 'glyphicon glyphicon-remove',
            validating: 'glyphicon glyphicon-refresh'
        },
    });
									
	$('#infosnavbar a').on('click', function (e) {
		e.preventDefault();
		var select_tab = $(this);
		
		if (select_tab.attr('id') === 'sidetoogle'){
			menusite_toogle();
			return;
		} else {
			switch(select_tab.attr('href')) {
			    case '#tab-settings':
					//$('#limit').chosen();
			        break;
			    //default:
			    //    default code block
			}
		}
		//select_tab.tab('show');
	});
	
	$('#sidebarnav a').on('click', function (e) {
		e.preventDefault()

		if ( $(this).attr('href') == "#tab-tree" ){
			if (_.isEmpty(selectedProvider)){
				var _error = '<div class="alert alert-danger" role="alert">Select a provider for display this tree.</div>'
				$('#tree-tree').html(_error);
				return;
			} else {
				if (loaded_datatree === selectedProvider){
					return;
				}
				var url = widukind_options.url_tree + selectedProvider;
				ajax(url, 'GET', {}, {dataType: 'script'}).done(function(data) {
		  		    local_treeview(datatree.tree, loadData);
		  		});
				loaded_datatree = selectedProvider;
			}
		} else if ( $(this).attr('href') == "#tab-tags" ){
			local_tags(loadData);
			return;
		}
	});

	
    function loadData(){
  		var url = widukind_options.url_explorer;
  		var options = {};
  		
  		options.limit = limit;
  		
  		if (selectedDataset) {
  			options.dataset = selectedDataset;
  		}
  		else if (! _.isEmpty(selectedProvider)) {
  			options.provider = selectedProvider;
  		}
        /*
        if (! _.isEmpty(selectedSeries)) {
            options.series = selectedSeries;
        }
        */
  		
  		dimension_filter = [];
  		full_dimension_filter = {};
  		is_filter = false;
  		
  		//var search = $('#search').val();
  		if (! _.isEmpty(search)) {
  			options.search = search;
  		}

        //TODO: tags
        /*
  		if (! _.isEmpty(selectedTags)) {
  			options.tags = selectedTags.join(' ');
  		}
  		*/
  		
  		_.forEach(dimensionFields, function(dim) {
  			var add_filter;
  			if (! _.isEmpty(dim.selectedOption)){
  				options['dimensions_' + dim.key] = dim.selectedOption.join(' ');
  				add_filter = dim.selectedOption.join('+');
  				if (! _.isEmpty(add_filter) ){
  					is_filter = true;
  					full_dimension_filter[dim.key] = add_filter;
  				}
  			} else {
  				add_filter = "";
  			}
  			dimension_filter.push(add_filter);
  		});

  		ajax(url, 'GET', options).done(function(data) {
        	$table.bootstrapTable('load', data.data);
        	$("#count_series").text(Humanize.formatNumber(data.data.length));
            $("#total_series").text(Humanize.formatNumber(data.meta.total));
            count_series = data.meta.total;
  		});
  	};
	
  	function loadProviders(){
		var url = widukind_options.url_providers;
		
		ajax(url, 'GET').done(function(data) {
            var providers = $.map(data.data, function(item) { return new Provider(item) });
            
            $('#provider').empty().append('<option value="">Select a Provider</option>');
            
            _.each(providers, function(item) {
            	providers_by_slug[item.id] = item.text;
            	if (selectedProvider && selectedProvider === item.id){
            		$('#provider').append($("<option></option>").attr("value", item.id).attr("selected", "true").text(item.text));
            	} else {
	            	$('#provider').append($("<option></option>").attr("value", item.id).text(item.text));
            	}
            });
            
            $('#provider').chosen(chosen_default_options);
		});
  	};
  	
  	function loadDatasets(){
  		if (_.isEmpty(selectedProvider)){
  			cleanDataset();
  			return;
  		}
  		
  		$("#dataset").chosen("destroy");
  		
		var url = '/views/ajax/providers/'+ selectedProvider +'/datasets';
		ajax(url, 'GET').done(function(data) {
            var datasets = $.map(data.data, function(item) { return new Dataset(item) });
            
            $('#dataset').empty().append('<option value="">Select a Dataset</option>');
            
            _.each(datasets, function(item) {
            	datasets_by_slug[item.id] = item.text;
            	datasets_by_slug_dscode[item.id] = item.dataset_code;
            	if (selectedDataset && selectedDataset === item.id){
            		$('#dataset').append($("<option></option>").attr("value", item.id).attr("selected", "true").text(item.text));
            	} else {
	            	$('#dataset').append($("<option></option>").attr("value", item.id).text(item.text));
            	}
            	//$('#dataset').append($("<option></option>").attr("value", item.id).text(item.text));
            });
            
            $('#dataset').chosen(chosen_default_options);
        });
  	};

  	function loadDimensions(){
  		
  		if ( _.isEmpty(selectedDataset) ){
  			cleanDimensions();
  			return;
  		}

  		cleanDimensions();
  		dimensionFields = new Array()
  		
		var url = '/views/ajax/datasets/'+ selectedDataset +'/dimensions/all';
		
		ajax(url, 'GET').done(function(data) {
			
			_.forEach(data.data, function(item){
        		var options = [];
        		
        		$.each(item.codes, function(key2, item2){
        			options.push({"id": key2, "text": item2});
        		});
        		
        		var newobj = {
        			"key": item.key,
        			"selectedOption": [],
        			"selectedDataset": selectedDataset,
        			"options": options,
        			"caption": item.name
        		};
        		dimensionFields.push(newobj);
        	});
        	
			_.forEach(dimensionFields, function(dim) {
		    	var rendered = Mustache.render(template, dim);
		        var result = $("#form-explorer").append(rendered);
		    });
			
			_.forEach(dimensionFields, function(dim) {
				$("#" + dim.key).chosen("destroy");
				
				$("#" + dim.key).chosen(chosen_default_options)
				.on('change', function() {
					dim.selectedOption = $(this).val();
					loadData();
				});
			});
			
		});
		
  	};

  	function cleanDataset(){
  		selectedDataset = null;
  		$('#dataset').empty().chosen();
  		$("#selectedDataset").text("All");
  		dimension_filter = [];
		is_filter = false;
  	}

  	function cleanDimensions(){
  		_.forEach(dimensionFields, function(dim) {
  			$("#" + dim.key).chosen("destroy");
  			$("#form_group_" + dim.key).remove();
  		});
  		dimensionFields = new Array();
  		dimension_filter = [];
		is_filter = false;
  		$("#sdmxURL").text(api_no_select_text);
  		$("#jsonURL").text(api_no_select_text);
  		//$("#htmlURL").text(api_no_select_text);
  	}
  	
  	$('#limit').on('change', function() {
  		limit = this.value;
  		$('#infosnavbar a[href="#tab-infos"]').tab('show');
  		loadData();
  	});	
  	
  	$('#provider').on('change', function() {
  		selectedProvider = $(this).val();
  		cleanDataset();
  		cleanDimensions();
  		if (selectedProvider){
  			$("#selectedProvider").text(providers_by_slug[selectedProvider]);
  		} else {
  			$("#selectedProvider").text("All");
  		}
  		//TODO: tags : selectedTags = [];
  		//TODO: tags : refresh_selectedTags();
  		$('#search').val('');
        $('#selectedSearch').text('None');
  		$('#tree-tree').val('');
        $('#tree_search').val('');
        loadDatasets();
  		loadData();
  	});	
  	
  	$('#dataset').on('change', function() {	  		
  		selectedDataset = this.value;
  		if (selectedDataset){
  			$("#selectedDataset").text(datasets_by_slug[selectedDataset]);
  		} else {
  			$("#selectedDataset").text("All");
  		}
  		cleanDimensions();
  		loadDimensions();
  		loadData();
  	});	

	loadProviders();
	loadDatasets();

		if (!_.isEmpty(selectedProvider)){
			$("#selectedProvider").text(providers_by_slug[selectedProvider]);
		}
		
		if (!_.isEmpty(selectedDataset)){
			$("#selectedDataset").text(datasets_by_slug[selectedDataset]);
			loadDimensions();
		}

    loadData();
    
    $("#series-list").delegate('.modal_show', 'click', modal_show);
    $("#series-list").delegate('.add_cart', 'click', add_cart);
    $("#series-list").delegate('.view_graph', 'click', show_graph);

    
    /*
    TODO: tags
    $("#tab-tags").delegate('.tag', 'click', function(e){
    	e.preventDefault();
    	var tag = $(this).attr('data-tag');
    	if (_.indexOf(selectedTags, tag) >= 0){
    		_.pull(selectedTags, tag);
    	} else {
    		selectedTags.push(tag);
    	}
    	$(this).toggleClass("label label-success");
    	refresh_selectedTags();
    	loadData();
    });
	
	$("#tab-infos").delegate('.tag-selected', 'click', function(e){
    	e.preventDefault();
    	var tag = $(this).attr('data-tag');
    	_.pull(selectedTags, tag);
    	$('.tag[data-tag="' + tag + '"]').toggleClass("label label-success");
    	refresh_selectedTags();
    	loadData();
    });
    */
    
    $("#down-sdmx").on('click', function(e){
		e.preventDefault();
		api_display_sdmx();
	});

    $("#down-json").on('click', function(e){
		e.preventDefault();
		api_display_json();
	});
	
	function reset_all_filters(){
        cleanDimensions();
        cleanDataset();
        selectedTags = [];
        refresh_selectedTags();
        search = null;
        $('#search').empty();
        if (! _.isEmpty(search)){
            $('#tree-tree').treeview('clearSearch');
        }
        loadDatasets();
        $('a.label-success').each(function(item){
            $(this).toggleClass("label label-success");
        });
        loadData();
	}
	
    $("#tab-reset-filters").on('click', function(e){
        e.preventDefault();
        reset_all_filters();
    });
	
    $("#viewCart").on('click', function(e){
		e.preventDefault();
		
		if (cartCount <= 0){
		 return false;
		}
		
    	var url = widukind_options.url_cart_view;
    	ajax(url, 'GET', {}, {"dataType": "html"}).done(function(data) {
    		
    		var dialog = bootbox.alert({
    			title: "Series cart",
    			backdrop: true,
    			size: 'large',
    			closeButton: false,
    			message: data
    		})
    		.on('shown.bs.modal', function () {
    			
    			var $cart = $('#series_cart').bootstrapTable();
    			var selected_cart = [];
    			
    			$cart.on('load-success.bs.table', function(data){
    			
    			    $("#series_cart").delegate('.modal_show', 'click', modal_show);
    			    $("#series_cart").delegate('.add_cart', 'click', add_cart);
    			    $("#series_cart").delegate('.view_graph', 'click', show_graph);
    				
	    	    	$('#checkAll').on('click', function (e) {
                        e.preventDefault();
	    	            $cart.bootstrapTable('checkAll');
	    	        });
	    	    	$('#uncheckAll').on('click', function (e) {
                        e.preventDefault();
	    	            $cart.bootstrapTable('uncheckAll');
	    	        });
	    	        
	    	        function removeCart(data){
                        $("#cart_count").text(data.count);
                        cartCount = data.count;
                        if (cartCount > 0) {
                            $cart.bootstrapTable('refresh', {});
                        } else {
                          dialog.modal('hide');
                        }
                        toastr[data.notify.category](data.notify.msg, {timeOut: 2000});
	    	        }
	    	    	
	    	        $('#delete').on('click', function (e) {
                        e.preventDefault();
                        var url = widukind_options.url_cart_remove + "?slug=all";
                        ajax(url, 'GET').done(function(data) {
                            removeCart(data);
                        });
	    	        });

                    $('.remove_cart').on('click', function (e) {
                        e.preventDefault();
                        var url = $(this).attr("data-cart-remove-url");
                        ajax(url, 'GET').done(function(data) {
                            removeCart(data);
                            /*
                            $("#cart_count").text(data.count);
                            cartCount = data.count;
                            if (cartCount > 0) {
                                $cart.bootstrapTable('refresh', {});
                            } else {
                              dialog.modal('hide');
                            }
                            toastr[data.notify.category](data.notify.msg, {timeOut: 2000});
                            */
                        });
                    });
	    	        
                    $('#cart-export-csv').on('click', function (e) {
                        e.preventDefault();
                        
                        var index = [];
                        var selected = $cart.bootstrapTable('getData');
                        
                        $('input[name="btSelectItem"]:checked').each(function () {
                            index.push(selected[$(this).data('index')].slug);
                        });
                        
                        if (_.isEmpty(index)){
                            var err_msg = "No selected series.";
                            toastr['error'](err_msg, {showDuration: 3000, 
                                                     timeOut: 4000,
                                                     closeButton: true});
                            return;
                        }
                        
                        var url_export_csv = widukind_options.url_export_csv + "/" + index.join('+');
                        $("#cart-export-csv-link").toggle().html('<a target="_blank" href="' + url_export_csv + '">Click here for download</a>');
                        
                        $("#cart-export-csv-link a").on('click', function(e){
                            $("#cart-export-csv-link").toggle();
                            return true;
                        });
                        
                    });
                    
    			});
    	        
    		});
    	});
	});
    
	/*
    $('.sparklines').sparkline('html', {
		width: '50px',
		height: '20px',
		//normalRangeMax: 20,
	});
	*/
	
}

$(document).ready(function() {

    $('.human-number').each(function(i, item){
        var value = $(item).text();
         $(item).text(Humanize.formatNumber(value));
    });

    $('.human-size-mb').each(function(i, item){
        var value = $(item).text();
         $(item).text(Humanize.fileSize(value));
    });
    
    toastr.options = {
      "closeButton": true,
      "debug": false,
      "newestOnTop": false,
      "progressBar": true,
      "positionClass": "toast-top-right",
      "preventDuplicates": false,
      "onclick": null,
      "showDuration": "3000",
      "hideDuration": "1000",
      "timeOut": "5000",
      "extendedTimeOut": "8000",
      "showEasing": "swing",
      "hideEasing": "linear",
      "showMethod": "fadeIn",
      "hideMethod": "fadeOut"
    };
    
    $(document).ajaxStart($.blockUI).ajaxStop($.unblockUI);
    
    var ajaxErrorMsg = "<h2>An unexpected error has occurred</h2>"+
                       "<p>The administrator has been notified.</p>"+
                       "<p>Sorry for the inconvenience!</p>";

    $(document).ajaxError(function(){
        toastr['error'](ajaxErrorMsg, {showDuration: 5000, 
                                      closeButton: true});
    });
    
    $("#contactLink").on('click', function(e){
        e.preventDefault();
        var url = $(this).attr("data-url") + '?modal=1';
        ajax(url, 'GET', {}, {"dataType": "html"}).done(function(data) {
            var dialog = bootbox.dialog({
                //title: 'Contact Form',
                backdrop: true,
                size: 'large',
                closeButton: false,
                show: false,
                message: data
            }).on('shown.bs.modal', function () {
                $('#contactForm')
                    .show()
                    .formValidation('resetForm', true);
                    
                $('#contactFormCancel').on('click', function(e){
                    //$('#contactForm').hide();
                    //$('#contactForm').formValidation('resetForm', true);
                    dialog.modal('hide');
                });
                    
            }).on('hide.bs.modal', function(e) {
                $('#contactForm').hide();
            }).modal('show');
        });
    });
        
});        

/*
function sparkFormatter(value, row) {
	var 	values = _.sortBy(row.values, function(num) { return _.ceil(parseFloat(num), 2); });
	return '<span class="sparklines" values="' + values.join(',') + '"></span>';
}

function sparkStyle(value, row, index){
	  	return {
		    //classes: 'text-nowrap',
		    css: {"background-color": "white"}
	};    	
}
*/

/*
//TODO: tags
function local_tags(){

    if (_.isEmpty(selectedProvider)){
        var _error = '<div class="alert alert-danger" role="alert">Select a provider for load tags.</div>'
        $('#tags-cloud').html(_error);
        return;
    }

	if (loaded_tags === selectedProvider){
		return;
	}
	
	var url = widukind_options.url_tags + selectedProvider;
	if (! _.isEmpty(selectedDataset) ){
	   url = url + '&dataset=' + selectedDataset;
	}
	ajax(url, 'GET').done(function(data) {
		if (data.length > 0) {
			//remove tag if name start with number value
			var tags = _.filter(data, function(item) { return _.isNaN(_.parseInt(item.name[0])); });
			var result = Mustache.render(template_tags, {tags: tags});
		} else {
			var result = '<span class="text-warning">No tags found</span>';
		}
		$('#tags-cloud').html(result);
		loaded_tags = selectedProvider;
		});

}
*/



