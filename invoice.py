# This file is part of account_arba Tryton.
# The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['Invoice']


class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'

    arba_perception = fields.Numeric('Perception', digits=(16, 2),
        readonly=True)
    arba_retention = fields.Numeric('Retention', digits=(16, 2),
        readonly=True)

    @fields.depends('arba_perception', 'arba_retention')
    def on_change_party(self):
        super(Invoice, self).on_change_party()
        self.arba_retention = None
        self.arba_perception = None
        if self.party:
            self.arba_retention = self.party.arba_retention
            self.arba_perception = self.party.arba_perception

    #@classmethod
    #def view_attributes(cls):
    #    return super(Invoice, cls).view_attributes() + [
    #        ('//[field="arba_perception"]', 'states', {
    #                'invisible': Eval('type').in_(['in_invoice', 'in_credit_note']),
    #                }),
    #        ('//[field="arba_retention"]', 'states', {
    #                'invisible': Eval('type').in_(['out_invoice', 'out_credit_note']),
    #                }),
    #        ]

    @classmethod
    def view_attributes(cls):
        states_in = {'invisible': Eval('type').in_(['in_invoice', 'in_credit_note'])}
        states_out = {'invisible': Eval('type').in_(['out_invoice', 'out_credit_note'])}
        #states = {'invisible': True}
        return super(Invoice, cls).view_attributes() + [
            ('/form//group[@id="arba_perception"]', 'states', states_in),
            #('/form//field[@name="arba_perception"]', 'states', states_in),
            ('/form//group[@id="arba_retention"]', 'states', states_out),
            #('/form//field[@name="arba_retention"]', 'states', states_out),
            ]
