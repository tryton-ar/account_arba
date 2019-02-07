# This file is part of account_arba Tryton.
# The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, ModelSingleton, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ValueMixin
from trytond import backend
from trytond.tools.multivalue import migrate_property

from calendar import monthrange
from pyafipws import iibb
from decimal import Decimal

import logging
logger = logging.getLogger(__name__)


__all__ = ['Configuration', 'ConfigurationPassword', 'ConfigurationCert']


class Configuration(ModelSingleton, ModelSQL, ModelView):
    'ARBA integration'
    __name__ = 'account.arba.configuration'
    password = fields.MultiValue(fields.Char('password'))
    arba_mode_cert = fields.MultiValue(fields.Selection([
                ('homologacion', 'Homologation'),
                ('produccion', 'Production'),
                ], 'Modo de certificacion'))

    @classmethod
    def __setup__(cls):
        super(Configuration, cls).__setup__()
        cls._error_messages.update({
            'arba_server_error': ('ARBA server error: '"%(msg)s"),
            'census_not_import': 'There are not census to import',
        })

        cls._buttons.update({
                'import_census': {},
                })

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'password':
            return pool.get('account_arba.configuration.password')
        if field == 'arba_mode_cert':
            return pool.get('account_arba.configuration.cert')
        return super(Configuration, cls).multivalue_model(field)

    @classmethod
    def default_password(cls, **pattern):
        return cls.multivalue_model(
            'password').default_password()

    @classmethod
    def default_arba_mode_cert(cls, **pattern):
        return cls.multivalue_model(
            'arba_mode_cert').default_arba_mode_cert()


    @classmethod
    @ModelView.button
    def import_census(cls, configs):
        """
        Import arba census.
        """
        partys = Pool().get('party.party').search([
                ('vat_number', '!=', None),
                ])

        ws = cls.conect_arba()
        Date = Pool().get('ir.date')
        _, end_date = monthrange(Date.today().year, Date.today().month)
        fecha_desde = Date.today().strftime('%Y%m') + '01'
        fecha_hasta = Date.today().strftime('%Y%m') + str(end_date)
        logger.info('fecha_desde: %s | fecha_desde: %s.'
            % (fecha_desde, fecha_hasta))
        for party in partys:
            data = cls.get_arba_data(ws, party, fecha_desde, fecha_hasta)
            if data is not None:
                logger.error('party: %s | AlicuotaPercepcion: %s.'
                    % (party.vat_number, data.AlicuotaPercepcion))
                if data.AlicuotaPercepcion != '':
                    party.AlicuotaPercepcion = Decimal(
                        data.AlicuotaPercepcion.replace(',', '.'))
                if data.AlicuotaRetencion != '':
                    party.arba_retention = Decimal(
                        data.AlicuotaRetencion.replace(',', '.'))
                    party.arba_perception = Decimal(
                        data.AlicuotaPercepcion.replace(',', '.'))
                party.save()
                Transaction().cursor.commit()

    @classmethod
    def conect_arba(self):
        'conect_arba'
        Config = Pool().get('account.arba.configuration')
        config = Config(1)
        ws = iibb.IIBB()
        Party = Pool().get('party.party')
        ws.Usuario = Party(Transaction().context.get('company')).vat_number
        ws.Password = config.password
        if config.arba_mode_cert == 'homologacion':
            ws.Conectar()
        else:
            URL = iibb.URL.replace("https://dfe.test.arba.gov.ar/",
                "https://dfe.arba.gov.ar/")
            ws.Conectar(URL, cacert=None)
        return ws

    @classmethod
    def get_arba_data(cls, ws, party, fecha_desde, fecha_hasta):
        'get_arba_data'
        ws.ConsultarContribuyentes(fecha_desde, fecha_hasta, party.vat_number)
        while ws.LeerContribuyente():
            return ws

    @classmethod
    def import_cron_census(cls, args=None):
        """
        Cron import arba census.
        """
        logger.info('Start Scheduler start import arba census.')
        cls.import_census(args)
        logger.info('End Scheduler import arba census.')


class _ConfigurationValue(ModelSQL):

    _configuration_value_field = None

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        exist = TableHandler.table_exist(cls._table)

        super(_ConfigurationValue, cls).__register__(module_name)

        if not exist:
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.append(cls._configuration_value_field)
        value_names.append(cls._configuration_value_field)
        migrate_property(
            'account_arba.configuration', field_names, cls, value_names,
            fields=fields)


class ConfigurationPassword(_ConfigurationValue, ModelSQL, ValueMixin):
    'Configuration ARBA Password'
    __name__ = 'account_arba.configuration.password'
    password = fields.Char('Password')
    _configuration_value_field = 'password'


class ConfigurationCert(_ConfigurationValue, ModelSQL, ValueMixin):
    'Configuration ARBA Cert'
    __name__ = 'account_arba.configuration.cert'
    arba_mode_cert = fields.Selection([
                ('homologacion', 'Homologation'),
                ('produccion', 'Production'),
                ], 'Modo de certificacion')
    _configuration_value_field = 'arba_mode_cert'

    @classmethod
    def default_arba_mode_cert(cls):
        return 'homologacion'
