odoo.define('aspl_pos_combo.pos', function (require) {
"use strict";

	var models = require('point_of_sale.models');
	var gui = require('point_of_sale.gui');
	var screens = require('point_of_sale.screens');
	var PopupWidget = require('point_of_sale.popups');

	var core = require('web.core');
	var QWeb = core.qweb;
    var _t = core._t;

	models.load_fields("product.product", ['is_combo','product_combo_ids']);
	models.load_fields("res.company", ['street','street2','city','logo']);

	models.PosModel.prototype.models.push({
        model: 'product.combo',
        loaded: function (self, product_combo) {
            self.product_combo = product_combo;
        }
    });

	var _super_Order = models.Order.prototype;
	models.Order = models.Order.extend({
        get_total_item : function(){
            var totalItem = 0;
            this.orderlines.each(function(line){
                if(line.get_display_price() > 0)
                    totalItem += line.get_quantity();
            });

            return totalItem;
        },
        get_exac_total_item : function(){
            var totalItemExac = 0;
            this.orderlines.each(function(line){
                if(line.get_display_price() > 0)
                    totalItemExac += line.get_quantity();
            });

            return totalItemExac;
        },
		add_product: function(product, options){
        	var self = this;
        	_super_Order.add_product.call(this, product, options);
        	if(product.is_combo && product.product_combo_ids.length > 0 && self.pos.config.enable_combo){
        		self.pos.gui.show_popup('combo_product_popup',{
        			'product':product
        		});
        	}
		},
		build_line_resume: function(){
        	var self = this;
            var resume = {};

            this.orderlines.each(function(line){
                if (line.mp_skip) {
                    return;
                }
                var line_hash = line.get_line_diff_hash();
                var qty  = Number(line.get_quantity());
                var note = line.get_note();
                var product_id = line.get_product().id;

                if (typeof resume[line_hash] === 'undefined') {
                    var combo_info = false;
                    if(line.combo_prod_info && line.combo_prod_info.length > 0){
                        combo_info = line.combo_prod_info;
                    }
                    resume[line_hash] = {
                        qty: qty,
                        note: note,
                        product_id: product_id,
                        product_name_wrapped: line.generate_wrapped_product_name(),
                        combo_info: combo_info || false,
                    };
                } else {
                    resume[line_hash].qty += qty;
                    resume[line_hash].combo_info = combo_info;
                }
            });
            return resume;
        },
        computeChanges: function(categories){
            var current_res = this.build_line_resume();
            var old_res     = this.saved_resume || {};
            var json        = this.export_as_JSON();
            var add = [];
            var rem = [];
            var line_hash;

            for ( line_hash in current_res) {
                var curr = current_res[line_hash];
                var old  = old_res[line_hash];

                if (typeof old === 'undefined') {
                    add.push({
                        'id':       curr.product_id,
                        'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     curr.note,
                        'qty':      curr.qty,
                        'combo_info': curr.combo_info,
                    });
                } else if (old.qty < curr.qty) {
                    add.push({
                        'id':       curr.product_id,
                        'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     curr.note,
                        'qty':      curr.qty - old.qty,
                        'combo_info': curr.combo_info,
                    });
                } else if (old.qty > curr.qty) {
                    rem.push({
                        'id':       curr.product_id,
                        'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     curr.note,
                        'qty':      old.qty - curr.qty,
                        'combo_info': curr.combo_info,
                    });
                }
            }

            for (line_hash in old_res) {
                if (typeof current_res[line_hash] === 'undefined') {
                    var old = old_res[line_hash];
                    if(old){
                    	rem.push({
                            'id':       old.product_id,
                            'name':     this.pos.db.get_product_by_id(old.product_id).display_name,
                            'name_wrapped': old.product_name_wrapped,
                            'note':     old.note,
                            'qty':      old.qty,
                            'combo_info': old.combo_info,
                        });
                    }
                }
            }

            if(categories && categories.length > 0){
                // filter the added and removed orders to only contains
                // products that belong to one of the categories supplied as a parameter

                var self = this;

                var _add = [];
                var _rem = [];

                for(var i = 0; i < add.length; i++){
                    if(self.pos.db.is_product_in_category(categories,add[i].id)){
                        _add.push(add[i]);
                    }
                }
                add = _add;

                for(var i = 0; i < rem.length; i++){
                    if(self.pos.db.is_product_in_category(categories,rem[i].id)){
                        _rem.push(rem[i]);
                    }
                }
                rem = _rem;
            }

            var d = new Date();
            var hours   = '' + d.getHours();
                hours   = hours.length < 2 ? ('0' + hours) : hours;
            var minutes = '' + d.getMinutes();
                minutes = minutes.length < 2 ? ('0' + minutes) : minutes;

            return {
                'new': add,
                'cancelled': rem,
                'table': json.table || false,
                'floor': json.floor || false,
                'name': json.name  || 'unknown order',
                'time': {
                    'hours':   hours,
                    'minutes': minutes,
                },
            };

        },
	});

	var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
    	initialize: function(attr,options){
            this.combo_prod_info = false;
            _super_orderline.initialize.call(this, attr, options);
        },
        init_from_JSON: function(json) {
        	var self = this;
        	_super_orderline.init_from_JSON.apply(this,arguments);
			var new_combo_data = [];
			if(json.combo_ext_line_info && json.combo_ext_line_info.length > 0){
				json.combo_ext_line_info.map(function(combo_data){
					if(combo_data[2].product_id){
						var product = self.pos.db.get_product_by_id(combo_data[2].product_id);
						if(product){
							new_combo_data.push({
								'product':product,
								'price':combo_data[2].price,
								'unit_price':combo_data[2].unit_price,
								'qty':combo_data[2].qty,
								'id':combo_data[2].id,
							});
						}
					}
				});
			}
			self.set_combo_prod_info(new_combo_data);
        },
        // overwrite set quantiy
        set_quantity: function(quantity, keep_price){
    	    keep_price = true
    	    _super_orderline.set_quantity.call(this,quantity, keep_price);
        },
        set_combo_prod_info: function(combo_prod_info){
        	this.combo_prod_info = combo_prod_info;
        	this.trigger('change',this);
        },
        get_combo_prod_info: function(){
        	return this.combo_prod_info;
        },
        export_as_JSON: function(){
            var self = this;
            var json = _super_orderline.export_as_JSON.call(this,arguments);
            var combo_ext_line_info = [];
            if(this.product.is_combo && this.combo_prod_info.length > 0){
                _.each(this.combo_prod_info, function(item){
                	combo_ext_line_info.push([0, 0, {
                		'product_id':item.product.id, 
                		'qty':item.qty,
                        'unit_price':item.unit_price,
                		'price':item.price,
                		'id':item.id,
                	}]);
                });
            }
            json.combo_ext_line_info = this.product.is_combo ? combo_ext_line_info : [];
            return json;
        },
        can_be_merged_with: function(orderline){
        	var result = _super_orderline.can_be_merged_with.call(this,orderline);
        	if(orderline.product.id == this.product.id && this.get_combo_prod_info()){
        		return false;
        	}
        	return result;
        },
        export_for_printing: function(){
            var lines = _super_orderline.export_for_printing.call(this);
            lines.combo_prod_info = this.get_combo_prod_info();
            return lines;
        },
    });

	var POSComboProductPopup = PopupWidget.extend({
        template: 'POSComboProductPopup',
        events: _.extend({}, PopupWidget.prototype.events, {
    		'click .collaps_div': 'collaps_div',
    		'click .product.selective_product': 'select_product',
    	}),
        show: function(options){
        	var self = this;
            this._super(options);
            this.product = options.product || false;
            this.combo_product_info = options.combo_product_info || false;
            var combo_products_details = [];
            this.new_combo_products_details = [];
            this.scroll_position = 0;
            this.product.product_combo_ids.map(function(id){
            	var record = _.find(self.pos.product_combo, function(data){
            		return data.id === id;
            	});
            	combo_products_details.push(record);
            });
            combo_products_details.map(function(combo_line){
        		var details = [];
        		if(combo_line.product_ids.length > 0){
        			combo_line.product_ids.map(function(product_id){
        				if(combo_line.require){
        					var data = {
                        		'no_of_items':combo_line.no_of_items,
                        		'product_id':product_id,
                        		'category_id':combo_line.pos_category_id[0] || false,
                        		'used_time':combo_line.no_of_items,
                        	}
            				details.push(data);
        				}else{
                            var data = {
                                'no_of_items':combo_line.no_of_items,
                                'product_id':product_id,
                                'category_id':combo_line.pos_category_id[0] || false,
                                'used_time':0
                            }
                            if(self.combo_product_info){
                                self.combo_product_info.map(function(line){
                                    if(combo_line.id == line.id && line.product.id == product_id){
                                        data['used_time'] =  line.qty;
                                    }
                                });
                            }
                            details.push(data);
        				}
        			});
        			self.new_combo_products_details.push({
        				'id':combo_line.id,
        				'no_of_items':combo_line.no_of_items,
        				'pos_category_id':combo_line.pos_category_id,
        				'product_details':details,
        				'product_ids':combo_line.product_ids,
        				'require':combo_line.require,
        			});
        		}
            });
            this.renderElement();
        },
        collaps_div: function(event){
        	if($(event.currentTarget).hasClass('fix_products')){
        		$('.combo_header_body').slideToggle('500');
        		$(event.currentTarget).find('i').toggleClass('fa-angle-down fa-angle-up');
        	}else if($(event.currentTarget).hasClass('selective_products')){
        		$('.combo_header2_body').slideToggle('500');
        		$(event.currentTarget).find('i').toggleClass('fa-angle-down fa-angle-up');
        	}
        },
        select_product: function(event){
        	var self = this;
        	var $el = $(event.currentTarget);
        	var product_id = Number($el.data('product-id'));
        	var category_id = Number($el.data('categ-id'));
        	var line_id = Number($el.data('line-id'));
        	self.scroll_position = Number(self.$el.find('.combo_header2_body').scrollTop()) || 0;
        	if($(event.target).hasClass('fa-times') || $(event.target).hasClass('product-remove')){
        		if($el.hasClass('selected')){
        			self.new_combo_products_details.map(function(combo_line){
                		if(!combo_line.require){
                			if(combo_line.id == line_id && combo_line.pos_category_id[0] == category_id && (_.contains(combo_line.product_ids, product_id))){
                				combo_line.product_details.map(function(product_detail){
                					if(product_detail.product_id == product_id){
                						product_detail.used_time = 0;
                					}
                				});
                			}
                		}
                	});
            	}
        	}else{
            	self.new_combo_products_details.map(function(combo_line){
            		if(!combo_line.require){
            			if(combo_line.id == line_id && combo_line.pos_category_id[0] == category_id && (_.contains(combo_line.product_ids, product_id))){
            				var added_item = 0;
            				combo_line.product_details.map(function(product_detail){
            					added_item += product_detail.used_time;
            				});
            				combo_line.product_details.map(function(product_detail){
            					if(product_detail.product_id == product_id){
            						if(product_detail.no_of_items > product_detail.used_time && product_detail.no_of_items > added_item){
            							product_detail.used_time += 1;
            						}
            					}
            				});
            			}
            		}
            	});
        	}
        	self.renderElement();
        },
        click_confirm: function(){
            var self = this;
            var order = self.pos.get_order();
            var total_amount = 0;
            var products_info = [];
            var pricelist = self.pos.gui.screen_instances.products.product_list_widget._get_active_pricelist();

            total_amount = self.product.get_price(pricelist, 1);

            var promotion_list = self.pos.pos_promotions;
            var pos_discount_multi_prods = self.pos.pos_discount_multi_prods;
			var pos_discount_multi_categ = self.pos.pos_discount_multi_categ;

            self.new_combo_products_details.map(function(combo_line){
            	if(combo_line.product_details.length > 0){
            		combo_line.product_details.map(function(prod_detail){
            			if(prod_detail.used_time){
            				var product = self.pos.db.get_product_by_id(prod_detail.product_id);
                            var disc_line_record = false;
                            var disc_product_line_record = false;

            				//CHECK PROMOTION PRODUCT ON COMBO
                            if(promotion_list && promotion_list[0]){
                                _.each(promotion_list, function(promotion) {
                                    if (promotion && promotion.promotion_type == "discount_on_multi_product") {
                                        if (promotion.multi_products_discount_ids && promotion.multi_products_discount_ids[0]) {
                                            _.each(promotion.multi_products_discount_ids, function (disc_line_id) {
                                                disc_product_line_record = _.find(pos_discount_multi_prods, function (obj) {
                                                    return obj.id == disc_line_id
                                                });
                                                // if (disc_line_record) {
                                                //     self.check_products_for_disc(disc_line_record, promotion);
                                                // }
                                            })
                                        }
                                    } else if (promotion && promotion.promotion_type == "discount_on_multi_categ") {
                                        if (promotion.multi_categ_discount_ids && promotion.multi_categ_discount_ids[0]) {
                                            _.each(promotion.multi_categ_discount_ids, function (disc_line_id) {
                                                disc_line_record = _.find(pos_discount_multi_categ, function (obj) {
                                                    return obj.id == disc_line_id
                                                });
                                                // if (disc_line_record) {
                                                //     console.log('discount category');
                                                //     console.log(disc_line_record);
                                                //     // self.check_categ_for_disc(disc_line_record, promotion);
                                                // }
                                            })
                                        }
                                    }
                                });
                            }

                			if(product){
                			    var cb_discount = 0;
                			    var cb_unit_price = product.get_price(pricelist, 1);

                			    // console.log(disc_line_record);

                			    if(disc_line_record){
                			        if(disc_line_record.categ_ids.indexOf(product.pos_categ_id[0]) >= 0){
                			            cb_discount = disc_line_record.categ_discount;
                			            cb_unit_price = product.get_price(pricelist, 1) * ((100 - disc_line_record.categ_discount)/100);
                                    }
                                }

                			    // console.log(disc_product_line_record);

                			    if(disc_product_line_record){
                			        if(disc_product_line_record.product_ids.indexOf(product.id) >= 0){
                			            cb_discount = disc_product_line_record.products_discount;
                			            cb_unit_price = product.get_price(pricelist, 1) * ((100 - disc_product_line_record.products_discount)/100);
                			            console.log(disc_product_line_record.products_discount)
                			            console.log(cb_unit_price)
                                    }
                                }

                				products_info.push({
                					"product":product, 
                					'qty':prod_detail.used_time,
                					'unit_price':cb_unit_price ,
                					'price': cb_unit_price * prod_detail.used_time,
                					'id':combo_line.id,
                					'discount':cb_discount,
                				});
                				total_amount += cb_unit_price * prod_detail.used_time;
                				// console.log("qty:" + prod_detail.used_time);
                				// console.log("line:" + total_amount);

                			}
            			}
            		});
            	}
            });
            // console.log(total_amount);
            // console.log(products_info);
            var selected_line = order.get_selected_orderline();
            if(products_info.length > 0){
            	if(selected_line){
            		selected_line.set_combo_prod_info(products_info);
            		// Code Change for Print Combo in Kitchen Screen
            		var combo_order_line = selected_line;
            		order.remove_orderline(selected_line);
            		var combo_product = self.pos.db.get_product_by_id(Number(combo_order_line.product.id));
                    order.add_product(combo_product, {
                        quantity: combo_order_line.quantity,
                    });
                    var new_line = order.get_selected_orderline();
                    new_line.set_combo_prod_info(combo_order_line.combo_prod_info);
                    new_line.set_unit_price(total_amount);
            	}else{
            		alert("Selected line not found!");
            	}
            }else{
            	if(selected_line && !selected_line.get_combo_prod_info()){
            		order.remove_orderline(selected_line);
            	}
            }
            self.gui.close_popup();
        },
        click_cancel: function(){
        	var order = this.pos.get_order();
        	var selected_line = order.get_selected_orderline();
        	if(selected_line && !selected_line.get_combo_prod_info()){
        		order.remove_orderline(selected_line);
        	}
        	this.gui.close_popup();
        },
        renderElement: function(){
        	this._super();
        	this.$el.find('.combo_header2_body').scrollTop(this.scroll_position);
        },
    });
    gui.define_popup({name:'combo_product_popup', widget: POSComboProductPopup});

    screens.OrderWidget.include({
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);

            this.total_item = 0;
        },
        render_orderline: function(orderline){
            var self = this;
            var el_node = this._super(orderline);
            var el_combo_icon = el_node.querySelector('.combo-popup-icon');
            if(el_combo_icon){
                el_combo_icon.addEventListener('click',(function(){
                    var product = orderline.get_product();
                    if(product.is_combo && product.product_combo_ids.length > 0 && self.pos.config.enable_combo){
                        self.pos.gui.show_popup('combo_product_popup',{
                            'product':product,
                            'combo_product_info': orderline.get_combo_prod_info(),
                        });
                    }
                }.bind(this)));
            }
            if(self.pos.config.edit_combo){
                if(el_node){
                    el_node.addEventListener('click',(function(){
                        var product = orderline.get_product();
                        if(product.is_combo && product.product_combo_ids.length > 0 && self.pos.config.enable_combo){
                            self.pos.gui.show_popup('combo_product_popup',{
                                'product':product,
                                'combo_product_info': orderline.get_combo_prod_info(),
                            });
                        }
                    }.bind(this)));
                }
            }
            return el_node;
        },
        update_summary: function(){
            this._super();

            var order  = this.pos.get_order();
            if (!order.get_orderlines().length) {
                return;
            }
            // var orderlines = order.get_orderlines();
            //
            // var totalItem = 0;
            // for(var i = 0, len = orderlines.length; i < len; i++){
            //     var orderline = orderlines[i];
            //     var orderline_quant = orderline.get_quantity();
            //     totalItem += orderline_quant
            // }
            //
            // var totalStr = "Total item: "+totalItem;
            var totalItem = order ? "Total item: " + order.get_total_item() : 0;
            this.total_item = totalItem;

            var total     = order ? order.get_total_with_tax() : 0;
            this.el.querySelector('.order .polines .category .total').textContent = totalItem;
        },
    });

    screens.ReceiptScreenWidget.include({
        renderElement: function() {
            var self = this;
            this._super();

            this.$('.button.print_product').click(function(){
                if (!self._locked) {
                    self.print_p();
                }
            });
        },
        print_p_web: function() {
            // in ticket chi tiet tung sp
            this.$('.pos-receipt-container').hide();
            if ($.browser.safari) {
                document.execCommand('print', false, null);
            } else {
                try {
                    window.print();
                } catch(err) {
                    if (navigator.userAgent.toLowerCase().indexOf("android") > -1) {
                        this.gui.show_popup('error',{
                            'title':_t('Printing is not supported on some android browsers'),
                            'body': _t('Printing is not supported on some android browsers due to no default printing protocol is available. It is possible to print your tickets by making use of an IoT Box.'),
                        });
                    } else {
                        throw err;
                    }
                }
            }
            this.pos.get_order()._printed = true;
            this.$('.pos-receipt-container').show();
        },
        print_p_xml: function() {
            console.log('print_p_xml');
            var receipt = QWeb.render('XmlReceipt', this.get_receipt_render_env());

            this.pos.proxy.print_receipt(receipt);
            this.pos.get_order()._printed = true;
        },
        print_p: function() {
            var self = this;

            if (!this.pos.config.iface_print_via_proxy) { // browser (html) printing

                // The problem is that in chrome the print() is asynchronous and doesn't
                // execute until all rpc are finished. So it conflicts with the rpc used
                // to send the orders to the backend, and the user is able to go to the next
                // screen before the printing dialog is opened. The problem is that what's
                // printed is whatever is in the page when the dialog is opened and not when it's called,
                // and so you end up printing the product list instead of the receipt...
                //
                // Fixing this would need a re-architecturing
                // of the code to postpone sending of orders after printing.
                //
                // But since the print dialog also blocks the other asynchronous calls, the
                // button enabling in the setTimeout() is blocked until the printing dialog is
                // closed. But the timeout has to be big enough or else it doesn't work
                // 1 seconds is the same as the default timeout for sending orders and so the dialog
                // should have appeared before the timeout... so yeah that's not ultra reliable.

                this.lock_screen(true);

                setTimeout(function(){
                    self.lock_screen(false);
                }, 1000);

                this.print_p_web();
            } else {    // proxy (xml) printing
                this.print_p_xml();
                this.lock_screen(false);
            }
        },
        print_web: function() {
            this.$('.pos-product-container').hide();
            this._super();
            // if ($.browser.safari) {
            //     document.execCommand('print', false, null);
            // } else {
            //     try {
            //         window.print();
            //     } catch(err) {
            //         if (navigator.userAgent.toLowerCase().indexOf("android") > -1) {
            //             this.gui.show_popup('error',{
            //                 'title':_t('Printing is not supported on some android browsers'),
            //                 'body': _t('Printing is not supported on some android browsers due to no default printing protocol is available. It is possible to print your tickets by making use of an IoT Box.'),
            //             });
            //         } else {
            //             throw err;
            //         }
            //     }
            // }
            // this.pos.get_order()._printed = true;
            this.$('.pos-product-container').show();
        },
        render_receipt: function() {
            this.$('.pos-receipt-container').html(QWeb.render('PosTicket', this.get_receipt_render_env()));
            this.$('.pos-product-container').html(QWeb.render('PosProduct', this.get_receipt_render_env()));
        }
    });

});