odoo.define('theme_scita.scita_product_js', function(require) {
    "use strict";
// Multi image gallery
    var ajax = require('web.ajax');
    var VariantMixin = require('sale.VariantMixin');
    var sAnimations = require('website.content.snippets.animation');
    var api;
    function check()
    {   
        if (chkObject('gallery')==true)
       {    
        
        ajax.jsonRpc('/theme_scita/scita_multi_image_thumbnail_config', 'call', {})
                    .then(function(res) {
            var dynamic_data = {}

            dynamic_data['gallery_images_preload_type'] = 'all'
            dynamic_data['slider_enable_text_panel'] = false
            dynamic_data['gallery_skin'] = "alexis"
            dynamic_data['gallery_height'] = 850
            dynamic_data['slider_scale_mode']='fit'
            dynamic_data['slider_enable_arrows'] = true
            
            dynamic_data['strippanel_enable_handle'] = true
            if (res.theme_panel_position != false) {
                dynamic_data['theme_panel_position'] = res.theme_panel_position
            }
            else{
             dynamic_data['theme_panel_position'] = "left"   
            }
            if (res.color_opt_thumbnail != false && res.color_opt_thumbnail != 'default') {
                dynamic_data['thumb_image_overlay_effect'] = true
                if (res.color_opt_thumbnail == 'b_n_w') {}
                if (res.color_opt_thumbnail == 'blur') {
                    dynamic_data['thumb_image_overlay_type'] = "blur"
                }
                if (res.color_opt_thumbnail == 'sepia') {
                    dynamic_data['thumb_image_overlay_type'] = "sepia"
                }
            }
            if (res.enable_disable_text == true) {
                dynamic_data['slider_enable_text_panel'] = true
            }
            if (res.change_thumbnail_size == true) {
                dynamic_data['thumb_height'] = res.thumb_height
                dynamic_data['thumb_width'] = res.thumb_width
            }
            else{
                dynamic_data['thumb_width'] = 66          
                dynamic_data['thumb_height'] = 86

            }
            if (res.interval_play != false) {
                dynamic_data['gallery_play_interval'] = res.interval_play
            }
            if (res.no_extra_options == false) {
                dynamic_data['slider_enable_progress_indicator'] = false
                dynamic_data['slider_enable_play_button'] = false
                dynamic_data['slider_enable_fullscreen_button'] = false
                dynamic_data['slider_enable_zoom_panel'] = false
                dynamic_data['slider_enable_text_panel'] = false
                dynamic_data['gridpanel_enable_handle'] = false
                dynamic_data['theme_panel_position'] = 'left'
                dynamic_data['thumb_image_overlay_effect'] = false
            }
            api = $('#gallery').unitegallery(dynamic_data);
            api.on("item_change", function(num, data) {
            if (data['index'] == 0) {
                    update_gallery_product_image();
                }
            });
            if (api != undefined && $('#gallery').length != 0) {
                setTimeout(function() {
                    update_gallery_product_image()
                }, 200);
            }
            });
            int=window.clearInterval(int);

       }
       else{

       }
    }
    var int=setInterval(check, 100);
    function chkObject(elemClass)
    {  
       return ($('#'+elemClass).length==1)? true : false;
    }
    // multi image for product id get and vraint image change start
    VariantMixin._onChangeCombinationProd = function (ev, $parent, combination) {
        var product_id = 0;

        // needed for list view of variants
        if ($parent.find('input.product_id:checked').length) {
            product_id = $parent.find('input.product_id:checked').val();
        } else {
            product_id = $parent.find('.product_id').val();
        }
        update_gallery_product_variant_image($parent, product_id);
        
    };
    
    function update_gallery_product_variant_image(event_source, product_id) {
        var $imgs = $(event_source).closest('.oe_website_sale').find('.ug-slide-wrapper');
        var $img = $imgs.find('img');
        if (api!= undefined)
        {
            var total_img = api.getNumItems()
            if (total_img != undefined) {
                api.selectItem(0);
            }
            var $stay;
            $img.each(function(e) {
                if ($(this).attr("src").startsWith('/web/image/scita.product.images/') == false) {
                    
                    $(this).attr("src", "/web/image/product.product/" + product_id + "/image_1920");
                    $("img.js_variant_img_small").attr("src", "/web/image/product.product/" + product_id + "/image_1920");
                    $stay = $(this).parent().parent();
                    $(this).css({
                        'width': 'initial',
                        'height': 'initial'
                    });
                    api.resetZoom();
                    api.zoomIn();
                    
                }
            });    
        }
        
    }

    function update_gallery_product_image() {
        var $container = $('.oe_website_sale').find('.ug-slide-wrapper');
        var $img = $container.find('img');
        var $product_container = $('.oe_website_sale').find('.js_product').first();
        var p_id = parseInt($product_container.find('input.product_id').first().val());

        if (p_id > 0) {
            $img.each(function(e_img) {
                if ($(this).attr("src").startsWith('/web/image/scita.product.images/') == false) {
                    
                    $(this).attr("src", "/web/image/product.product/" + p_id + "/image_1920");
                    
                }
            });
        } else {
            var spare_link = api.getItem(0).urlThumb;
            $img.each(function(e_img) {
                if ($(this).attr("src").startsWith('/web/image/scita.product.images/') == false) {
                    
                    $(this).attr("src", spare_link);
                    
                }
            });
        }
    }
    sAnimations.registry.WebsiteSale.include({
        _onChangeCombination: function (){
            this._super.apply(this, arguments);
            VariantMixin._onChangeCombinationProd.apply(this, arguments);
        }
    });
    // multi image for product id get and vraint image change end

    
    $(document).ready(function () {
        //product detail page cart fix
        if ($('div').hasClass("sct-add-to-cart-mob")){
            $('#wrapwrap').addClass("sct-mobile-pro-detail-list");
        }
        if ($('#product_detail').length != 0) {
            $('body').addClass('sct-cst-pro-page');
        }
        // Product delivery location available checking start
        $('.checker').on('click', function(){
            var zip =  $('input.value-zip').val();
            ajax.jsonRpc("/shop/zipcode", 'call', {
                'zip_code':zip
            }).then(function (data){
                if (data.status == true){
                    $('.get_status').removeClass("fail");
                    $('.get_status').addClass("success");
                    $('#fail_msg').addClass("o_hidden");
                    $('#success_msg').removeClass("o_hidden");
                    $('#blank_msg').addClass("o_hidden");
                    $('input.value-zip').val(zip);
                }
                if (data.status == false) {
                    $('input.value-zip').val(zip);
                    $('.get_status').removeClass("success");
                    $('.get_status').addClass("fail");
                    $('#fail_msg').removeClass("o_hidden");
                    $('#success_msg').addClass("o_hidden");
                    $('#blank_msg').addClass("o_hidden");
                }
                if(data.zip == "notavailable"){
                    $('input.value-zip').val(zip);
                    $('.get_status').removeClass("success");
                    $('.get_status').addClass("fail");
                    $('#fail_msg').addClass("o_hidden");
                    $('#success_msg').addClass("o_hidden");
                    $('#blank_msg').removeClass("o_hidden");
                }
             });
        });
        // Product delivery location available checking end
    });
});