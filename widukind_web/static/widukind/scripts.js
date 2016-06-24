var widukind_options = {
    spin_opts: {
          lines: 13 // The number of lines to draw
        , length: 28 // The length of each line
        , width: 14 // The line thickness
        , radius: 42 // The radius of the inner circle
        , scale: 1 // Scales overall size of the spinner
        , corners: 1 // Corner roundness (0..1)
        , color: '#000' // #rgb or #rrggbb or array of colors
        , opacity: 0.2 // Opacity of the lines
        , rotate: 0 // The rotation offset
        , direction: 1 // 1: clockwise, -1: counterclockwise
        , speed: 1 // Rounds per second
        , trail: 60 // Afterglow percentage
        , fps: 20 // Frames per second when using setTimeout() as a fallback for CSS
        , zIndex: 2e9 // The z-index (defaults to 2000000000)
        , className: 'spinner' // The CSS class to assign to the spinner
        , top: '50%' // Top position relative to parent
        , left: '50%' // Left position relative to parent
        , shadow: true // Whether to render a shadow
        , hwaccel: false // Whether to use hardware acceleration
        , position: 'absolute' // Element positioning
    }
};

function datasetLastUpdateFormatter(value, row) {
    return new String(moment(value).format('LL')); // + " (" + new String((moment(value).fromNow())) + ")";
}

function datasetDownloadLastFormatter(value, row) {
    return new String(moment(value).format('LL')); // + " (" + new String((moment(value).fromNow())) + ")";
}

function createdFormatter(value, row) {
    return new String(moment(value).format('L')) + " (" + new String((moment(value).fromNow())) + ")";
}

function datasetNameFormatter(value, row){
	return '<a href="' + row.view + '" title="Dataset link">' + value + '</a>';
}

function datasetButtonFormatter(value, row){
    var d = [];
    d.push('<div class="btn-group btn-group-xs" role="group"><center>');
    d.push('<div class="btn btn-xs btn-group" role="group">');
    d.push('<a href="' + row.series + '" title="Series link">');
    d.push('<i class="fa fa-stack-exchange fa-lg"></i>');
    d.push('</a>');
    d.push('</div>');
    if ( row.docHref ) {
        d.push('<div class="btn btn-xs btn-group" role="group">');          
        d.push('<a target="_blank" href="' + row.docHref + '" title="Web Site"><i class="fa fa-external-link-square fa-lg"></i></a>');
        d.push('</div>');
    }
    d.push('</center></div>');
    return d.join('');
}

function seriesKeyLinkFormatter(value, row){
    return '<a href="' + row.view + '" title="Show detail">' + row.key +'</a>';
}

function is_revisions_Formatter(value, row){
	if ( row.is_revisions === true ) {
    	return '<i class="fa fa-check"></i>';
    } else {
    	return '&nbsp;';
    }
}


function seriesNameLinkFormatter(value, row){
    return '<a href="' + row.view + '" title="Show detail">' + row.name +'</a>';
}

/*
function seriesButtonFormatter(value, row, line){
    var _html = [];
    _html.push('<div class="btn-group btn-group-xs btn-group-justified" role="group">');

    if (row.export_csv){
    	_html.push('<a class="btn btn-xs" href="' + row.export_csv + '" title="CSV Export">');
		_html.push('<i class="fa fa-file-excel-o fa-lg"></i>');                          
		_html.push('</a>');
    }
    
    if (row.view_graphic) {
		_html.push('<a target="_blank" class="btn btn-xs view_graphic" rel="'+ line + '" href="' + row.view_graphic + '" title="Graphic">');
		_html.push('<i class="fa fa-area-chart fa-lg"></i>');
		_html.push('</a>');
    }
    
    _html.push('</div>');
    return _html.join('');
}
*/
    
function spinnerShow(){
    $('#spinner').spin(widukind_options.spin_opts);
}

function spinnerHide(){
    $('#spinner').spin(false);
}

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

function ajax(uri, method, data, new_options, callback_error) {
	
    var options_default = {
        timeout: 120 * 1000, //120 seconds
        async: true,
        //cache: true,
        //accepts: "application/json",
        //contentType: "application/json",
        //dataType: 'json',
    };
	
	var options = $.extend(true, {}, options_default, new_options);
	
    var request = {
        url: uri,
        type: method,
        async: options.async,
        timeout: options.timeout,
        //contentType: options.contentType,
        //accepts: options.accepts,
        cache: options.cache,
        //dataType: options.dataType,
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
		        }
		   	});
		   $(options.parent_id).toggle();
	    }
	});
}
        