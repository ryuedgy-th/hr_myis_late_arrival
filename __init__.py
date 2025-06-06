from . import models
from . import wizard

def post_init_hook(cr, registry):
    """Post-installation hook to initialize module data"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Recompute all attendance late arrival data
    attendances = env['hr.attendance'].search([('check_in', '!=', False)])
    attendances._compute_late_arrival_info()

    # Update employee statistics
    employees = env['hr.employee'].search([])
    employees._compute_late_statistics()
    employees._compute_attendance_score()

    # Log successful installation
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("MYIS Late Arrival Management module installed successfully")
