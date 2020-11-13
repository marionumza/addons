odoo.define('turno_online.main', function (require) {
    'use strict';

    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    var _t = core._t;

    publicWidget.registry.OnlineTurno = publicWidget.Widget.extend({
        selector: '#turno_online',
        init: function () {
            this._super.apply(this, arguments);

            this.days_with_free_schedules = {};
            this.focus_year = 0;
            this.focus_month = 0;
        },
        start: function () {
            var self = this;

            $('.datepicker').datepicker({
                dateFormat: 'dd/mm/yy',
                startDate: '-3d',
                beforeShowDay: function(date) {
                    var d = self._format_date(date);
                    var key = date.getFullYear().toString() + ','+ (date.getMonth() + 1).toString();
                    if (self.days_with_free_schedules[key] && self.days_with_free_schedules[key][d]) {
                        return [true, 'color_green', ''];
                    } else {
                        return [false, '', ''];
                    }
                },
                onChangeMonthYear: function(year, month, datepicker) {
                    self._update_days_with_free_schedules(year, month);
                },
            });

             $.datepicker.regional['es'] = {
                 closeText: 'Cerrar',
                 prevText: '< Ant',
                 nextText: 'Sig >',
                 currentText: 'Hoy',
                 monthNames: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
                 monthNamesShort: ['Ene','Feb','Mar','Abr', 'May','Jun','Jul','Ago','Sep', 'Oct','Nov','Dic'],
                 dayNames: ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
                 dayNamesShort: ['Dom','Lun','Mar','Mié','Juv','Vie','Sáb'],
                 dayNamesMin: ['Do','Lu','Ma','Mi','Ju','Vi','Sá'],
                 weekHeader: 'Sm',
                 dateFormat: 'yy-mm-dd',
                 firstDay: 1,
                 isRTL: false,
                 showMonthAfterYear: false,
                 yearSuffix: ''
                 };
                 $.datepicker.setDefaults($.datepicker.regional['es']);




            

            $("#turno_option_id").on('change', function() {
                self.days_with_free_schedules = {};
                self._update_timeschedule();
            });

            $("#appointee_id").on('change', function() {
                self.days_with_free_schedules = {};
                self._update_timeschedule();
            });

            $("#turno_date").on('change', function() {
                self._update_timeschedule();
            });

            self._update_timeschedule();
        },

        _format_date: function (date) {
            var self = this;

            var d = new Date(date),
                month = '' + (d.getMonth() + 1),
                day = '' + d.getDate(),
                year = d.getFullYear();

            if (month.length < 2)
                month = '0' + month;
            if (day.length < 2)
                day = '0' + day;

            return [year, month, day].join('-');
        },

        _update_timeschedule: function () {
            var self = this;
            this._rpc({
                route: '/turno-online/timeschedules',
                params: {
                    'turno_option': $("#turno_option_id").val(),
                    'turno_with': $("#appointee_id").val(),
                    'turno_date': $("#turno_date").val(),
                    'form_criteria': $("#form_criteria").val(),
                },
            }).then(function(result) {
                self.focus_year = result.focus_year;
                self.focus_month = result.focus_month;
                self.days_with_free_schedules[self._get_yearmonth_key.bind(self)()] = result.days_with_free_schedules;
                var options = [];
                var timeschedules = result.timeschedules;
                options.push('<option value="">-:--</option>');
                for (var i = 0; i < timeschedules.length; i++) {
                    options.push('<option value="', timeschedules[i].id, '">', timeschedules[i].timeschedule, '</option>')
                }
                $("#timeschedule_id").html(options.join(''));
            });
        },

        _update_days_with_free_schedules: function (year, month) {
            var self = this;

            this._rpc({
                route: '/turno-online/month-bookable',
                params: {
                    'turno_option': $("#turno_option_id").val(),
                    'turno_with': $("#appointee_id").val(),
                    'turno_year': year,
                    'turno_month': month,
                    'form_criteria': $("#form_criteria").val(),
                },
            }).then(function(result) {
                self.focus_year = result.focus_year;
                self.focus_month = result.focus_month;
                self.days_with_free_schedules[self._get_yearmonth_key.bind(self)()] = result.days_with_free_schedules;
                $(".datepicker" ).datepicker("refresh");
            });
        },

        _get_yearmonth_key: function() {
            var key = this.focus_year.toString() + ',' + this.focus_month.toString();
            return key
        },

    }),

    publicWidget.registry.OnlineTurnoPortal = publicWidget.Widget.extend({
        selector: '#online_turno_interaction',
        start: function () {
            var self = this;
            var button_cancel = $('#cancel_turno_button');
            var button_confirm = $('#confirm_turno_button');

            button_cancel.click(function() {
                var dialog = $('#cancel_turno_dialog').modal('show');
            });

            button_confirm.click(function() {
                var dialog = $('#confirm_turno_dialog').modal('show');
            });
        }
    })
});
