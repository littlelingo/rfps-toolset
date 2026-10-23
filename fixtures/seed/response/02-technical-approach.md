<!-- Response source for the docx. Headings must match the docx exactly. Build with /rfps:build-wip. -->

# Technical Approach

We build the portal in three parts, each traced to the RFP.

- **Scheduling (RFP 2.1).** Supervisors create, move and cancel appointments from a single calendar view. [ASSERTION: the calendar prevents double-booking a bay]
- **Migration (RFP 2.2).** We load the legacy spreadsheet history into the portal before go-live, reconciling every record against the source, as we did when we moved 11 years of records without loss [GROUNDED: E-002].
- **Reminders (RFP 2.3).** The portal emails the responsible driver at least 3 days before each appointment. SMS is optional under Amendment 1, so we will not build it in the base scope.
- **Accessibility (RFP 2.4).** Every public and staff page is built and tested to WCAG 2.1 AA. [ASSERTION: accessibility testing is part of every release]
- **Reporting (RFP 2.5).** We will provide the monthly utilization report to the Fleet Manager.
