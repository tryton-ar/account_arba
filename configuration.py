# -*- coding: utf-8 -*-
# This file is part of account_arba Tryton.
# The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, ModelSingleton, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from calendar import monthrange
import string
import random
import hashlib
from pyafipws import iibb
import logging
logger = logging.getLogger(__name__)

try:
    import bcrypt
except ImportError:
    bcrypt = None

__all__ = ['Configuration']


class Configuration(ModelSingleton, ModelSQL, ModelView):
    'ARBA integration'

    __name__ = 'account.arba.configuration'

    password_hash = fields.Property(fields.Char('Password Hash'))
    password = fields.Property(fields.Function(fields.Char('API Password'), getter='get_password',
        setter='set_password'))
    arba_mode_cert = fields.Property(fields.Selection([
           ('homologacion', u'Homologación'),
           ('produccion', u'Producción'),
       ], 'Modo de certificacion',
       help=u"El objetivo de Homologación (testing), es facilitar las pruebas. \
           Los certificados de Homologación y Producción son distintos."))

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

    @staticmethod
    def default_arba_mode_cert():
        return 'homologacion'

    def get_password(self, name):
        return 'x' * 10

    @classmethod
    def set_password(cls, users, name, value):
        if value == 'x' * 10:
            return
        to_write = []
        for user in users:
            to_write.extend([[user], {
                        'password_hash': cls.hash_password(value),
                        }])
        cls.write(*to_write)

    @staticmethod
    def hash_method():
        return 'bcrypt' if bcrypt else 'sha1'

    @classmethod
    def hash_password(cls, password):
        '''Hash given password in the form
        <hash_method>$<password>$<salt>...'''
        if not password:
            return ''
        return getattr(cls, 'hash_' + cls.hash_method())(password)

    @classmethod
    def check_password(cls, password, hash_):
        if not hash_:
            return False
        hash_method = hash_.split('$', 1)[0]
        return getattr(cls, 'check_' + hash_method)(password, hash_)

    @classmethod
    def hash_sha1(cls, password):
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        salt = ''.join(random.sample(string.ascii_letters + string.digits, 8))
        hash_ = hashlib.sha1(password + salt).hexdigest()
        return '$'.join(['sha1', hash_, salt])

    @classmethod
    def check_sha1(cls, password, hash_):
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        if isinstance(hash_, unicode):
            hash_ = hash_.encode('utf-8')
        hash_method, hash_, salt = hash_.split('$', 2)
        salt = salt or ''
        assert hash_method == 'sha1'
        return hash_ == hashlib.sha1(password + salt).hexdigest()

    @classmethod
    def hash_bcrypt(cls, password):
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        hash_ = bcrypt.hashpw(password, bcrypt.gensalt())
        return '$'.join(['bcrypt', hash_])

    @classmethod
    def check_bcrypt(cls, password, hash_):
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        if isinstance(hash_, unicode):
            hash_ = hash_.encode('utf-8')
        hash_method, hash_ = hash_.split('$', 1)
        assert hash_method == 'bcrypt'
        return hash_ == bcrypt.hashpw(password, hash_)

    @classmethod
    @ModelView.button
    def import_census(self, configs):
        """
        Import arba census.
        """
        partys = Pool().get('party.party').search([
                ('vat_number', '!=', None),
                ])

        ws = self.conect_arba()
        Date = Pool().get('ir.date')
        _, end_date = monthrange(Date.today().year, Date.today().month)
        fecha_desde = Date.today().strftime('%Y%m') + '01'
        fecha_hasta = Date.today().strftime('%Y%m') + str(end_date)
        for party in partys:
            data = self.get_arba_data(ws, party, fecha_desde, fecha_hasta)
            if data is not None:
                party.AlicuotaPercepcion = data.AlicuotaPercepcion
                party.AlicuotaRetencion =  data.AlicuotaRetencion
                party.save()


    @classmethod
    def conect_arba(cls):
        'conect_arba'
        Config = Pool().get('account.arba.configuration')
        config = Config(1)
        ws = iibb.IIBB()
        Party = Pool().get('party.party')
        ws.Usuario =  Party(Transaction().context.get('company')).vat_number
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
        cls.import_census(args)
        return True

    #@classmethod
    #def assign_try_scheduler(cls, args=None):
    #    '''
    #    This method is intended to be called from ir.cron
    #    args: warehouse ids [ids]
    #    '''
    #    pool = Pool()
    #    Cron = pool.get('ir.cron')
    #    ModelData = pool.get('ir.model.data')
    #    ShipmentOut = pool.get('stock.shipment.out')

    #    cron = Cron(ModelData.get_id('stock_shipment_out_autoassign',
    #            'cron_shipment_out_assign_try_scheduler'))
    #    from_date = cron.next_call - Cron.get_delta(cron)

    #    domain = [
    #        ('state', '=', 'waiting'),
    #        ('write_date', '>=', from_date),
    #        ]
    #    if args:
    #        domain.append(
    #            ('id', 'in', args),
    #            )

    #    shipments_assigned = []
    #    with Transaction().set_context(dblock=False):
    #        shipments = ShipmentOut.search(domain)

    #        logger.info(
    #            'Scheduler Try Assign. Total: %s' % (len(shipments)))

    #        while cls.stock_move_locked():
    #            sleep(0.1)
    #        for s in shipments:
    #            shipment = ShipmentOut(s.id)
    #            if ShipmentOut.assign_try([shipment]):
    #                shipments_assigned.append(shipment)
    #            Transaction().cursor.commit()

    #        logger.info(
    #            'End Scheduler Try Assign. Assigned: %s' % (len(shipments_assigned)))

