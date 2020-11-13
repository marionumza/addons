# -*- coding: utf-8 -*-

{
    'name': 'Turno Online',
    'version': '13.0.1.2',
    'author': 'pronexo.com',
    'price': 0.0,
    'currency': 'EUR',
    'maintainer': 'pronexo.com',
    'support': 'soporte@pronexo.com',
    'license': 'OPL-1',
    'website': 'https://www.pronexo.com',
    'category':  'Website',
    'summary': 'Let visitors book an appointment over the website',
    'description':
        """Visitors can book appointments over the website. A calendar pops up, the days marked green are available for selection.
        After selecting a date the visitor needs to choose a timeslot and a appointment option. In the backend you define per
        user his available timeslots. Only timeslots are selectable by the visitor when no other "calendar.event" is present for that period of time.
        Appointment options you define globally in the backend and have a duration. This way a "calendar.event" is created with the correct start and stop.
        
        website appointment
        online appointment
        portal appointment
        appointment
        website meeting
        online meeting
        portal meeting
        meeting
         
        """,
    'depends': [
        'calendar',
        'website',
        'portal'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/turno_template.xml',
        'views/turno_portal_template.xml',
        'views/menus.xml',
        'views/turno_schedule_view.xml',
        'views/turno_option_view.xml',
    ],
    'images': [
        'static/description/turno_online_home.png',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}

