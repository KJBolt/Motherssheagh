from odoo import http
from odoo.http import request

class AllProducts(http.Controller):
    @http.route('/shop_details/<int:product_id>', type='http', auth='public', website=True)
    def shop_details(self, product_id):
        # Fetch product template and get its default variant
        product = request.env['product.template'].sudo().search([('id', '=', product_id)])
        return request.render('sheaonyou.shop_details', {'product': product})
