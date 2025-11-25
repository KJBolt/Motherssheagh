from odoo import http
from odoo.http import request


class CartController(http.Controller):
    @http.route('/shop/cart_new', type='http', auth='public', website=True)
    def fetch_cart_details(self):
        # Get current cart
        order = request.website.sale_get_order()
        return request.render('sheaonyou.cart', {'order': order})
    

    @http.route('/shop/cart/add', type='http', auth='public', website=True, methods=['POST'])
    def add_to_cart(self, product_id, **kwargs):
        """Add product to cart and redirect to cart page"""
        # Get or create sale order (cart)
        order = request.website.sale_get_order(force_create=True)
        
        # Get product template
        product_template = request.env['product.template'].sudo().browse(int(product_id))
        
        if product_template.exists():
            # Get the product variant (product.product)
            product_variant = product_template.product_variant_id
            if product_variant:
                # Add product to cart (quantity = 1)
                order._cart_update(
                    product_id=product_variant.id,
                    add_qty=1,
                    set_qty=0,
                )
        
        # Redirect to cart page
        return request.redirect('/shop/cart_new')
    
    
    @http.route('/shop/cart/update_line', type='json', auth='public', website=True)
    def update_cart_line(self, line_id=None, set_qty=None, **kwargs):
        """Update cart item quantity or remove item"""
        order = request.website.sale_get_order()
        success = False
        message = ''
        
        if order and line_id:
            line = request.env['sale.order.line'].sudo().browse(int(line_id))
            
            # Verify the line belongs to the current order
            if line.exists() and line.order_id.id == order.id:
                if set_qty is not None:
                    qty = float(set_qty)
                    if qty <= 0:
                        # Remove item from cart
                        line.unlink()
                        success = True
                        message = 'Item removed from cart'
                    else:
                        # Update quantity
                        line.write({'product_uom_qty': qty})
                        success = True
                        message = 'Cart updated'
        
        # Get updated cart totals
        order = request.website.sale_get_order()
        cart_data = {
            'success': success,
            'message': message,
            'cart_quantity': int(order.cart_quantity) if order else 0,
            'amount_untaxed': order.amount_untaxed if order else 0,
            'amount_tax': order.amount_tax if order else 0,
            'amount_total': order.amount_total if order else 0,
            'currency_symbol': order.currency_id.symbol if order else '$',
            'line_count': len(order.order_line) if order else 0
        }
        
        return cart_data
