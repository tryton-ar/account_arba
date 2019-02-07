# This file is part of account_arba Tryton.
# The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Party']


class Party:
    __metaclass__ = PoolMeta
    __name__ = 'party.party'

    arba_perception = fields.Numeric('Perception', digits=(16, 2),
        readonly=True)
    arba_retention = fields.Numeric('Retention', digits=(16, 2),
        readonly=True)
