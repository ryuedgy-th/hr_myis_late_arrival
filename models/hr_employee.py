from odoo import models, fields, api, _
from datetime import date, timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Employee Type for different grace periods
    employee_type = fields.Selection([
        ('teacher', 'Teacher'),
        ('nanny', 'Teaching Assistant / Nanny'),
        ('operation', 'Operation Support'),
        ('admin', 'Administrative Staff'),
        ('management', 'Management')
    ], string='Employee Type', default='teacher',
       help="Employee type affects grace period for late arrival detection")

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

    # Working schedule display
    working_schedule_display = fields.Char(
        string='Working Schedule',
        compute='_compute_working_schedule_display'
    )

    @api.depends('resource_calendar_id', 'resource_calendar_id.attendance_ids')
    def _compute_working_schedule_display(self):
        """Display working schedule in a readable format"""
        for employee in self:
            if not employee.resource_calendar_id:
                employee.working_schedule_display = "No schedule defined"
                continue

            calendar = employee.resource_calendar_id
            schedule_lines = []

            # Group by day
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            for day_idx, day_name in enumerate(days):
                day_attendances = calendar.attendance_ids.filtered(
                    lambda x: int(x.dayofweek) == day_idx
                ).sorted('hour_from')

                if day_attendances:
                    time_ranges = []
                    for att in day_attendances:
                        start_time = f"{int(att.hour_from):02d}:{int((att.hour_from % 1) * 60):02d}"
                        end_time = f"{int(att.hour_to):02d}:{int((att.hour_to % 1) * 60):02d}"
                        time_ranges.append(f"{start_time}-{end_time}")

                    schedule_lines.append(f"{day_name}: {', '.join(time_ranges)}")

            employee.working_schedule_display = '; '.join(schedule_lines) if schedule_lines else "No working hours defined"

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
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.id),
                ('is_late', '=', True)
            ],
            'context': {'default_employee_id': self.id},
        }

    def get_grace_period_for_type(self):
        """Get grace period based on employee type"""
        grace_periods = {
            'teacher': 10,          # Teachers: 10 minutes grace
            'nanny': 10,            # Teaching assistants: 15 minutes
            'operation': 10,        # Operations: 20 minutes
            'admin': 10,            # Admin: 15 minutes
            'management': 10        # Management: 30 minutes
        }
        return grace_periods.get(self.employee_type, 15)

    def get_working_hours_for_date(self, target_date):
        """Get working hours for a specific date"""
        self.ensure_one()
        if not self.resource_calendar_id:
            return []

        weekday = target_date.weekday()
        working_hours = self.resource_calendar_id.attendance_ids.filtered(
            lambda x: int(x.dayofweek) == weekday
        ).sorted('hour_from')

        schedule_info = []
        for wh in working_hours:
            start_time = f"{int(wh.hour_from):02d}:{int((wh.hour_from % 1) * 60):02d}"
            end_time = f"{int(wh.hour_to):02d}:{int((wh.hour_to % 1) * 60):02d}"
            schedule_info.append({
                'start': start_time,
                'end': end_time,
                'hour_from': wh.hour_from,
                'hour_to': wh.hour_to
            })

        return schedule_info
