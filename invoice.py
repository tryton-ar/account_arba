# This file is part of account_arba Tryton.
# The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Invoice']


class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'

    arba_perception = fields.Function(fields.Numeric('Perception',
            digits=(16, 2)), 'get_arba_percentage')
    arba_retention = fields.Function(fields.Numeric('Retention',
            digits=(16, 2)), 'get_arba_percentage')

    def get_arba_percentage(self, name):
        percentage = None
        if name[5:] == 'perception':
            percentage = self.party.arba_perception
        else:
            percentage = self.party.arba_retention
        return percentage

    @fields.depends('arba_perception', 'arba_retention')
    def on_change_party(self):
        super(Invoice, self).on_change_party()
        self.arba_retention = None
        self.arba_perception = None
        if self.party:
            self.arba_retention = self.party.arba_retention
            self.arba_perception = self.party.arba_perception
