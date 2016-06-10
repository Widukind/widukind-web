#!/bin/bash

curl -OL http://cdnjs.cloudflare.com/ajax/libs/awesome-bootstrap-checkbox/0.3.7/awesome-bootstrap-checkbox.min.css
curl -OL http://cdnjs.cloudflare.com/ajax/libs/select2/3.5.4/select2.min.css
curl -OL https://cdnjs.cloudflare.com/ajax/libs/select2/3.5.4/select2-spinner.gif
curl -OL https://cdnjs.cloudflare.com/ajax/libs/select2/3.5.4/select2.png
curl -OL https://cdnjs.cloudflare.com/ajax/libs/select2/3.5.4/select2x2.png
curl -OL http://cdnjs.cloudflare.com/ajax/libs/select2/3.5.4/select2-bootstrap.min.css

curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-daterangepicker/2.1.19/daterangepicker.min.css
curl -OL http://cdnjs.cloudflare.com/ajax/libs/formvalidation/0.6.1/css/formValidation.min.css
curl -OL http://cdnjs.cloudflare.com/ajax/libs/chosen/1.5.1/chosen.min.css
curl -OL https://cdnjs.cloudflare.com/ajax/libs/chosen/1.5.1/chosen-sprite.png
curl -OL https://cdnjs.cloudflare.com/ajax/libs/chosen/1.5.1/chosen-sprite@2x.png

curl -OL http://cdnjs.cloudflare.com/ajax/libs/select2/3.5.4/select2.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-daterangepicker/2.1.19/daterangepicker.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/formvalidation/0.6.1/js/formValidation.min.js
curl http://cdnjs.cloudflare.com/ajax/libs/formvalidation/0.6.1/js/framework/bootstrap.min.js -o formvalidation-bootstrap.min.js 
curl -OL http://cdnjs.cloudflare.com/ajax/libs/jquery-sparklines/2.1.2/jquery.sparkline.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/chosen/1.5.1/chosen.jquery.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/mustache.js/2.2.1/mustache.min.js    

curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-treeview/1.2.0/bootstrap-treeview.min.css
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-treeview/1.2.0/bootstrap-treeview.min.js

curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/bootstrap-table.min.css

curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/bootstrap-table.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/extensions/cookie/bootstrap-table-cookie.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/extensions/export/bootstrap-table-export.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/extensions/filter-control/bootstrap-table-filter-control.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/extensions/filter/bootstrap-table-filter.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/extensions/flat-json/bootstrap-table-flat-json.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/extensions/mobile/bootstrap-table-mobile.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/extensions/natural-sorting/bootstrap-table-natural-sorting.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/extensions/toolbar/bootstrap-table-toolbar.min.js
curl -OL http://cdnjs.cloudflare.com/ajax/libs/bootstrap-table/1.10.1/locale/bootstrap-table-en-US.min.js

mkdir css fonts
curl http://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.6.3/css/font-awesome.min.css -o css/font-awesome.min.css 
curl http://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.6.3/fonts/FontAwesome.otf -o fonts/FontAwesome.otf
curl http://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.6.3/fonts/fontawesome-webfont.eot -o fonts/fontawesome-webfont.eot
curl http://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.6.3/fonts/fontawesome-webfont.svg -o fonts/fontawesome-webfont.svg
curl http://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.6.3/fonts/fontawesome-webfont.ttf -o fonts/fontawesome-webfont.ttf
curl http://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.6.3/fonts/fontawesome-webfont.woff -o fonts/fontawesome-webfont.woff
curl http://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.6.3/fonts/fontawesome-webfont.woff2 -o fonts/fontawesome-webfont.woff2

curl -O http://cdnjs.cloudflare.com/ajax/libs/jquery/2.2.4/jquery.min.js
curl -O http://cdnjs.cloudflare.com/ajax/libs/spin.js/2.3.2/spin.min.js
curl -OL http://raw.githubusercontent.com/fgnass/spin.js/master/jquery.spin.js
curl -O http://cdnjs.cloudflare.com/ajax/libs/humanize-plus/1.6.0/humanize.min.js
curl -O http://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.13.1/lodash.min.js
curl -O http://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.13.1/lodash.min.js.map
curl -O http://cdnjs.cloudflare.com/ajax/libs/mustache.js/2.2.1/mustache.min.js
curl -O http://cdnjs.cloudflare.com/ajax/libs/moment.js/2.13.0/moment.min.js

curl -OL http://dygraphs.com/1.1.1/dygraph-combined.js
curl -O http://cdnjs.cloudflare.com/ajax/libs/jquery-sparklines/2.1.2/jquery.sparkline.min.js 

curl -L -o bootstrap3-typeaheadjs.css http://raw.githubusercontent.com/bassjobsen/typeahead.js-bootstrap-css/master/typeaheadjs.css
curl -O http://cdnjs.cloudflare.com/ajax/libs/bootstrap-3-typeahead/4.0.1/bootstrap3-typeahead.min.js
curl -O http://cdnjs.cloudflare.com/ajax/libs/typeahead.js/0.11.1/bloodhound.min.js
#bloodhound.js + typeahead.jquery.js
#curl -O http://cdnjs.cloudflare.com/ajax/libs/typeahead.js/0.11.1/typeahead.bundle.min.js

curl -O http://cdnjs.cloudflare.com/ajax/libs/bootstrap-tagsinput/0.8.0/bootstrap-tagsinput.css
curl -O http://cdnjs.cloudflare.com/ajax/libs/bootstrap-tagsinput/0.8.0/bootstrap-tagsinput-typeahead.css
curl -O http://cdnjs.cloudflare.com/ajax/libs/bootstrap-tagsinput/0.8.0/bootstrap-tagsinput.min.js

curl -O http://cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.4.0/bootbox.min.js
curl -O http://cdnjs.cloudflare.com/ajax/libs/clipboard.js/1.5.12/clipboard.min.js


