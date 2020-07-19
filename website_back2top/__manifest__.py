# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Website Scroll Back To Top",
  "summary"              :  """Website Scroll Back To Top adds a button on the web page page to scroll back to the top.""",
  "category"             :  "Website",
  "version"              :  "1.0.0",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "website"              :  "https://store.webkul.com/",
  "description"          :  """Website Scroll Back To Top
Odoo Website Scroll Back To Top
Go to the Top
Scroll Back To Top
Button to take to the Top
Scroll Back to the top of the page""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=website_back2top",
  "depends"              :  ['website'],
  "data"                 :  ['views/templates.xml'],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "pre_init_hook"        :  "pre_init_check",
}