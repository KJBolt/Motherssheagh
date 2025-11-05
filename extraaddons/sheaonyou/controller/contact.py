from odoo import http
from odoo.http import request   


class ContactController(http.Controller):
    @http.route('/contact', type='http', auth='public', website=True)
    def contact(self):
        return request.render('sheaonyou.contact')
