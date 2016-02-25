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

/*
function toggle_content(options){

    //var menu_left_col = options.menu_left_col || widukind_options.menu_left_col;
    //var page_col = options.page_col || widukind_options.page_col;
	
    var $site_menu_left = $("#site_menu_left");
    var $site_page = $("#site_content");
    
	if ($site_menu_left.is(':visible')) {
		$site_menu_left.hide();
		$site_page.removeClass('col-md-10');
		$site_page.addClass('col-md-12');
	} else {
		$site_menu_left.show();
		$site_page.removeClass('col-md-12');
		$site_page.addClass('col-md-10');		
	} 
}
*/

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
    /*
    return [
            '<div class="btn-group btn-group-xs btn-group-justified" role="group">',
            
                //'<a class="btn btn-xs add_cart" href="#" data-series-id="' + row.slug + '" title="Add Cart">',
                //  '<i class="fa fa-shopping-cart fa-lg"></i>',                          
                //'</a>',
            
            '</div>'
    ].join('');
    */
}

function addCart(url){
    $(".add_cart").on('click', function(e){

    	e.preventDefault();
       
        var _id = $(this).attr("data-series-id");
        
        $.ajax({
            url: url,
            data: {"id": _id},
            cache: false,
            complete: function(jqXHR, textStatus){
                if (textStatus == "success"){
                	var response = jqXHR.responseJSON;
                    $("#badge_cart").text(response.count);
                }
            }
       });
        
    });
}
    
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
			query.push("providers: " + item.query.provider_name.join(',') );
		}
		query.push("limit: " + item.query.limit);
		query.push("sort: " + item.query.sort);
		item.query = query.join(" - ");		
	});
	return res;
}

