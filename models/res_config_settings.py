from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_grace_period = fields.Integer(
        related='company_id.attendance_grace_period',
        readonly=False,
        string="Default Grace Period (minutes)",
        help="Default grace period before marking attendance as late"
    )
    late_notification_template = fields.Many2one(
        'mail.template',
        string="Late Arrival Notification Template",
        domain=[('model', '=', 'hr.attendance')],
        config_parameter='myis_late_arrival.notification_template'
    )
    auto_create_late_records = fields.Boolean(
        string="Auto-create Late Arrival Records",
        config_parameter='myis_late_arrival.auto_create_records',
        default=True
    )

class ResCompany(models.Model):
    _inherit = 'res.company'

    attendance_grace_period = fields.Integer(
        string='Attendance Grace Period',
        default=15,
        help="Default grace period in minutes before marking as late"
    )# =====================================
# Custom Module: Late Arrival Management
# สำหรับ MYIS International School
# อ้างอิงจาก Odoo 18 official structure
# =====================================
