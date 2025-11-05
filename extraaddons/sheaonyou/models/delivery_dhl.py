import requests
import base64
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ShippingCarrier(models.Model):
    """Custom Shipping Carrier for Odoo Community Edition"""
    _name = 'shipping.carrier'
    _description = 'Shipping Carrier'
    _order = 'sequence, name'

    name = fields.Char(string='Carrier Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    carrier_type = fields.Selection([
        ('dhl', 'DHL Express'),
        ('fixed', 'Fixed Price'),
        ('free', 'Free Shipping'),
    ], string='Carrier Type', required=True, default='dhl')
    
    # Pricing
    fixed_price = fields.Float(string='Fixed Price', default=0.0)
    free_if_over = fields.Float(string='Free if Order Over', default=0.0)
    
    # DHL API Credentials
    dhl_api_key = fields.Char(string='DHL API Key', groups='base.group_system')
    dhl_api_secret = fields.Char(string='DHL API Secret', groups='base.group_system')
    dhl_account_number = fields.Char(string='DHL Account Number')
    
    # DHL Configuration
    dhl_product_code = fields.Selection([
        ('P', 'DHL Express Worldwide'),
        ('N', 'DHL Express 12:00'),
        ('K', 'DHL Express 9:00'),
        ('Y', 'DHL Express Envelope'),
    ], string='DHL Product', default='P')
    
    dhl_package_type = fields.Selection([
        ('EE', 'DHL Express Envelope'),
        ('OD', 'Other DHL Packaging'),
        ('CP', 'Customer Provided'),
    ], string='Package Type', default='OD')
    
    dhl_test_mode = fields.Boolean(string='Test Mode', default=True)

    def _get_dhl_api_url(self):
        if self.dhl_test_mode:
            return 'https://express.api.dhl.com/mydhlapi/test'
        return 'https://express.api.dhl.com/mydhlapi'

    def _get_dhl_auth_header(self):
        if not self.dhl_api_key or not self.dhl_api_secret:
            raise UserError(_('DHL API credentials not configured.'))
        credentials = f"{self.dhl_api_key}:{self.dhl_api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {'Authorization': f'Basic {encoded}', 'Content-Type': 'application/json'}

    def calculate_shipping_rate(self, order):
        self.ensure_one()
        if self.carrier_type == 'free':
            return 0.0
        elif self.carrier_type == 'fixed':
            if self.free_if_over and order.amount_untaxed >= self.free_if_over:
                return 0.0
            return self.fixed_price
        elif self.carrier_type == 'dhl':
            return self._get_dhl_rate(order)
        return 0.0

    def _get_dhl_rate(self, order):
        try:
            payload = self._prepare_dhl_rate_request(order)
            url = f"{self._get_dhl_api_url()}/rates"
            headers = self._get_dhl_auth_header()
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if 'products' in result and result['products']:
                    return float(result['products'][0]['totalPrice'][0]['price'])
            return self.fixed_price or 0.0
        except Exception as e:
            _logger.error(f"DHL Rate Error: {str(e)}")
            return self.fixed_price or 0.0

    def _prepare_dhl_rate_request(self, order):
        shipper = order.company_id.partner_id
        recipient = order.partner_shipping_id or order.partner_id
        total_weight = sum(line.product_id.weight * line.product_uom_qty 
                        for line in order.order_line if line.product_id.weight) or 1.0
        return {
            "customerDetails": {
                "shipperDetails": {
                    "postalCode": shipper.zip or '',
                    "cityName": shipper.city or '',
                    "countryCode": shipper.country_id.code or 'US',
                },
                "receiverDetails": {
                    "postalCode": recipient.zip or '',
                    "cityName": recipient.city or '',
                    "countryCode": recipient.country_id.code or 'US',
                }
            },
            "accounts": [{"typeCode": "shipper", "number": self.dhl_account_number}],
            "productCode": self.dhl_product_code,
            "packages": [{"weight": total_weight, "dimensions": {"length": 10, "width": 10, "height": 10}}],
            "plannedShippingDateAndTime": datetime.now().strftime('%Y-%m-%dT%H:%M:%S GMT+00:00'),
            "unitOfMeasurement": "metric",
            "isCustomsDeclarable": shipper.country_id != recipient.country_id,
        }

    def create_dhl_shipment(self, picking):
        self.ensure_one()
        try:
            payload = self._prepare_dhl_shipment_request(picking)
            url = f"{self._get_dhl_api_url()}/shipments"
            headers = self._get_dhl_auth_header()
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code in [200, 201]:
                data = response.json()
                tracking = data.get('shipmentTrackingNumber')
                label = self._get_dhl_label(data)
                picking.write({'carrier_tracking_ref': tracking, 'shipping_label': label})
                return {'tracking_number': tracking, 'label': label}
            else:
                raise UserError(_(f"DHL Shipment Failed: {response.text}"))
        except Exception as e:
            raise UserError(_(f"Error: {str(e)}"))

    def _prepare_dhl_shipment_request(self, picking):
        shipper = picking.company_id.partner_id
        recipient = picking.partner_id
        total_weight = sum(move.product_id.weight * move.product_uom_qty 
                        for move in picking.move_ids_without_package if move.product_id.weight) or 1.0
        return {
            "plannedShippingDateAndTime": datetime.now().strftime('%Y-%m-%dT%H:%M:%S GMT+00:00'),
            "pickup": {"isRequested": False},
            "productCode": self.dhl_product_code,
            "accounts": [{"typeCode": "shipper", "number": self.dhl_account_number}],
            "customerDetails": {
                "shipperDetails": {
                    "postalAddress": {"postalCode": shipper.zip or '', "cityName": shipper.city or '', 
                                    "countryCode": shipper.country_id.code or 'US', "addressLine1": shipper.street or ''},
                    "contactInformation": {"email": shipper.email or '', "phone": shipper.phone or '', 
                                        "companyName": shipper.name or '', "fullName": shipper.name or ''}
                },
                "receiverDetails": {
                    "postalAddress": {"postalCode": recipient.zip or '', "cityName": recipient.city or '', 
                                    "countryCode": recipient.country_id.code or 'US', "addressLine1": recipient.street or ''},
                    "contactInformation": {"email": recipient.email or '', "phone": recipient.phone or '', 
                                        "companyName": recipient.name or '', "fullName": recipient.name or ''}
                }
            },
            "content": {
                "packages": [{"typeCode": self.dhl_package_type, "weight": total_weight, 
                            "dimensions": {"length": 10, "width": 10, "height": 10}}],
                "isCustomsDeclarable": shipper.country_id != recipient.country_id,
                "description": picking.origin or 'Shipment',
                "unitOfMeasurement": "metric"
            },
            "outputImageProperties": {"imageOptions": [{"typeCode": "label", "templateName": "ECOM26_84_001", "isRequested": True}]}
        }

    def _get_dhl_label(self, shipment_data):
        if 'documents' in shipment_data:
            for doc in shipment_data['documents']:
                if doc.get('typeCode') == 'label':
                    return base64.b64decode(doc['content'])
        return False

    def track_shipment(self, tracking_number):
        try:
            url = f"{self._get_dhl_api_url()}/shipments/{tracking_number}/tracking"
            response = requests.get(url, headers=self._get_dhl_auth_header(), timeout=30)
            return response.json() if response.status_code == 200 else False
        except:
            return False

    def get_tracking_link(self, tracking_number):
        return f"https://www.dhl.com/en/express/tracking.html?AWB={tracking_number}" if tracking_number else False