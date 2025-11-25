from odoo import http
from odoo.http import request
import json

class AllProducts(http.Controller):
    @http.route('/shop_new', type='http', auth='public', website=True)
    def all_products(self):

        products = request.env['product.template'].sudo().search([
            ('name', '!=', 'Standard delivery')
        ])
        return request.render('sheaonyou.shop', {'products': products})
    
    @http.route('/shop/search', type='json', auth='public', website=True)
    def search_products(self, search_query='', sort_by='', price_min='', price_max=''):
        """Search products by name, filter by price range, and sort by price"""
        domain = [('name', '!=', 'Standard delivery')]
        
        if search_query and search_query.strip():
            domain.append(('name', 'ilike', search_query))
        
        # Filter by price range
        if price_min and str(price_min).strip():
            try:
                domain.append(('list_price', '>=', float(price_min)))
            except ValueError:
                pass
        
        if price_max and str(price_max).strip():
            try:
                domain.append(('list_price', '<=', float(price_max)))
            except ValueError:
                pass
        
        # Determine sort order based on sort_by parameter
        order = 'id desc'  # Default order
        if sort_by == 'price_low_high':
            order = 'list_price asc'
        elif sort_by == 'price_high_low':
            order = 'list_price desc'
        
        products = request.env['product.template'].sudo().search(domain, order=order)
        
        # Format products data for JSON response
        products_data = []
        for product in products:
            # Use product.template for image URL
            image_url = '/web/image/product.template/%s/image_1024' % product.id if product.image_1024 else '/web/image/product.template/1/image_1024'
            
            products_data.append({
                'id': product.id,
                'name': product.name,
                'list_price': product.list_price,
                'currency_symbol': product.currency_id.symbol,
                'image_url': image_url,
                'has_image': bool(product.image_1024)
            })
        
        return products_data
