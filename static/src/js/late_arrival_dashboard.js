/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

class LateArrivalDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            todayStats: {},
            weekStats: {},
            monthStats: {},
            loading: true
        });

        onWillStart(async () => {
            await this.loadStats();
        });
    }

    async loadStats() {
        try {
            const today = new Date().toISOString().split('T')[0];
            const weekStart = this.getWeekStart();
            const monthStart = this.getMonthStart();

            // Load today's stats
            const todayLate = await this.orm.searchCount("hr.attendance", [
                ["is_late", "=", true],
                ["check_in", ">=", today + " 00:00:00"],
                ["check_in", "<", this.getTomorrow() + " 00:00:00"]
            ]);

            // Load week's stats
            const weekLate = await this.orm.searchCount("hr.attendance", [
                ["is_late", "=", true],
                ["check_in", ">=", weekStart + " 00:00:00"]
            ]);

            // Load month's stats
            const monthLate = await this.orm.searchCount("hr.attendance", [
                ["is_late", "=", true],
                ["check_in", ">=", monthStart + " 00:00:00"]
            ]);

            this.state.todayStats = { late: todayLate };
            this.state.weekStats = { late: weekLate };
            this.state.monthStats = { late: monthLate };
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading late arrival stats:", error);
            this.state.loading = false;
        }
    }

    getWeekStart() {
        const today = new Date();
        const dayOfWeek = today.getDay();
        const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        const monday = new Date(today);
        monday.setDate(today.getDate() + mondayOffset);
        return monday.toISOString().split('T')[0];
    }

    getMonthStart() {
        const today = new Date();
        return new Date(today.getFullYear(), today.getMonth(), 1)
            .toISOString().split('T')[0];
    }

    getTomorrow() {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        return tomorrow.toISOString().split('T')[0];
    }
}

LateArrivalDashboard.template = "myis_late_arrival.LateArrivalDashboard";

registry.category("actions").add("late_arrival_dashboard", LateArrivalDashboard);
