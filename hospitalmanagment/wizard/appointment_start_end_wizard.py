# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date,datetime,timedelta


class appointment_start_end_wizard(models.TransientModel):
    _name = "appointment.start.end.wizard"

    appointment_start_end_physician_ids = fields.Many2many('medical.physician',string='Name Of Physician')
#     speciality_ids = fields.Many2many('medical.speciality',string='Speciality')
    start_date = fields.Date("Start Date")
    end_date = fields.Date('End Date')

    def show_record(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        
        result = mod_obj.get_object_reference('hospitalmanagment','action_medical_appointment')
        id = result and result[1] or False
        if id:
            current_action = act_obj.browse(id)
            result = current_action.read()[0]
            domain = []        
            if self.start_date:
                from_date = datetime.strptime(self.start_date, "%Y-%m-%d")
                from_date = from_date.strftime("%Y-%m-%d %H:%M:%S")
                domain.append(('appointment_date','>=',from_date))
                
            if self.end_date:
                to_date = datetime.strptime(self.end_date, "%Y-%m-%d")
                to_date = to_date+timedelta(days=1)
                to_date = to_date.strftime("%Y-%m-%d %H:%M:%S")
                domain.append(('appointment_end','<=',to_date))
            
            if self.appointment_start_end_physician_ids:
                domain.append(('doctor_id','in',map(int,self.appointment_start_end_physician_ids)))
#             if self.speciality_ids:
#                 domain.append(('speciality_id','in',map(int,self.speciality_ids)))

            result['domain'] = domain
            result['view_type'] = 'form'
            return result

