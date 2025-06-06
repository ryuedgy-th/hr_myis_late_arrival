from odoo import models, fields, api
from datetime import datetime, date, timedelta

class LateArrival(models.Model):
    _name = 'myis.late.arrival'
    _description = 'Late Arrival Record'
    _order = 'date desc, employee_id'
    _rec_name = 'display_name'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    department_id = fields.Related('employee_id.department_id', string='Department', store=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    check_in_time = fields.Datetime(string='Check-in Time', required=True)
    scheduled_time = fields.Datetime(string='Scheduled Time', required=True)
    late_minutes = fields.Integer(string='Late Minutes', required=True)
    reason = fields.Text(string='Reason')
    manager_approved = fields.Boolean(string='Manager Approved', default=False)
    payroll_deducted = fields.Boolean(string='Payroll Deducted', default=False)
    attendance_id = fields.Many2one('hr.attendance', string='Related Attendance')

    display_name = fields.Char(string='Display Name', compute='_compute_display_name')

    @api.depends('employee_id', 'date', 'late_minutes')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.employee_id.name} - {record.date} ({record.late_minutes} min)"

    @api.model
    def create_from_attendance(self, attendance):
        """Create late arrival record from attendance"""
        if not attendance.is_late:
            return False

        # Check if already exists
        existing = self.search([
            ('attendance_id', '=', attendance.id)
        ])
        if existing:
            return existing

        # Calculate scheduled time
        calendar = attendance.employee_id.resource_calendar_id
        check_in_weekday = attendance.check_in.weekday()
        working_hours = calendar.attendance_ids.filtered(
            lambda x: int(x.dayofweek) == check_in_weekday
        )

        if working_hours:
            earliest_start = min(working_hours.mapped('hour_from'))
            scheduled_time = attendance.check_in.replace(
                hour=int(earliest_start),
                minute=int((earliest_start % 1) * 60),
                second=0,
                microsecond=0
            )
        else:
            scheduled_time = attendance.check_in

        return self.create({
            'employee_id': attendance.employee_id.id,
            'date': attendance.check_in.date(),
            'check_in_time': attendance.check_in,
            'scheduled_time': scheduled_time,
            'late_minutes': attendance.late_minutes,
            'attendance_id': attendance.id,
        })
