odoo.define('pos_promotion.promotion', function (require) {
"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var utils = require('web.utils');

	var round_di = utils.round_decimals;
	var round_pr = utils.round_precision;

	models.PosModel.prototype.models.push(
	{
        model:  'pos.promotion',
        fields: [],
        domain: function(self){
        	var current_date = moment(new Date()).locale('en').format("YYYY-MM-DD");
            var weekday = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
        	var current_time = moment(new Date().getTime()).locale('en').format("H");
            var d = new Date();
            var current_day = weekday[d.getDay()]
        	return [['from_date','<=',current_date],['to_date','>=',current_date],['active','=',true],
        	        ['day_of_week_ids.name','in',[current_day]]];
        },
        loaded: function(self, pos_promotions){
            self.pos_promotions = pos_promotions;
        },
    },{
    	model:  'pos.conditions',
        fields: [],
        loaded: function(self,pos_conditions){
            self.pos_conditions = pos_conditions;
        },
    },{
    	model:  'get.discount',
        fields: [],
        loaded: function(self,pos_get_discount){
            self.pos_get_discount = pos_get_discount;
        },
    },{
    	model:  'quantity.discount',
        fields: [],
        loaded: function(self,pos_get_qty_discount){
            self.pos_get_qty_discount = pos_get_qty_discount;
        },
    },{
    	model:  'quantity.discount.amt',
        fields: [],
        loaded: function(self,pos_qty_discount_amt){
            self.pos_qty_discount_amt = pos_qty_discount_amt;
        },
    },{
    	model:  'discount.multi.products',
        fields: [],
        loaded: function(self,pos_discount_multi_prods){
            self.pos_discount_multi_prods = pos_discount_multi_prods;
        },
    },{
    	model:  'discount.multi.categories',
        fields: [],
        loaded: function(self,pos_discount_multi_categ){
            self.pos_discount_multi_categ = pos_discount_multi_categ;
        },
    },{
    	model:  'discount.above.price',
        fields: [],
        loaded: function(self,pos_discount_above_price){
            self.pos_discount_above_price = pos_discount_above_price;
        },
    });

	models.load_fields("product.product", ['product_brand_id']);

	var _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
    	add_product: function(product, options){
    		var self = this;
    		// _super_Order.add_product.call(this, product, options);
    		///newwwwww
            if(this._printed){
                this.destroy();
                return this.pos.get_order().add_product(product, options);
            }
            this.assert_editable();
            options = options || {};
            var attr = JSON.parse(JSON.stringify(product));
            attr.pos = this.pos;
            attr.order = this;
            var line = new models.Orderline({}, {pos: this.pos, order: this, product: product});

            if(options.quantity !== undefined){
                line.set_quantity(options.quantity);
            }

            if(options.price !== undefined){
                line.set_unit_price(options.price);
            }

            //To substract from the unit price the included taxes mapped by the fiscal position
            this.fix_tax_included_price(line);

            if(options.discount !== undefined){
                line.set_discount(options.discount);
            }

            if(options.extras !== undefined){
                for (var prop in options.extras) {
                    line[prop] = options.extras[prop];
                }
            }

            var found = false;
            var orderlines = [];
	        if (this.orderlines) {
	            orderlines = this.orderlines.models;
	        }
	        for (var i = 0; i < orderlines.length; i++) {
	            var _line = orderlines[i];
	            if (_line && _line.can_be_merged_with(line) &&
	                options.merge !== false) {
	                _line.merge(line);
	                this.select_orderline(_line);
	                found = true;
	                break;
	            }
	        }
	        if (!found) {
			    this.orderlines.add(line);
			    this.select_orderline(line);
	        }
            this.select_orderline(this.get_last_orderline());

            if(line.has_product_lot){
                this.display_lot_popup();
            }
            self.apply_promotion();
        },
        remove_promotion: function(){
	    	var self = this;
    		var order = self.pos.get_order();
			var lines = order.get_orderlines();
			var cashier = self.pos.get_cashier();
			lines.map(function(selected_line){
				if(selected_line){
					if(selected_line.get_child_line_id()){
						var child_line = order.get_orderline(selected_line.get_child_line_id());
						if(child_line){
							selected_line.set_child_line_id(false);
							selected_line.set_is_rule_applied(false);
							order.remove_orderline(child_line);
						}
					}else if(selected_line.get_buy_x_get_dis_y()){
                        _.each(lines, function(line){
                            if(line && line.get_buy_x_get_y_child_item()){
                                line.set_discount(0);
                                line.set_buy_x_get_y_child_item({});
                                line.set_is_rule_applied(false);
                                self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
                            }
                        });
					}else if(selected_line.get_quantity_discount()){
						selected_line.set_quantity_discount({});
						selected_line.set_discount(0);
						selected_line.set_is_rule_applied(false);
					}else if(selected_line.get_discount_amt()){
						selected_line.set_discount_amt_rule(false);
						selected_line.set_discount_amt(0);
						selected_line.set_unit_price(selected_line.product.list_price);
						selected_line.set_is_rule_applied(false);
					}else if(selected_line.get_multi_prods_line_id()){
						var multi_prod_id = selected_line.get_multi_prods_line_id() || false;
						if(multi_prod_id){
							_.each(lines, function(_line){
								if(_line && _line.get_multi_prods_line_id() == multi_prod_id){
									_line.set_discount(0);
									_line.set_is_rule_applied(false);
									_line.set_combinational_product_rule(false);
									self.pos.chrome.screens.products.order_widget.rerender_orderline(_line);
								}
							});
						}
					}
				}
			});
	    },
    	apply_promotion: function(){
    		var self = this;
    		self.remove_promotion();
			var order = self.pos.get_order();
			var lines = order.get_new_order_lines();
			var promotion_list = self.pos.pos_promotions;
			var condition_list = self.pos.pos_conditions;
			var discount_list = self.pos.pos_get_discount;
			var pos_get_qty_discount_list = self.pos.pos_get_qty_discount;
			var pos_qty_discount_amt = self.pos.pos_qty_discount_amt;
			var pos_discount_multi_prods = self.pos.pos_discount_multi_prods;
			var pos_discount_multi_categ = self.pos.pos_discount_multi_categ;
			var pos_discount_above_price = self.pos.pos_discount_above_price;
			var selected_line = self.pos.get_order().get_selected_orderline();
        	var current_time = Number(moment(new Date().getTime()).locale('en').format("H"));
			if(order && lines && lines[0]){
				_.each(lines, function(line){
					if(promotion_list && promotion_list[0]){
						_.each(promotion_list, function(promotion){
						    if((Number(promotion.from_time) <= current_time && Number(promotion.to_time) > current_time) || (!promotion.from_time && !promotion.to_time)){
							if(promotion && promotion.promotion_type == "buy_x_get_y"){
								if(promotion.pos_condition_ids && promotion.pos_condition_ids[0]){
									_.each(promotion.pos_condition_ids, function(pos_condition_line_id){
										var line_record = _.find(condition_list, function(obj) { return obj.id == pos_condition_line_id});
										if(line_record){
											if(line_record.product_x_id && line_record.product_x_id[0] == line.product.id){
												if(!line.get_is_rule_applied()){
													if(line_record.operator == 'is_eql_to'){
														if(line_record.quantity == line.quantity){
															if(line_record.product_y_id && line_record.product_y_id[0]){
																var product = self.pos.db.get_product_by_id(line_record.product_y_id[0]);
																var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
																new_line.set_quantity(line_record.quantity_y);
																new_line.set_unit_price(0);
																new_line.set_promotion({
																	'prom_prod_id':line_record.product_y_id[0],
																	'parent_product_id':line_record.product_x_id[0],
																	'rule_name':promotion.promotion_code,
																});
																new_line.set_is_rule_applied(true);
										                        order.add_orderline(new_line);
										                        line.set_child_line_id(new_line.id);
										                        line.set_is_rule_applied(true);
															}
														}
													}else if(line_record.operator == 'greater_than_or_eql'){
														if(line.quantity >= line_record.quantity){
															if(line_record.product_y_id && line_record.product_y_id[0]){
																var product = self.pos.db.get_product_by_id(line_record.product_y_id[0]);
																var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
																new_line.set_quantity(line_record.quantity_y);
																new_line.set_unit_price(0);
																new_line.set_promotion({
																	'prom_prod_id':line_record.product_y_id[0],
																	'parent_product_id':line_record.product_x_id[0],
																	'rule_name':promotion.promotion_code,
																});
																new_line.set_is_rule_applied(true);
										                        order.add_orderline(new_line);
										                        line.set_child_line_id(new_line.id);
										                        line.set_is_rule_applied(true);
															}
														}
													}
												}
											}
										}
									});
								}
							}else if(promotion && promotion.promotion_type == "buy_x_get_dis_y"){
								if(promotion.parent_product_ids && promotion.parent_product_ids[0] && (jQuery.inArray(line.product.id,promotion.parent_product_ids) != -1)){
									var disc_line_ids = [];
									_.each(promotion.pos_quntity_dis_ids, function(pos_quntity_dis_id){
										var disc_line_record = _.find(discount_list, function(obj) { return obj.id == pos_quntity_dis_id});
										if(disc_line_record){
											if(disc_line_record.product_id_dis && disc_line_record.product_id_dis[0]){
												disc_line_ids.push(disc_line_record);
											}
										}
									});
									line.set_buy_x_get_dis_y({
										'disc_line_ids':disc_line_ids,
										'promotion':promotion,
									});
								}
								if(line.get_buy_x_get_dis_y().disc_line_ids){
									_.each(line.get_buy_x_get_dis_y().disc_line_ids, function(disc_line){
										_.each(lines, function(orderline){
											if(disc_line.product_id_dis && disc_line.product_id_dis[0] == orderline.product.id){
												var count = 0;
												_.each(order.get_orderlines(), function(_line){
													if(_line.product.id == orderline.product.id){
														count += 1;
													}
												});
												if(count <= disc_line.qty){
													var cart_line_qty = orderline.get_quantity();
													if(cart_line_qty >= disc_line.qty){
														var prmot_disc_lines = [];
														var flag = true;
														order.get_orderlines().map(function(o_line){
															if(o_line.product.id == orderline.product.id){
																if(o_line.get_is_rule_applied()){
																	flag = false;
																}
															}
														});
														if(flag){
															var extra_prod_qty = cart_line_qty - disc_line.qty;
															if(extra_prod_qty != 0){
																orderline.set_quantity(disc_line.qty);
															}
															orderline.set_discount(disc_line.discount_dis_x);
															orderline.set_buy_x_get_y_child_item({
																'rule_name':line.get_buy_x_get_dis_y().promotion.promotion_code,
																'promotion_type':line.get_buy_x_get_dis_y().promotion.promotion_type,
															});
															orderline.set_is_rule_applied(true);
															self.pos.chrome.screens.products.order_widget.rerender_orderline(orderline);
															if(extra_prod_qty != 0){
																var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: orderline.product});
																new_line.set_quantity(extra_prod_qty);
										                        order.add_orderline(new_line);
															}
															return false;
														}
													}
												}
											}
										});
									});
								}
							}else if(promotion && promotion.promotion_type == "quantity_discount"){
								if(promotion.product_id_qty && promotion.product_id_qty[0] == line.product.id){
									var line_ids = [];
									_.each(promotion.pos_quntity_ids, function(pos_quntity_id){
										var line_record = _.find(pos_get_qty_discount_list, function(obj) { return obj.id == pos_quntity_id});
										if(line_record){
											if(line.get_quantity() == line_record.quantity_dis){
												if(line_record.discount_dis){
													line.set_discount(line_record.discount_dis);
													line.set_quantity_discount({
														'rule_name':promotion.promotion_code,
													});
													line.set_is_rule_applied(true);
													self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
													return false;
												}
											}
										}
									});
								}
							}else if(promotion && promotion.promotion_type == "quantity_price"){
								if(promotion.product_id_amt && promotion.product_id_amt[0] == line.product.id){
									var line_ids = [];
									_.each(promotion.pos_quntity_amt_ids, function(pos_quntity_amt_id){
										var line_record = _.find(pos_qty_discount_amt, function(obj) { return obj.id == pos_quntity_amt_id});
										if(line_record){
											if(line.get_quantity() >= line_record.quantity_amt){
												if(line_record.discount_price){
													line.set_discount_amt(line_record.discount_price);
													line.set_discount_amt_rule(promotion.promotion_code);
//													line.set_unit_price(((line.get_unit_price()*line.get_quantity()) - line_record.discount_price)/line.get_quantity());
													line.set_unit_price(line_record.discount_price);
													line.set_is_rule_applied(true);
													self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
													return false;
												}
											}
										}
									});
								}
							}else if(promotion && promotion.promotion_type == "discount_on_multi_product"){
								if(promotion.multi_products_discount_ids && promotion.multi_products_discount_ids[0]){
									_.each(promotion.multi_products_discount_ids, function(disc_line_id){
										var disc_line_record = _.find(pos_discount_multi_prods, function(obj) { return obj.id == disc_line_id});
										if(disc_line_record){
											self.check_products_for_disc(disc_line_record, promotion);
										}
									})
								}
							}else if(promotion && promotion.promotion_type == "discount_on_multi_categ"){
								if(promotion.multi_categ_discount_ids && promotion.multi_categ_discount_ids[0]){
									_.each(promotion.multi_categ_discount_ids, function(disc_line_id){
										var disc_line_record = _.find(pos_discount_multi_categ, function(obj) { return obj.id == disc_line_id});
										if(disc_line_record){
											self.check_categ_for_disc(disc_line_record, promotion);
										}
									})
								}
							}else if(promotion && promotion.promotion_type == "discount_on_above_price"){
								if(promotion && promotion.discount_price_ids && promotion.discount_price_ids[0]){
									_.each(promotion.discount_price_ids, function(line_id){
										var line_record = _.find(pos_discount_above_price, function(obj) { return obj.id == line_id});
										if(line_record && line_record.product_brand_ids && line_record.product_brand_ids[0] 
											&& line_record.product_categ_ids && line_record.product_categ_ids[0]){
											if(line.product.product_brand_id && line.product.product_brand_id[0]){
												if($.inArray(line.product.product_brand_id[0], line_record.product_brand_ids) != -1){
													if(line.product.pos_categ_id){
														var product_category = self.pos.db.get_category_by_id(line.product.pos_categ_id[0])
														if(product_category){
															if($.inArray(product_category.id, line_record.product_categ_ids) != -1){
																if(line_record.discount_type == "fix_price"){
																	if(line.product.lst_price >= line_record.price && line.quantity > 0){
																		if(line_record.price){
																			line.set_discount_amt(line_record.price);
																			line.set_discount_amt_rule(line_record.pos_promotion_id[1]);
																			line.set_unit_price(((line.get_unit_price()*line.get_quantity()) - line_record.price)/line.get_quantity());
																			line.set_is_rule_applied(true);
																			self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
																		}
																	}
																} else if(line_record.discount_type == "percentage"){
																	if(line_record.discount){
																		if(line.product.lst_price >= line_record.price && line.quantity > 0){
																			line.set_discount(line_record.discount);
																			line.set_is_rule_applied(true);
																		}	
																	}
																} else if(line_record.discount_type == "free_product"){
																	if(line_record.free_product && line_record.free_product[0]){
																		var product = self.pos.db.get_product_by_id(line_record.free_product[0]);
																		var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
																		new_line.set_quantity(1);
																		new_line.set_unit_price(0);
																		new_line.set_promotion({
																			'prom_prod_id':line_record.free_product[0],
																			'parent_product_id':line.id,
																			'rule_name':line_record.pos_promotion_id[1],
																		});
																		new_line.set_is_rule_applied(true);
												                        order.add_orderline(new_line);
												                        line.set_child_line_id(new_line.id);
												                        line.set_is_rule_applied(true);
																	}
																}
															}
														}
													}
												}
											}
										}else if(line_record.product_brand_ids.length <= 0 && line_record.product_categ_ids.length > 0){
											if(line.product.pos_categ_id){
												var product_category = self.pos.db.get_category_by_id(line.product.pos_categ_id[0]);
												if(product_category){
													if($.inArray(product_category.id, line_record.product_categ_ids) != -1){
														if(line_record.discount_type == "fix_price"){
															if(line.product.lst_price >= line_record.price && line.quantity > 0){
																if(line_record.price){
																	line.set_discount_amt(line_record.price);
																	line.set_discount_amt_rule(line_record.pos_promotion_id[1]);
																	line.set_unit_price(((line.get_unit_price()*line.get_quantity()) - line_record.price)/line.get_quantity());
																	line.set_is_rule_applied(true);
																	self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
																}
															}
														} else if(line_record.discount_type == "percentage"){
															if(line_record.discount){
																if(line.product.lst_price >= line_record.price && line.quantity > 0){
																	line.set_discount(line_record.discount);
																	line.set_is_rule_applied(true);
																}	
															}
														} else if(line_record.discount_type == "free_product"){
															if(line_record.free_product && line_record.free_product[0]){
																var product = self.pos.db.get_product_by_id(line_record.free_product[0]);
																var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
																new_line.set_quantity(1);
																new_line.set_unit_price(0);
																new_line.set_promotion({
																	'prom_prod_id':line_record.free_product[0],
																	'parent_product_id':line.id,
																	'rule_name':line_record.pos_promotion_id[1],
																});
																new_line.set_is_rule_applied(true);
										                        order.add_orderline(new_line);
										                        line.set_child_line_id(new_line.id);
										                        line.set_is_rule_applied(true);
															}
														}
													}
												}
											}
										}else if(line_record.product_categ_ids.length == 0 && line_record.product_brand_ids.length > 0){
											if(line.product.product_brand_id && line.product.product_brand_id[0]){
												if($.inArray(line.product.product_brand_id[0], line_record.product_brand_ids) != -1){
													if(line_record.discount_type == "fix_price"){
														if(line.product.lst_price >= line_record.price && line.quantity > 0){
															if(line_record.price){
																line.set_discount_amt(line_record.price);
																line.set_discount_amt_rule(line_record.pos_promotion_id[1]);
																line.set_unit_price(((line.get_unit_price()*line.get_quantity()) - line_record.price)/line.get_quantity());
																line.set_is_rule_applied(true);
																self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
															}
														}
													} else if(line_record.discount_type == "percentage"){
														if(line_record.discount){
															if(line.product.lst_price >= line_record.price && line.quantity > 0){
																line.set_discount(line_record.discount);
																line.set_is_rule_applied(true);
															}	
														}
													} else if(line_record.discount_type == "free_product"){
														if(line_record.free_product && line_record.free_product[0]){
															var product = self.pos.db.get_product_by_id(line_record.free_product[0]);
															var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
															new_line.set_quantity(1);
															new_line.set_unit_price(0);
															new_line.set_promotion({
																'prom_prod_id':line_record.free_product[0],
																'parent_product_id':line.id,
																'rule_name':line_record.pos_promotion_id[1],
															});
															new_line.set_is_rule_applied(true);
									                        order.add_orderline(new_line);
									                        line.set_child_line_id(new_line.id);
									                        line.set_is_rule_applied(true);
														}
													}
												}
											}
										}
									});
								}
							}
							}
						});
					}
				});
			}
    	},
    	check_products_for_disc: function(disc_line, promotion){
    		var self = this;
    		var product_ids = disc_line.product_ids;
    		var discount = disc_line.products_discount;
    		var order = self.pos.get_order();
    		var lines = self.get_new_order_lines();
    		var product_cmp_list = [];
    		var orderline_ids = [];
    		var products_qty = [];
    		if(product_ids && product_ids[0] && discount){
    			_.each(lines, function(line){
        			if(jQuery.inArray(line.product.id,product_ids) != -1){
        				product_cmp_list.push(line.product.id);
        				orderline_ids.push(line.id);
        				products_qty.push(line.get_quantity());
        			}
        		});
    			if(!_.contains(products_qty, 0)){
    				if(_.isEqual(_.sortBy(product_ids), _.sortBy(product_cmp_list))){
            			_.each(orderline_ids, function(orderline_id){
            				var orderline = order.get_orderline(orderline_id);
            				if(orderline && orderline.get_quantity() > 0){
            					orderline.set_discount(discount);
            					orderline.set_multi_prods_line_id(disc_line.id);
            					orderline.set_is_rule_applied(true);
            					orderline.set_combinational_product_rule(promotion.promotion_code);
            					self.pos.chrome.screens.products.order_widget.rerender_orderline(orderline);
            				}
            			});
            		}
    			}
    		}
    	},
    	check_categ_for_disc: function(disc_line, promotion){
    		var self = this;
    		var order = self.pos.get_order();
    		var lines = self.get_new_order_lines();
    		var categ_ids = disc_line.categ_ids;
    		var discount = disc_line.categ_discount;
    		if(categ_ids && categ_ids[0] && discount){
    			_.each(categ_ids, function(categ_id){
    				var products = self.pos.db.get_product_by_category(categ_id);
    				if(products && products[0]){
    					_.each(lines, function(line){
    						if($.inArray(line.product, products) != -1){
    							line.set_discount(discount);
    							line.set_is_rule_applied(true);
    							line.set_multi_prod_categ_rule(promotion.promotion_code);
            					self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
    						}
    					});
    				}
    			});
    		}
    	},
    	get_new_order_lines: function(){
    		var self = this;
    		var order = self.pos.get_order();
			var lines = order.get_orderlines();
			var new_lines = [];
			_.each(lines, function(line){
				if(line && line.get_quantity() > 0 && !line.get_is_rule_applied()){
					new_lines.push(line);
				}
			});
			return new_lines;
    	},
    	calculate_discount_amt: function(){
    		var self = this;
    		var order = self.pos.get_order();
    		var total = order ? order.get_total_with_tax() : 0;
    		var promotion_list = self.pos.pos_promotions;
    		var discount = 0;
    		var current_time = Number(moment(new Date().getTime()).locale('en').format("H"));
    		if(promotion_list && promotion_list[0]){
    			_.each(promotion_list, function(promotion){
    			    if((Number(promotion.from_time) <= current_time && Number(promotion.to_time) > current_time) || (!promotion.from_time && !promotion.to_time)){
                        if(promotion.promotion_type == 'dicount_total'){
                            if(promotion.operator == 'greater_than_or_eql'){
                                if(promotion.total_amount && total >= promotion.total_amount){
                                    if(promotion.discount_product && promotion.discount_product[0]){
                                    	if(promotion.discount_type == 'Percent'){
                                    		discount = (total * promotion.total_discount)/100;
										}else{
                                    		discount = promotion.total_discount;
										}

                                        // console.log(discount);
                                        order.set_discount_product_id(promotion.discount_product[0]);
                                       // order.set_discount_history(true);
                                    }
                                }
                            }else if(promotion.operator == 'is_eql_to'){
                                if(promotion.total_amount && total == promotion.total_amount){
                                    if(promotion.discount_product && promotion.discount_product[0]){
                                        if(promotion.discount_type == 'Percent'){
                                    		discount = (total * promotion.total_discount)/100;
										}else{
                                    		discount = promotion.total_discount;
										}
                                        order.set_discount_product_id(promotion.discount_product[0]);
                                       // order.set_discount_history(true);
                                    }
                                }
                            }
                        }
                    }
    			});
    		}
    		return Number(discount);
    	},
    	get_total_without_tax: function() {
    		var result = _super_Order.get_total_without_tax.call(this);
    		return result - this.get_order_total_discount();
    	},
        set_order_total_discount: function(order_total_discount){
        	this.order_total_discount = order_total_discount;
        },
        get_order_total_discount: function(){
        	return this.order_total_discount;
        },
        set_discount_price: function(discount_price){
        	this.discount_price = discount_price;
        },
        get_discount_price: function(){
        	return this.discount_price;
        },
        set_discount_product_id: function(discount_product_id){
        	this.discount_product_id = discount_product_id;
        },
        get_discount_product_id: function(){
        	return this.discount_product_id;
        },
        set_discount_history: function(disc){
        	this.disc_history = disc;
        },
        get_discount_history: function(){
        	return this.disc_history;
        },
        get_change: function(paymentline) {
            if (!paymentline) {
                var change = this.get_total_paid() - this.get_total_with_tax() - this.get_order_total_discount();
            } else {
                var change = -this.get_total_with_tax(); 
                var lines  = this.paymentlines.models;
                for (var i = 0; i < lines.length; i++) {
                    change += lines[i].get_amount();
                    if (lines[i] === paymentline) {
                        break;
                    }
                }
            }
            return round_pr(Math.max(0,change), this.pos.currency.rounding);
        },
    });

    screens.OrderWidget.include({
    	set_value: function(val) {
    		var self = this;
    		var order = self.pos.get_order();
			var lines = order.get_orderlines();
			var selected_line = order.get_selected_orderline() || false;
			if(selected_line){
				if(selected_line.get_child_line_id()){
					self._super(val);
					var child_line = order.get_orderline(selected_line.get_child_line_id());
					if(child_line){
						selected_line.set_child_line_id(false);
						selected_line.set_is_rule_applied(false);
						order.remove_orderline(child_line);
					}
				}else if(selected_line.get_buy_x_get_dis_y()){
					self._super(val);
					if(selected_line.get_quantity() < 1){
						_.each(lines, function(line){
							if(line && line.get_buy_x_get_y_child_item()){
//								order.remove_orderline(line);
								line.set_discount(0);
								line.set_buy_x_get_y_child_item({});
								line.set_is_rule_applied(false);
								self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
							}
						});
					}
				}else if(selected_line.get_quantity_discount()){
					selected_line.set_quantity_discount({});
					selected_line.set_discount(0);
					selected_line.set_is_rule_applied(false);
					self._super(val);
				}else if(selected_line.get_discount_amt()){
					selected_line.set_discount_amt_rule(false);
					selected_line.set_discount_amt(0);
					selected_line.set_unit_price(selected_line.product.price);
					selected_line.set_is_rule_applied(false);
					self._super(val);
				}else if(selected_line.get_multi_prods_line_id()){
					var multi_prod_id = selected_line.get_multi_prods_line_id() || false;
					if(multi_prod_id){
						_.each(lines, function(_line){
							if(_line && _line.get_multi_prods_line_id() == multi_prod_id){
								_line.set_discount(0);
								_line.set_is_rule_applied(false);
								_line.set_combinational_product_rule(false);
								self.pos.chrome.screens.products.order_widget.rerender_orderline(_line);
							}
						});
					}
					self._super(val);
				}else if(selected_line.get_multi_prod_categ_rule()){
					selected_line.set_discount(0);
					selected_line.set_is_rule_applied(false);
					selected_line.set_multi_prod_categ_rule(false);
					self._super(val);
				}
				else{
					if(!selected_line.get_promotion()){
						self._super(val);
					}
				}
			}
    		order.apply_promotion();
    	},
    	update_summary: function(){
    		var self = this;
    		var order = self.pos.get_order();
            if(!order){
                return;
            }
            var total = order ? order.get_total_with_tax() : 0;
            var discount = 0;
            order.set_discount_product_id(false);
            order.set_order_total_discount(discount);
            discount = order && !order.get_discount_history() ? order.calculate_discount_amt() : 0;
            order.set_order_total_discount(Number(discount));

            // console.log('discount');
            // console.log(discount);
            if(self.el.querySelector('.discount .value')){
                self.el.querySelector('.discount .value').textContent = this.format_currency(discount);
            }
            self._super();
    	},
    });

    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr,options){
            this.promotion = {};
            this.child_line_id = false;
            this.product_ids = false;
            this.buy_x_get_y_child_item = false;
            this.discount_line_id = false;
            this.disvalidate_ordercount_rule_name = false;
            this.quantity_discount = false;
            this.discount_amt_rule = false;
            this.discount_amt = false;
            this.multi_prods_line_id = false;
            this.is_rule_applied = false;
            this.combinational_product_rule = false;
            this.multi_prod_categ_rule = false;
            _super_orderline.initialize.call(this, attr, options);
        },
        can_be_merged_with: function(orderline) {
	        var result = _super_orderline.can_be_merged_with.call(this, orderline);
	        if (!result) {
	            if (!this.manual_price) {
	            	if(this.get_promotion() && this.get_promotion().parent_product_id){
	            		return false;
	            	}else if(this.get_is_rule_applied()){
	            		return false;
	            	}
	            	//ẩn đi vì cần check bên app combo
	            	// else{
	            	// 	return (this.get_product().id === orderline.get_product().id);
	            	// }
	            } else {
	                return false;
	            }
	        }
	        return result;
	    },
        set_promotion: function(promotion) {
            this.set('promotion', promotion);
        },
        get_promotion: function() {
            return this.get('promotion');
        },
        set_child_line_id: function(child_line_id){
        	this.child_line_id = child_line_id;
        },
        get_child_line_id: function(){
        	return this.child_line_id;
        },
        set_buy_x_get_dis_y: function(product_ids){
        	this.product_ids = product_ids;
        },
        get_buy_x_get_dis_y: function(){
        	return this.product_ids;
        },
        set_buy_x_get_y_child_item: function(buy_x_get_y_child_item){
        	this.buy_x_get_y_child_item = buy_x_get_y_child_item;
        },
        get_buy_x_get_y_child_item: function(buy_x_get_y_child_item){
        	return this.buy_x_get_y_child_item;
        },
        set_discount_line_id: function(discount_line_id){
        	this.discount_line_id = discount_line_id;
        },
        get_discount_line_id: function(discount_line_id){
        	return this.discount_line_id;
        },
        set_quantity_discount: function(quantity_discount){
        	this.quantity_discount = quantity_discount;
        },
        get_quantity_discount: function(){
        	return this.quantity_discount;
        },
        set_discount_amt_rule: function(discount_amt_rule){
        	this.discount_amt_rule = discount_amt_rule;
        },
        get_discount_amt_rule: function(){
        	return this.discount_amt_rule;
        },
        set_discount_amt: function(discount_amt){
        	this.discount_amt = discount_amt;
        },
        get_discount_amt: function(){
        	return this.discount_amt;
        },
        get_discount_amt_str: function(){
        	return this.pos.chrome.format_currency(this.discount_amt);
        },
        set_multi_prods_line_id: function(multi_prods_line_id){
        	this.multi_prods_line_id = multi_prods_line_id;
        },
        get_multi_prods_line_id: function(){
        	return this.multi_prods_line_id;
        },
        set_is_rule_applied: function(is_rule_applied){
        	this.is_rule_applied = is_rule_applied;
        },
        get_is_rule_applied: function(){
        	return this.is_rule_applied;
        },
        set_combinational_product_rule: function(combinational_product_rule){
        	this.combinational_product_rule = combinational_product_rule;
        },
        get_combinational_product_rule: function(){
        	return this.combinational_product_rule;
        },
        set_multi_prod_categ_rule: function(multi_prod_categ_rule){
        	this.multi_prod_categ_rule = multi_prod_categ_rule;
        },
        get_multi_prod_categ_rule: function(){
        	return this.multi_prod_categ_rule;
        },
    });

    screens.PaymentScreenWidget.include({
    	finalize_validation: function() {
    		var self = this;
            var order = this.pos.get_order();
    	    order.set_discount_history(true);
            if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {
                this.pos.proxy.open_cashbox();
            }

            order.initialize_validation_date();

            if(order.get_discount_product_id() && order.get_order_total_discount() > 0){
            	order.set_discount_price(order.get_order_total_discount());
            	var product = self.pos.db.get_product_by_id(order.get_discount_product_id());
				var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
				new_line.set_quantity(-1);
				new_line.set_unit_price(order.get_order_total_discount());
                order.add_orderline(new_line);
            }

            if (order.is_to_invoice()) {
                var invoiced = this.pos.push_and_invoice_order(order);
                this.invoicing = true;

                invoiced.fail(function(error){
                    self.invoicing = false;
                    if (error.message === 'Missing Customer') {
                        self.gui.show_popup('confirm',{
                            'title': _t('Please select the Customer'),
                            'body': _t('You need to select the customer before you can invoice an order.'),
                            confirm: function(){
                                self.gui.show_screen('clientlist');
                            },
                        });
                    } else if (error.code < 0) {        // XmlHttpRequest Errors
                        self.gui.show_popup('error',{
                            'title': _t('The order could not be sent'),
                            'body': _t('Check your internet connection and try again.'),
                        });
                    } else if (error.code === 200) {    // OpenERP Server Errors
                        self.gui.show_popup('error-traceback',{
                            'title': error.data.message || _t("Server Error"),
                            'body': error.data.debug || _t('The server encountered an error while receiving your order.'),
                        });
                    } else {                            // ???
                        self.gui.show_popup('error',{
                            'title': _t("Unknown Error"),
                            'body':  _t("The order could not be sent to the server due to an unknown error"),
                        });
                    }
                });

                invoiced.done(function(){
                    self.invoicing = false;
                    self.gui.show_screen('receipt');
                });
            } else {
                this.pos.push_order(order);
                this.gui.show_screen('receipt');
            }
    	},
    });

});