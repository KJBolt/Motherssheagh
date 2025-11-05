from odoo import http
from odoo.http import request

class Home(http.Controller):
    @http.route('/', type='http', auth='public', methods=['GET'], website=True, csrf=False)
    def home(self):

        products = request.env['product.product'].search([
            ('name', '!=', 'Standard delivery')
        ], limit=4)
        return request.render('sheaonyou.home', {'products': products})
