from odoo import http
from odoo.http import request


class AboutController(http.Controller):
    @http.route('/about', type='http', auth='public', methods=['GET'], csrf=False, website=True)
    def about(self):
        return request.render('sheaonyou.about')
