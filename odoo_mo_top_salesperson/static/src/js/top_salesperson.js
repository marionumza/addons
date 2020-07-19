odoo.define('odoo_mo_top_salesperson.top_salesperson', function (require) {
    'use strict';
    var core = require('web.core');
    var QWeb = core.qweb;
    var AbstractAction = require('web.AbstractAction');
    var top_salesperson_view = AbstractAction.extend({
        hasControlPanel: true,
        events: {
            'dblclick .categ': 'view_so',
        },


        init: function (parent, action) {
            $(".main_report").empty();
            this.report_name = action.report_name;
            this.lines = action.lines;
            return this._super.apply(this, arguments);

        },


        renderElement: function () {
            this._super();
            var self = this;
            var lines = [];
            if (this.lines) {
                for (var i in this.lines) {
                    lines.push(this.lines[i]);
                }
            }
            var $content = $(QWeb.render("report_top_salesperson", {
                heading: self.report_name,
                id: self.id,
                type: 'report',
                lines: lines,
                group: this.group
            }));
            self.$el.html($content);
            return;
        },
        view_so: function (e) {
            var user_id = $(e.target).data('id');
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: "sale.order",
                name: "Top Salesperson",
                domain: [['user_id','=',user_id],['state','=',"sale"]],
                views: [[false, 'list']],
            });

        }

    });


    core.action_registry.add("top_salesperson_view", top_salesperson_view);
    return top_salesperson_view;
});