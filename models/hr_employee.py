from odoo import models, fields, api, _
from datetime import date, timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Late arrival statistics
    late_arrival_count_today = fields.Integer(
        string='Late Today',
        compute='_compute_late_statistics'
    )
    late_arrival_count_week = fields.Integer(
        string='Late This Week',
        compute='_compute_late_statistics'
    )
    late_arrival_count_month = fields.Integer(
        string='Late This Month',
        compute='_compute_late_statistics'
    )
    total_late_minutes_month = fields.Integer(
        string='Total Late Minutes (Month)',
        compute='_compute_late_statistics'
    )
    attendance_score = fields.Float(
        string='Attendance Score',
        compute='_compute_attendance_score',
        help="Score based on punctuality (100 = perfect, 0 = very poor)"
    )

    # Configuration fields
    custom_grace_period = fields.Integer(
        string='Custom Grace Period (minutes)',
        help="Override company default grace period for this employee"
    )
    attendance_notification = fields.Boolean(
        string='Send Late Notifications',
        default=True,
        help="Send email notifications when employee is late"
    )

    @api.depends('attendance_ids', 'attendance_ids.is_late', 'attendance_ids.check_in')
    def _compute_late_statistics(self):
        """Compute late arrival statistics for different periods"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        for employee in self:
            # Get all late attendances
            late_attendances = employee.attendance_ids.filtered('is_late')

            # Today's late arrivals
            today_late = late_attendances.filtered(
                lambda x: x.check_in and x.check_in.date() == today
            )
            employee.late_arrival_count_today = len(today_late)

            # This week's late arrivals
            week_late = late_attendances.filtered(
                lambda x: x.check_in and x.check_in.date() >= week_start
            )
            employee.late_arrival_count_week = len(week_late)

            # This month's late arrivals
            month_late = late_attendances.filtered(
                lambda x: x.check_in and x.check_in.date() >= month_start
            )
            employee.late_arrival_count_month = len(month_late)
            employee.total_late_minutes_month = sum(month_late.mapped('late_minutes'))

    @api.depends('attendance_ids')
    def _compute_attendance_score(self):
        """Compute attendance score based on punctuality over last 30 days"""
        thirty_days_ago = date.today() - timedelta(days=30)

        for employee in self:
            recent_attendances = employee.attendance_ids.filtered(
                lambda x: x.check_in and x.check_in.date() >= thirty_days_ago
            )

            if not recent_attendances:
                employee.attendance_score = 100.0
                continue

            total_days = len(recent_attendances)
            late_days = len(recent_attendances.filtered('is_late'))

            # Calculate score (100 = perfect, deduct points for late days)
            if total_days > 0:
                punctuality_rate = (total_days - late_days) / total_days
                employee.attendance_score = punctuality_rate * 100
            else:
                employee.attendance_score = 100.0

    def action_view_late_arrivals(self):
        """Action to view employee's late arrivals"""
        self.ensure_one()
        return {
            'name': _('Late Arrivals - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form',
            'domain': [
                ('employee_id', '=', self.id),
                ('is_late', '=', True)
            ],
            'context': {'default_employee_id': self.id},
        }

    def get_effective_grace_period(self):
        """Get effective grace period (custom or company default)"""
        self.ensure_one()
        if self.custom_grace_period:
            return self.custom_grace_period
        return self.company_id.attendance_grace_period or 15
