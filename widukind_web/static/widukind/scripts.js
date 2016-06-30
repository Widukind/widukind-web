
var widukind_options = {
    url_tags: null,
    url_tree: null,
    url_explorer: null,
    url_providers: null,
    url_cart_view: null,
    url_export_csv: null, 
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
}

function onShownModal(){
    
    onLoadSeries();
    
    flask_moment_render_all();
    
    $('[data-toggle="tooltip"]').tooltip({
        placement: 'auto left',
    });
    
}

function table_buttons(){
    //button in first column of data table
    
    $(".modal_show").off('click').on('click', function(e){
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
    });
    
    $(".add_cart").off('click').on('click', function(e){
        e.preventDefault();
        var url = $(this).attr("data-cart-add-url");
        var slug = $(this).attr("data-series-slug");
        ajax(url, 'GET').done(function(data) {
            $("#cart_count").text(data.count);
            cartCount = data.count;
            toastr[data.notify.category](data.notify.msg, {timeOut: 2000});
        });         
    });
    
    $(".view_graph").off('click').on('click', function(e){
        e.preventDefault();
        var url = $(this).attr("data-series-plot-url");
        loadGraph(url);
    });
}
    
function after_loadData(){
    table_buttons(); 
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

function seriesKeyLinkFormatter(value, row){
    return '<small>' + value + '</small>';
    //return '<small><a class="modal_show" data-title="Series details" data-url="' + row.view +'" data-series-slug="' + row.slug + '" href="javascript:void(0)" title="Show detail">' + row.key +'</a></small>';
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
        ajax(url, 'GET').done(function(data) {
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