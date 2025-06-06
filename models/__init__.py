from . import hr_attendance
from . import late_arrival
from . import hr_employee

# ==== 3. models/hr_attendance.py ====
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import pytz

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # New fields for late arrival tracking
    is_late = fields.Boolean(
        string='Late Arrival',
        compute='_compute_late_arrival_info',
        store=True,
        help="Indicates if this check-in was after the allowed grace period"
    )
    late_minutes = fields.Integer(
        string='Minutes Late',
        compute='_compute_late_arrival_info',
        store=True,
        help="Number of minutes after grace period"
    )
    expected_check_in = fields.Datetime(
        string='Expected Check-in',
        compute='_compute_late_arrival_info',
        store=True,
        help="When employee was supposed to check in"
    )
    grace_period_end = fields.Datetime(
        string='Grace Period End',
        compute='_compute_late_arrival_info',
        store=True,
        help="Latest time to check in without being late"
    )
    late_reason = fields.Text(
        string='Reason for Late Arrival',
        help="Employee can provide justification for being late"
    )
    manager_approved = fields.Boolean(
        string='Late Arrival Approved',
        default=False,
        help="Manager has approved this late arrival"
    )
    late_category = fields.Selection([
        ('minor', 'Minor (1-15 min)'),
        ('moderate', 'Moderate (16-30 min)'),
        ('major', 'Major (31-60 min)'),
        ('severe', 'Severe (>60 min)'),
    ], string='Late Category', compute='_compute_late_category', store=True)

    def _get_company_grace_period(self):
        """Get grace period from company settings, default 15 minutes"""
        return self.env.company.attendance_grace_period or 15

    def _get_employee_timezone(self):
        """Get employee timezone or company timezone"""
        tz_name = (self.employee_id.tz or
                  self.employee_id.company_id.partner_id.tz or
                  'UTC')
        return pytz.timezone(tz_name)

    @api.depends('check_in', 'employee_id', 'employee_id.resource_calendar_id')
    def _compute_late_arrival_info(self):
        """Compute late arrival information based on working calendar and grace period"""
        for attendance in self:
            # Reset values
            attendance.is_late = False
            attendance.late_minutes = 0
            attendance.expected_check_in = False
            attendance.grace_period_end = False

            if not attendance.check_in or not attendance.employee_id:
                continue

            employee = attendance.employee_id
            calendar = employee.resource_calendar_id

            if not calendar:
                continue

            # Convert check-in to employee timezone for calculation
            tz = attendance._get_employee_timezone()
            check_in_local = pytz.utc.localize(attendance.check_in).astimezone(tz)
            check_in_date = check_in_local.date()
            check_in_weekday = check_in_local.weekday()

            # Find working hours for this weekday
            working_hours = calendar.attendance_ids.filtered(
                lambda x: int(x.dayofweek) == check_in_weekday
            )

            if not working_hours:
                continue  # No working hours defined for this day

            # Get the earliest start time for the day
            earliest_start_hour = min(working_hours.mapped('hour_from'))

            # Create expected check-in datetime in local timezone
            expected_local = tz.localize(datetime.combine(
                check_in_date,
                datetime.min.time().replace(
                    hour=int(earliest_start_hour),
                    minute=int((earliest_start_hour % 1) * 60)
                )
            ))

            # Convert back to UTC for storage
            attendance.expected_check_in = expected_local.astimezone(pytz.utc).replace(tzinfo=None)

            # Calculate grace period end
            grace_period = attendance._get_company_grace_period()
            grace_end_local = expected_local + timedelta(minutes=grace_period)
            attendance.grace_period_end = grace_end_local.astimezone(pytz.utc).replace(tzinfo=None)

            # Check if late
            if attendance.check_in > attendance.grace_period_end:
                attendance.is_late = True
                late_delta = attendance.check_in - attendance.grace_period_end
                attendance.late_minutes = int(late_delta.total_seconds() / 60)

    @api.depends('late_minutes')
    def _compute_late_category(self):
        """Categorize lateness based on minutes"""
        for attendance in self:
            if attendance.late_minutes <= 0:
                attendance.late_category = False
            elif attendance.late_minutes <= 15:
                attendance.late_category = 'minor'
            elif attendance.late_minutes <= 30:
                attendance.late_category = 'moderate'
            elif attendance.late_minutes <= 60:
                attendance.late_category = 'major'
            else:
                attendance.late_category = 'severe'

    def action_approve_late_arrival(self):
        """Action to approve late arrival"""
        self.ensure_one()
        if not self.is_late:
            raise ValidationError(_("This attendance is not marked as late."))

        self.manager_approved = True
        # Log approval in chatter
        self.message_post(
            body=_("Late arrival approved by %s") % self.env.user.name,
            subtype_xmlid='mail.mt_note'
        )

        return True

    def action_request_approval(self):
        """Employee action to request approval for late arrival"""
        self.ensure_one()
        if not self.is_late:
            raise ValidationError(_("This attendance is not marked as late."))

        # Send notification to manager
        if self.employee_id.parent_id:
            template = self.env.ref('myis_late_arrival.email_template_late_approval_request',
                                  raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)

        self.message_post(
            body=_("Late arrival approval requested"),
            subtype_xmlid='mail.mt_note'
        )

        return True
