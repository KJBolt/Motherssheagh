from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shipping_carrier_id = fields.Many2one('shipping.carrier', string='Shipping Carrier')
    carrier_tracking_ref = fields.Char(string='Tracking Number')
    shipping_label = fields.Binary(string='Shipping Label', attachment=True)
    shipping_label_filename = fields.Char(string='Label Filename')
    shipping_cost = fields.Float(string='Shipping Cost')
    dhl_tracking_status = fields.Text(string='Tracking Status', readonly=True)
    dhl_last_update = fields.Datetime(string='Last Update', readonly=True)

    def action_create_dhl_shipment(self):
        """Create DHL shipment and generate label"""
        self.ensure_one()
        
        if not self.shipping_carrier_id:
            raise UserError(_('Please select a shipping carrier first.'))
        
        if self.shipping_carrier_id.carrier_type != 'dhl':
            raise UserError(_('Selected carrier is not DHL.'))
        
        result = self.shipping_carrier_id.create_dhl_shipment(self)
        
        if result:
            self.shipping_label_filename = f"DHL_Label_{self.name}.pdf"
            self.message_post(
                body=f"DHL Shipment created successfully. Tracking: {result['tracking_number']}",
                subject="Shipment Created"
            )
        
        return True

    def action_track_shipment(self):
        """Track DHL shipment"""
        self.ensure_one()
        
        if not self.carrier_tracking_ref:
            raise UserError(_('No tracking number found.'))
        
        if not self.shipping_carrier_id or self.shipping_carrier_id.carrier_type != 'dhl':
            raise UserError(_('Tracking is only available for DHL shipments.'))
        
        tracking_data = self.shipping_carrier_id.track_shipment(self.carrier_tracking_ref)
        
        if tracking_data and 'shipments' in tracking_data:
            shipment = tracking_data['shipments'][0]
            status = shipment.get('status', {}).get('description', 'Unknown')
            
            self.write({
                'dhl_tracking_status': status,
                'dhl_last_update': fields.Datetime.now()
            })
            
            self.message_post(
                body=f"Tracking Update: {status}",
                subject="Shipment Tracking"
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Tracking Update'),
                    'message': status,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_('Unable to retrieve tracking information.'))

    def action_open_tracking_url(self):
        """Open tracking URL in browser"""
        self.ensure_one()
        
        if not self.carrier_tracking_ref or not self.shipping_carrier_id:
            raise UserError(_('No tracking information available.'))
        
        url = self.shipping_carrier_id.get_tracking_link(self.carrier_tracking_ref)
        
        if url:
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }
        else:
            raise UserError(_('Tracking URL not available.'))