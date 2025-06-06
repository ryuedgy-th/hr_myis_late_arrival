# ==== 1. __manifest__.py ====
{
    'name': 'MYIS Late Arrival Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Enhanced late arrival tracking for MYIS International School',
    'description': '''
        Enhanced Attendance Management for MYIS International School
        ============================================================

        Features:
        * Automatic late arrival detection with grace period
        * Daily/Weekly/Monthly late arrival reports
        * Department-wise late arrival analysis
        * Manager approval workflow for justified late arrivals
        * Integration with payroll deductions
        * Email notifications for HR managers
        * Customizable tolerance settings per employee type

        This module extends the standard hr_attendance module to provide
        comprehensive late arrival management suitable for educational institutions.
    ''',
    'author': 'MYIS IT Team',
    'website': 'https://magicyears.ac.th',
    'depends': [
        'hr',
        'hr_attendance',
        'resource',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/hr_attendance_views.xml',
        'views/late_arrival_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'views/menuitem.xml',
        'reports/late_arrival_report.xml',
        'wizard/late_arrival_wizard_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'myis_late_arrival/static/src/css/late_arrival.css',
            'myis_late_arrival/static/src/js/late_arrival_dashboard.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
