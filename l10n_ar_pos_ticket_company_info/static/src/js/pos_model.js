odoo.define('pos_receipt_invoice_number', function (require) {
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var qweb = core.qweb;

    var _super_Order = models.Order.prototype;

    var _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            var partner_model = _.find(this.models, function (model) {
                return model.model === 'res.company';
            });

            partner_model.fields.push('report_header');
            partner_model.fields.push('report_company_name');

            _super_PosModel.initialize.apply(this, arguments);

        },

    });
    screens.ReceiptScreenWidget.include({
        print_xml: function () {
            var self = this;
            if (this.pos.config.receipt_invoice_number) {
                self.receipt_data = this.get_receipt_render_env();
                var order = this.pos.get_order();

                self.receipt_data['order']['report_header'] = self['pos']['company']['report_header'];
                self.receipt_data['order']['report_company_name'] = self['pos']['company']['report_company_name'];

                var receipt = qweb.render('XmlReceipt', self.receipt_data);
                self.pos.proxy.print_receipt(receipt);
            } else {
                this._super();
            }
        },
        render_receipt: function () {
            console.log('render_receipt');
            this._super();
            var self = this;
            var order = this.pos.get_order();

            if (!this.pos.config.iface_print_via_proxy && this.pos.config.receipt_invoice_number && order.is_to_invoice()) {
                var invoiced = new $.Deferred();
                self.pos.get_order()['report_header'] = self['pos']['company']['report_header'];
                self.pos.get_order()['report_company_name'] = self['pos']['company']['report_company_name'];
                console.log('get_order', self.pos.get_order())
                self.$('.pos-receipt-container').html(qweb.render('PosTicket', self.get_receipt_render_env()));

                return invoiced;
            } else {
                this._super();
            }
        }
    })
});
