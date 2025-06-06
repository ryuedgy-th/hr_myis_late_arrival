from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta

class LateArrivalReportWizard(models.TransientModel):
    _name = 'late.arrival.report.wizard'
    _description = 'Late Arrival Report Wizard'

    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.today
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Leave empty for all departments'
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Leave empty for all employees'
    )
    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('department', 'Department Analysis'),
        ('employee', 'Employee Analysis')
    ], string='Report Type', default='summary', required=True)

    include_approved = fields.Boolean(
        string='Include Approved Late Arrivals',
        default=True
    )
    min_late_minutes = fields.Integer(
        string='Minimum Late Minutes',
        default=0,
        help='Only include late arrivals with at least this many minutes'
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError(_('From Date cannot be later than To Date'))

            # Limit to reasonable date range
            max_range = timedelta(days=365)
            if record.date_to - record.date_from > max_range:
                raise UserError(_('Date range cannot exceed 365 days'))

    def action_generate_report(self):
        """Generate the late arrival report"""
        self.ensure_one()

        # Build domain for searching attendances
        domain = [
            ('is_late', '=', True),
            ('check_in', '>=', self.date_from.strftime('%Y-%m-%d 00:00:00')),
            ('check_in', '<=', self.date_to.strftime('%Y-%m-%d 23:59:59')),
            ('late_minutes', '>=', self.min_late_minutes)
        ]

        if not self.include_approved:
            domain.append(('manager_approved', '=', False))

        if self.department_ids:
            domain.append(('employee_id.department_id', 'in', self.department_ids.ids))

        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        # Get the data
        late_attendances = self.env['hr.attendance'].search(domain)

        if not late_attendances:
            raise UserError(_('No late arrivals found for the selected criteria'))

        # Return appropriate action based on report type
        if self.report_type == 'summary':
            return self._action_summary_report(late_attendances)
        elif self.report_type == 'detailed':
            return self._action_detailed_report(late_attendances)
        elif self.report_type == 'department':
            return self._action_department_report(late_attendances)
        elif self.report_type == 'employee':
            return self._action_employee_report(late_attendances)

    def _action_summary_report(self, attendances):
        """Generate summary report"""
        context = {
            'default_attendances': attendances.ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': 'summary'
        }

        return {
            'name': _('Late Arrival Summary Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'pivot,graph,tree',
            'domain': [('id', 'in', attendances.ids)],
            'context': context
        }

    def _action_detailed_report(self, attendances):
        """Generate detailed report"""
        return {
            'name': _('Late Arrival Detailed Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form',
            'view_id': self.env.ref('myis_late_arrival.hr_attendance_late_tree').id,
            'domain': [('id', 'in', attendances.ids)],
            'context': {
                'search_default_group_by_employee': 1,
                'search_default_group_by_date': 2
            }
        }

    def _action_department_report(self, attendances):
        """Generate department analysis report"""
        department_ids = attendances.mapped('employee_id.department_id').ids

        return {
            'name': _('Department Late Arrival Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,kanban,pivot,graph',
            'domain': [('department_id', 'in', department_ids)],
            'context': {
                'search_default_group_by_department': 1,
                'attendances_domain': [('id', 'in', attendances.ids)]
            }
        }

    def _action_employee_report(self, attendances):
        """Generate employee analysis report"""
        employee_ids = attendances.mapped('employee_id').ids

        return {
            'name': _('Employee Late Arrival Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,kanban,form',
            'domain': [('id', 'in', employee_ids)],
            'context': {
                'attendances_domain': [('id', 'in', attendances.ids)]
            }
        }

class LateArrivalBulkApprovalWizard(models.TransientModel):
    _name = 'late.arrival.bulk.approval.wizard'
    _description = 'Bulk Approve Late Arrivals'

    attendance_ids = fields.Many2many(
        'hr.attendance',
        string='Late Arrivals to Approve',
        domain=[('is_late', '=', True), ('manager_approved', '=', False)]
    )
    approval_reason = fields.Text(
        string='Approval Reason',
        help='Reason for bulk approval (will be added to each record)'
    )

    def action_bulk_approve(self):
        """Bulk approve selected late arrivals"""
        if not self.attendance_ids:
            raise UserError(_('Please select at least one late arrival to approve'))

        for attendance in self.attendance_ids:
            attendance.manager_approved = True

            # Add approval message to chatter
            message = _("Bulk approved by %s") % self.env.user.name
            if self.approval_reason:
                message += _("\nReason: %s") % self.approval_reason

            attendance.message_post(
                body=message,
                subtype_xmlid='mail.mt_note'
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%s late arrivals have been approved') % len(self.attendance_ids),
                'type': 'success'
            }
        }
