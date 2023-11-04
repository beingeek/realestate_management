# Copyright (c) 2023, CE Construction and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class PlotList(Document):
	def validate(self):
		self.set_title()

	def set_title(self):
		self.title = _("{0} - {1} - {2}").format(self.plot_name, self.land_price, self.plot_feature)