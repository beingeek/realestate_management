from . import __version__ as app_version

app_name = "realestate_account"
app_title = "Realestate Account"
app_publisher = "CE Construction"
app_description = "A Realestate accounting management system"
app_email = "info@ce-construction.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/realestate_account/css/realestate_account.css"
# app_include_js = "/assets/realestate_account/js/realestate_account.js"

# include js, css files in header of web template
# web_include_css = "/assets/realestate_account/css/realestate_account.css"
# web_include_js = "/assets/realestate_account/js/realestate_account.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "realestate_account/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "realestate_account.utils.jinja_methods",
#	"filters": "realestate_account.utils.jinja_filters"
# }

# Installation
# ------------

after_migrate = "realestate_account.setup.install.after_migrate"
after_install = "realestate_account.setup.install.after_migrate"

# Uninstallation
# ------------

before_uninstall = "realestate_account.setup.install.before_uninstall"
# after_uninstall = "realestate_account.uninstall.after_uninstall"


# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "realestate_account.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

period_closing_doctypes = [
	"Sales Invoice",
	"Purchase Invoice",
	"Journal Entry",
	"Bank Clearance",
	"Stock Entry",
	"Dunning",
	"Invoice Discounting",
	"Payment Entry",
	"Period Closing Voucher",
	"Process Deferred Accounting",
	"Asset",
	"Asset Capitalization",
	"Asset Repair",
	"Delivery Note",
	"Landed Cost Voucher",
	"Purchase Receipt",
	"Stock Reconciliation",
	"Subcontracting Receipt",
	"Plot Booking",
	"Customer Payment",
	"Property Transfer",
	"Cancellation Property",
    "Plot Token" 
]

doc_events = {
    "Journal Entry": {
        'on_cancel': [
            'realestate_account.events.journal_entry.check_plot_booking',
            'realestate_account.events.journal_entry.check_document_status'
        ]
    },
    "Customer": {
        'validate': [
            'realestate_account.events.journal_entry.validate_id_card_number_format'
        ]
    },
}


# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"realestate_account.tasks.all"
#	],
#	"daily": [
#		"realestate_account.tasks.daily"
#	],
#	"hourly": [
#		"realestate_account.tasks.hourly"
#	],
#	"weekly": [
#		"realestate_account.tasks.weekly"
#	],
#	"monthly": [
#		"realestate_account.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "realestate_account.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "realestate_account.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "realestate_account.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["realestate_account.utils.before_request"]
# after_request = ["realestate_account.utils.after_request"]

# Job Events
# ----------
# before_job = ["realestate_account.utils.before_job"]
# after_job = ["realestate_account.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"realestate_account.auth.validate"
# ]
