# This file is part of the account_arba module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'

    arba_password = fields.Char('Password')
    arba_mode_cert = fields.Selection([
        (None, 'n/a'),
        ('homologacion', 'Homologación'),
        ('produccion', 'Producción'),
        ], 'Modo de certificacion', sort=False)
    arba_regimen_retencion = fields.Many2One('account.retencion',
        'Régimen Retención ARBA',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'iibb')])
    arba_regimen_percepcion = fields.Many2One('account.tax',
        'Régimen Percepción ARBA',
        domain=[
            ('group.afip_kind', '=', 'provincial'),
            ('group.kind', '=', 'sale'),
            ])

    @staticmethod
    def default_arba_mode_cert():
        return None
