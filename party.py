# This file is part of the account_arba module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from pyafipws.iibb import IIBB as WSIIBB
from calendar import monthrange
from decimal import Decimal

from trytond.model import ModelView
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

logger = logging.getLogger(__name__)


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'get_arba_data': {},
            })

    @classmethod
    @ModelView.button
    def get_arba_data(cls, parties):
        cls.import_arba_census(parties)

    @classmethod
    def import_arba_census(cls, parties):
        pool = Pool()
        Date = pool.get('ir.date')
        Company = pool.get('company.company')
        PartyWithholdingIIBB = pool.get('party.retencion.iibb')

        ws = cls.get_ws_arba()
        if not ws:
            return

        company = Company(Transaction().context['company'])
        arba_regimen_retencion = company.arba_regimen_retencion
        arba_regimen_percepcion = company.arba_regimen_percepcion
        if not arba_regimen_retencion and not arba_regimen_percepcion:
            return

        today = Date.today()
        _, end_date = monthrange(today.year, today.month)
        fecha_desde = today.strftime('%Y%m') + '01'
        fecha_hasta = today.strftime('%Y%m') + str(end_date)
        logger.info('fecha_desde: %s | fecha_hasta: %s' %
            (fecha_desde, fecha_hasta))

        for party in parties:
            if not party.vat_number:
                continue

            data = cls.get_arba_party_data(ws, party, fecha_desde, fecha_hasta)
            if data is None:
                continue

            clause = [('party', '=', party)]
            if arba_regimen_retencion:
                clause.append(('regimen_retencion', '=', arba_regimen_retencion))
            if arba_regimen_percepcion:
                clause.append(('regimen_percepcion', '=', arba_regimen_percepcion))
            iibb_regimenes = PartyWithholdingIIBB.search(clause)
            if iibb_regimenes:
                arba_regimen = iibb_regimenes[0]
            else:
                arba_regimen = PartyWithholdingIIBB(
                    party=party,
                    regimen_retencion=arba_regimen_retencion,
                    regimen_percepcion=arba_regimen_percepcion,
                    )
            iibb_rate_percepcion = data.AlicuotaPercepcion
            iibb_rate_retencion = data.AlicuotaRetencion
            logger.info('Party: %s | Percepción: %s | Retención: %s' %
                (party.vat_number, iibb_rate_percepcion, iibb_rate_retencion))
            if iibb_rate_percepcion != '':
                arba_regimen.rate_percepcion = Decimal(
                    iibb_rate_percepcion.replace(',', '.'))
            if iibb_rate_retencion != '':
                arba_regimen.rate_retencion = Decimal(
                    iibb_rate_retencion.replace(',', '.'))
            arba_regimen.save()
            Transaction().commit()

    @classmethod
    def get_ws_arba(cls):
        pool = Pool()
        Company = pool.get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
        else:
            logger.error('The company is not defined')
            raise UserError(gettext(
                'party_ar.msg_company_not_defined'))

        ws = WSIIBB()
        ws.Usuario = company.party.vat_number
        ws.Password = company.arba_password

        if company.arba_mode_cert == 'homologacion':
            URL = ('https://dfe.test.arba.gov.ar/DomicilioElectronico/'
                'SeguridadCliente/dfeServicioConsulta.do')
        elif company.arba_mode_cert == 'produccion':
            URL = ('https://dfe.arba.gov.ar/DomicilioElectronico/'
                'SeguridadCliente/dfeServicioConsulta.do')
        else:
            logger.error('Certification mode is not defined in company')
            return None

        ws.Conectar(URL, cacert=None)
        return ws

    @classmethod
    def get_arba_party_data(cls, ws, party, fecha_desde, fecha_hasta):
        ws.ConsultarContribuyentes(fecha_desde, fecha_hasta, party.vat_number)
        if ws.Excepcion:
            logger.error('Excepcion: %s\n%s' % (ws.Excepcion, ws.Traceback))
        while ws.LeerContribuyente():
            return ws

    @classmethod
    def import_cron_arba(cls):
        logger.info('Import ARBA Census::Start')
        parties = cls.search([('vat_number', '!=', None)])
        cls.import_arba_census(parties)
        logger.info('Import ARBA Census::End')


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
                ('party.party|import_cron_arba', 'Import ARBA Census'),
                ])
