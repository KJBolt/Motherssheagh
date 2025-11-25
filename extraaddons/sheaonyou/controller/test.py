from odoo import http
from odoo.http import request

class TestController(http.Controller):
    @http.route('/test', type='http', auth='public', website=True)
    def test(self, **kw):
        return request.render('sheaonyou.test')
