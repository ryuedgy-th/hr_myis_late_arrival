from odoo import models, fields, api
from datetime import datetime, timedelta
import pytz
import logging

_logger = logging.getLogger(__name__)

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Basic late arrival fields
    is_late = fields.Boolean(
        string='Late Arrival',
        compute='_compute_is_late',
        store=True,
        help="True if employee checked in after 8:15 AM"
    )

    late_minutes = fields.Integer(
        string='Minutes Late',
        compute='_compute_is_late',
        store=True,
        help="Number of minutes late after 8:15 AM"
    )

    expected_check_in = fields.Datetime(
        string='Expected Check-in',
        compute='_compute_is_late',
        store=True,
        help="Expected check-in time (8:00 AM)"
    )

    late_reason = fields.Text(
        string='Reason for Being Late',
        help="Employee explanation for late arrival"
    )

    manager_approved = fields.Boolean(
        string='Approved by Manager',
        default=False,
        help="Manager has approved this late arrival"
    )

    @api.depends('check_in', 'employee_id')
    def _compute_is_late(self):
        """Fixed late detection with proper timezone handling"""
        for record in self:
            record.is_late = False
            record.late_minutes = 0
            record.expected_check_in = False

            if not record.check_in:
                continue

            # Get check-in time and ensure it's timezone-aware
            check_in_time = record.check_in
            if check_in_time.tzinfo is None:
                # Assume UTC if no timezone info
                check_in_time = pytz.utc.localize(check_in_time)

            # Convert to Bangkok timezone for calculation
            bangkok_tz = pytz.timezone('Asia/Bangkok')
            check_in_bangkok = check_in_time.astimezone(bangkok_tz)

            _logger.info(f"Processing attendance {record.id}: check_in = {check_in_time} (UTC), {check_in_bangkok} (Bangkok)")

            # Only process morning check-ins (before 12:00 PM)
            if check_in_bangkok.hour >= 12:
                _logger.info(f"Skipping afternoon check-in: {check_in_bangkok.hour}:00")
                continue

            # Set expected check-in to 8:00 AM Bangkok time on the same date
            check_in_date = check_in_bangkok.date()
            expected_bangkok = bangkok_tz.localize(
                datetime.combine(check_in_date, datetime.min.time().replace(hour=8, minute=0))
            )

            # Convert back to UTC for storage
            record.expected_check_in = expected_bangkok.astimezone(pytz.utc).replace(tzinfo=None)

            # Grace period ends at 8:15 AM Bangkok time
            grace_period_end_bangkok = expected_bangkok + timedelta(minutes=15)

            _logger.info(f"Expected (Bangkok): {expected_bangkok}")
            _logger.info(f"Grace end (Bangkok): {grace_period_end_bangkok}")
            _logger.info(f"Actual (Bangkok): {check_in_bangkok}")

            # Check if late
            if check_in_bangkok > grace_period_end_bangkok:
                record.is_late = True
                late_delta = check_in_bangkok - grace_period_end_bangkok
                record.late_minutes = int(late_delta.total_seconds() / 60)
                _logger.info(f"LATE: {record.late_minutes} minutes")
            else:
                early_delta = grace_period_end_bangkok - check_in_bangkok
                _logger.info(f"ON TIME: arrived {int(early_delta.total_seconds() / 60)} minutes before deadline")

    def action_approve_late(self):
        """Manager action to approve late arrival"""
        self.ensure_one()
        self.manager_approved = True
        return True

    def manual_recompute_late(self):
        """Manual action to recompute late arrival with forced refresh"""
        self.ensure_one()

        # Force recomputation by invalidating cache
        self.invalidate_cache(['is_late', 'late_minutes', 'expected_check_in'])

        # Recompute
        self._compute_is_late()

        # Force database update
        self.flush()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recomputed Successfully',
                'message': f'Late: {self.is_late}, Minutes: {self.late_minutes}, Check-in: {self.check_in}',
                'type': 'success'
            }
        }

    def mass_recompute_late(self):
        """Mass recompute for all attendance records"""
        all_attendances = self.env['hr.attendance'].search([
            ('check_in', '!=', False)
        ])

        _logger.info(f"Mass recomputing {len(all_attendances)} attendance records")

        for attendance in all_attendances:
            attendance._compute_is_late()

        all_attendances.flush()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Mass Recompute Completed',
                'message': f'Processed {len(all_attendances)} records',
                'type': 'success'
            }
        }
