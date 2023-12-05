# -*- coding: utf-8 -*-
# This file is part of the account_arba module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
import stdnum.ar.cuit as cuit
from io import BytesIO
import zipfile

from trytond.model import fields, ModelView
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool
from trytond.transaction import Transaction

import logging
logger = logging.getLogger(__name__)


class ARBARN3811(object):
    """ Registro general de campos.

    Resolución Normativa Nº 038/11
    http://www.arba.gov.ar/Apartados/Agentes/InstructivoMarcoNormativo.asp
    """
    _EOL = '\r\n'

    def _format_string(self, text, length, fill=' ', align='<'):
        """
        Formats the string into a fixed length ASCII (iso-8859-1) record.

        Note:
            'Todos los campos alfanuméricos y alfabéticos se presentarán
            alineados a la izquierda y rellenos de blancos por la derecha,
            en mayúsculas sin caracteres especiales, y sin vocales acentuadas.
            Para los caracteres específicos del idioma se utilizará la
            codificación ISO-8859-1. De esta forma la letra “Ñ”
            tendrá el valor ASCII 209 (Hex.
            D1) y la “Ç”(cedilla mayúscula) el valor ASCII 199 (Hex. C7).'
        """

        # Turn text (probably unicode) into an ASCII (iso-8859-1) string
        ascii_string = str(text).encode('ascii', 'replace')

        # Cut the string if it is too long
        if len(ascii_string) > length:
            ascii_string = ascii_string[:length]

        # Format the string
        if align == '<':
            ascii_string = str(ascii_string) + (
                length - len(str(ascii_string))) * fill
        elif align == '>':
            ascii_string = (length - len(str(ascii_string))) * fill + str(
                ascii_string)
        else:
            assert False, ('Wrong aling option. It should be < or >')

        # Turn into uppercase
        ascii_string = ascii_string.upper()

        # Replace accents
        replacements = [('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'),
            ('Ú', 'U')]
        for orig, repl in replacements:
            ascii_string.replace(orig, repl)

        # Sanity-check
        assert len(ascii_string) == length, \
            ("The formated string must match the given length")

        return ascii_string

    def _format_number(self, number, int_length, dec_length=0,
            include_sign=False):
        """
        Formats the number into a fixed length ASCII (iso-8859-1) record.
        Note:
            'Todos los campos numéricos se presentarán alineados a la derecha
            y rellenos a ceros por la izquierda sin signos y sin empaquetar.'
        """

        # Separate the number parts
        # (-55.23 => int_part=55, dec_part=0.23, sign='-')
        if number == '':
            number = 0
        _number = str(float(number))

        int_part = int(float(_number))
        dec_part = _number[_number.find('.') + 1:]
        sign = int_part < 0 and '-' or ''

        # Format the string
        ascii_string = ''
        if int_length > 0:
            ascii_string += '%.*d' % (int_length, abs(int_part))
        if dec_length > 0:
            ascii_string += '.' + str(dec_part) \
                + (dec_length - 1 - len(str(dec_part))) * '0'
        if include_sign:
            ascii_string = sign + ascii_string[len(sign):]

        # Sanity-check
        assert len(ascii_string) == int_length + dec_length, \
            ("The formated string (%s) must match the given length" % (
                ascii_string,))

        return ascii_string

    def _format_integer(self, value, length):
        res = ''.join([x for x in value
            if x in list(map(str, list(range(10))))])[:length]
        res = str(res) + (length - len(str(res))) * ' '  # fill
        return res

    def _format_vat_number(self, vat_number, check=True):
        """ Formato 99-99999999-9 """
        if not vat_number:
            return False
        if check and not self._check_vat_number(vat_number):
            return False
        vat_number = '-'.join([vat_number[:2], vat_number[2:-1],
            vat_number[-1]])
        return vat_number

    def _check_vat_number(self, vat_number):
        """ Valida CUIT corto (sin separador) para Argentina. """
        if (vat_number.isdigit() and
                len(vat_number) == 11 and
                cuit.is_valid(vat_number)):
            return True
        return False

    def get_tax_amount(self, invoice, tax):
        res = Decimal('0.0')
        for line in invoice.taxes:
            if line.tax == tax:
                res += line.amount
        return res

    def ordered_fields(self):
        """ Devuelve lista de campos ordenados """
        return []

    def a_text(self, csv_format=False):
        """ Concatena los valores de los campos de la clase y los
        devuelve en una cadena de texto.
        """
        fields = self.ordered_fields()
        fields = [x for x in fields if x != '']
        separator = csv_format and ';' or ''
        text = separator.join(fields) + self._EOL
        return text


class LoteImportacion12(ARBARN3811):
    """ Registro de campos que conforman una alícuota de un comprobante.

    Resolución Normativa Nº 038/11
    1.2. Percepciones Act. 7 método Percibido (quincenal)
    """

    def __init__(self):
        super(LoteImportacion12, self).__init__()
        # Campo 1: Cuit Contribuyente percibido.
        self.cuit_contribuyente = None
        # Campo 2: Fecha percepción.
        self.fecha_percepcion = None
        # Campo 3: Tipo de comprobante.
        self.tipo_comprobante = None
        # Campo 4: Letra de comprobante.
        self.letra_comprobante = None
        # Campo 5: Número de sucursal.
        self.nro_sucursal = None
        # Campo 6: Número de emisión.
        self.nro_emision = None
        # Campo 7: Monto imponible.
        self.monto_imponible = None
        # Campo 8: Importe Percepcion.
        self.importe_percepcion = None
        # Campo 9: Fecha de emisión.
        self.fecha_emision = None
        # Campo 10: Tipo operación.
        self.tipo_operacion = None

    def ordered_fields(self):
        return [
            self.cuit_contribuyente,
            self.fecha_percepcion,
            self.tipo_comprobante,
            self.letra_comprobante,
            self.nro_sucursal,
            self.nro_emision,
            self.monto_imponible,
            self.importe_percepcion,
            self.fecha_emision,
            self.tipo_operacion,
            ]


class LoteImportacion19(ARBARN3811):
    """ Registro de campos que conforman una alícuota de un comprobante.

    Resolución Normativa Nº 038/11
    1.9. Retenciones Act. 6 de Bancos
    """

    def __init__(self):
        super(LoteImportacion19, self).__init__()
        # Campo 1: Cuit Contribuyente retenido.
        self.cuit_contribuyente = None
        # Campo 2: Monto imponible.
        self.monto_imponible = None
        # Campo 3: Importe Retención.
        self.importe_retencion = None
        # Campo 4: Fecha Retención.
        self.fecha_retencion = None
        # Campo 5: Tipo operación.
        self.tipo_operacion = None

    def ordered_fields(self):
        return [
            self.cuit_contribuyente,
            self.monto_imponible,
            self.importe_retencion,
            self.fecha_retencion,
            self.tipo_operacion,
            ]


class ExportARBARN3811Start(ModelView):
    'Retenciones y Percepciones de Ingresos Brutos (ARBA RN Nº 38/11)'
    __name__ = 'arba.rn3811.start'

    start_date = fields.Date('Start date', required=True)
    end_date = fields.Date('End date', required=True)
    csv_format = fields.Boolean('CSV format',
        help='Check this box if you want export to csv format.')


class ExportARBARN3811Result(ModelView):
    'Retenciones y Percepciones de Ingresos Brutos (ARBA RN Nº 38/11)'
    __name__ = 'arba.rn3811.result'

    lote12_file = fields.Binary(
        '1.2. Percepciones Act. 7 método Percibido (quincenal)',
        filename='lote12_filename', readonly=True)
    lote12_filename = fields.Char('Name')
    lote19_file = fields.Binary(
        '1.9. Retenciones Act. 6 de Bancos',
        filename='lote19_filename', readonly=True)
    lote19_filename = fields.Char('Name')
    message = fields.Text('Message', readonly=True)


class ExportARBARN3811(Wizard):
    'Retenciones y Percepciones de Ingresos Brutos (ARBA RN Nº 38/11)'
    __name__ = 'arba.rn3811'

    start = StateView('arba.rn3811.start',
        'account_arba.arba_rn3811_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Export', 'export', 'tryton-forward', default=True),
            ])
    export = StateTransition()
    result = StateView('arba.rn3811.result',
        'account_arba.arba_rn3811_result_view_form', [
            Button('Close', 'end', 'tryton-close', default=True),
            ])

    def transition_export(self):
        """
        Action that exports the data into a formated text file.
        """
        pool = Pool()
        Company = pool.get('company.company')
        Invoice = pool.get('account.invoice')
        TaxWithholdingSubmitted = pool.get('account.retencion.efectuada')

        company = Company(Transaction().context['company'])
        arba_regimen_percepcion = company.arba_regimen_percepcion
        arba_regimen_retencion = company.arba_regimen_retencion

        self.result.message = ''

        # 1.2. Percepciones Act. 7 método Percibido (quincenal)
        file_contents_lote12 = ''
        invoices = Invoice.search([
            ('type', '=', 'out'),
            ['OR', ('state', 'in', ['posted', 'paid']),
                [('state', '=', 'cancelled'), ('number', '!=', None)]],
            ('move.date', '>=', self.start.start_date),
            ('move.date', '<=', self.start.end_date),
            #('pos.pos_do_not_report', '=', False),
            ], order=[
            ('number', 'ASC'),
            ('invoice_date', 'ASC'),
            ])
        for invoice in invoices:
            aux_record, add_line, message = self._get_formated_record_lote12(
                invoice, arba_regimen_percepcion)
            if add_line:
                file_contents_lote12 += aux_record
            if message:
                self.result.message += message + '\n'
        self.result.lote12_file = str(
            file_contents_lote12).encode('utf-8')

        # 1.9. Retenciones Act. 6 de Bancos
        file_contents_lote19 = ''
        retenciones = TaxWithholdingSubmitted.search([
            ('tax', '=', arba_regimen_retencion),
            ('date', '>=', self.start.start_date),
            ('date', '<=', self.start.end_date),
            ('state', '=', 'issued'),
            ], order=[
            ('date', 'ASC'),
            ('name', 'ASC'),
            ])
        for retencion in retenciones:
            aux_record, add_line, message = self._get_formated_record_lote19(
                retencion)
            if add_line:
                file_contents_lote19 += aux_record
            if message:
                self.result.message += message + '\n'
        self.result.lote19_file = str(
            file_contents_lote19).encode('utf-8')

        return 'result'

    def _get_formated_record_lote12(self, invoice, arba_regimen_percepcion):
        """ RN Nº 3811
        1.2. Percepciones Act. 7 método Percibido (quincenal)

        Devuelve tupla con dos posiciones con los siguientes valores:
         - Campos del Comprobante concatenados en una cadena de texto.
         - add_line (False or True)
        """
        Cbte = LoteImportacion12()
        tax_amount = Cbte.get_tax_amount(invoice, arba_regimen_percepcion)
        if tax_amount == Decimal('0'):
            logger.info('La factura %s no tiene percepción de IIBB BSAS',
                invoice.number)
            return ('', False, '')

        # -- Cálculo auxiliar para Campo 2, 3, 4 --
        ref = invoice.reference or invoice.number
        ref = ref.strip().upper()
        comprobante = {}

        comprobante['letter'] = invoice.invoice_type.rec_name[-1:]
        comprobante['pos'] = ref.split('-')[0] if '-' in ref else ''
        comprobante['number'] = ref.split('-')[1] if '-' in ref else ref

        # -- Campo 1: CUIT contribuyente. --
        # | Cantidad: 13 | Dato: Alfanumérico |
        cuitOk = Cbte._format_vat_number(invoice.party.vat_number)
        if cuitOk:
            Cbte.cuit_contribuyente = cuitOk
        else:
            return ('', False, 'ERROR: La factura %s de la entidad %s no '
                'tiene CUIT. Fue quitada del listado.'
                % (invoice.number, invoice.party.name))

        # -- Campo 2: Fecha de percepción. --
        # | Cantidad: 10 | Dato: Fecha |
        # | Formato: dd/mm/aaaa |
        Cbte.fecha_percepcion = (invoice.invoice_date and
            invoice.invoice_date.strftime('%d/%m/%Y') or None)
        assert Cbte.fecha_percepcion, (
            'Falta "Fecha Comprobante"! (Campo 2)')
        Cbte.fecha_emision = Cbte.fecha_percepcion

        # -- Campo 3: Tipo de Comprobante. --
        # | Cantidad: 1 | Dato: Texto |
        # | Formato: Valores F=Factura, R=Recibo,
        # | C=Nota Crédito, D=Nota Debito|
        tipo_comprobante = invoice.invoice_type.rec_name[0]
        if tipo_comprobante == 'N':
            tipo_comprobante = invoice.invoice_type.rec_name[8:9]
        Cbte.tipo_comprobante = tipo_comprobante

        # -- Campo 4: Letra de Comprobante. --
        # | Cantidad: 1 | Dato: Texto |
        # | Formato: Valores A, B, C o ' ' |
        Cbte.letra_comprobante = invoice.invoice_type.rec_name[-1]

        # -- Campo 5: Numero Sucursal. --
        # | Cantidad: 4 | Dato: Numerico |
        # | Formato: Mayor o igual a cero. Completar con ceros a la izq ' ' |
        Cbte.nro_sucursal = Cbte._format_number(
            invoice.number.split('-')[0], 4, 0, include_sign=False)

        # -- Campo 6: Numero Emision. --
        # | Cantidad: 8 | Dato: Numerico |
        # | Formato: Mayor o igual a cero. Completar con ceros a la izq ' ' |
        Cbte.nro_emision = Cbte._format_number(
            invoice.number.split('-')[1], 8, 0, include_sign=False)

        # -- Campo 7: Monto imponible. --
        # | Cantidad: 12,2 | Dato: Numerico |
        # | Formato: Seprador Decimal (,) o (.).
        # | Mayor a cero, o Excepto para Nota de crédito, donde el
        # | importe debe ser negativo y la base debe ser menor o igual a cero.
        # | Completar con ceros a la izquierda. En las notas de crédito el
        # | signo negativo ocupará la primera posición a la izq. |

        # -- Campo 8: Importe percepcion. --
        # | Cantidad: 11 | Dato: Numérico |
        if invoice.type == 'out':
            Cbte.monto_imponible = Cbte._format_number(
                invoice.untaxed_amount, 9, 3, include_sign=True)
            Cbte.importe_percepcion = Cbte._format_number(
                tax_amount, 8, 3, include_sign=True)
        #elif invoice.type == 'out_credit_note':
        #    Cbte.monto_imponible = Cbte._format_number(
        #        invoice.untaxed_amount * -1,9, 3, include_sign=True)
        #    Cbte.importe_percepcion = Cbte._format_number(
        #        tax_amount * -1, 8, 3, include_sign=True)

        # -- Campo 9: Tipo de operacion
        # | Cantidad: 1 | Dato: Texto |
        Cbte.tipo_operacion = 'A'

        return (Cbte.a_text(self.start.csv_format), True, '')

    def _get_formated_record_lote19(self, retencion):
        """ RN Nº 3811
        1.9. Retenciones Act. 6 de Bancos

        Devuelve tupla con dos posiciones con los siguientes valores:
         - Campos del Comprobante concatenados en una cadena de texto.
         - add_line (False or True)
        """
        Cbte = LoteImportacion19()

        # -- Campo 1: Cuit Contribuyente retenido. --
        # | Cantidad: 13 | Dato: Alfanumérico |
        cuitOk = Cbte._format_vat_number(retencion.party.vat_number)
        if cuitOk:
            Cbte.cuit_contribuyente = cuitOk
        else:
            return ('', False, 'ERROR: La retención %s de la entidad %s no '
                'tiene CUIT. Fue quitada del listado.'
                % (retencion.name, retencion.party.name))

        # -- Campo 2: Monto imponible. --
        # | Cantidad: 12,2 | Dato: Numerico |
        # | Formato: Seprador Decimal (,) o (.).
        # | Siempre mayor a cero.
        # | Completar con ceros a la izquierda.
        if retencion.payment_amount:
            Cbte.monto_imponible = Cbte._format_number(
                retencion.payment_amount, 9, 3, include_sign=True)
        else:
            return ('', False, 'ERROR: La retención %s de la entidad %s no '
                'tiene Monto imponible. Fue quitada del listado.'
                % (retencion.name, retencion.party.name))

        # -- Campo 3: Importe Retención. --
        # | Cantidad: 11 | Dato: Numérico |
        Cbte.importe_retencion = Cbte._format_number(
            retencion.amount, 8, 3, include_sign=True)

        # -- Campo 4: Fecha Retención. --
        # | Cantidad: 10 | Dato: Fecha |
        # | Formato: dd/mm/aaaa |
        Cbte.fecha_retencion = retencion.date.strftime('%d/%m/%Y')

        # -- Campo 5: Tipo operación.
        # | Cantidad: 1 | Dato: Texto |
        Cbte.tipo_operacion = 'A'

        return (Cbte.a_text(self.start.csv_format), True, '')

    def default_result(self, fields):
        pool = Pool()
        Company = pool.get('company.company')

        company = Company(Transaction().context['company'])
        company_vat_number = company.party.vat_number
        period = self.start.start_date.strftime('%Y%m') + '0'
        ext = 'CSV' if self.start.csv_format else 'TXT'

        lote12_filename = 'AR-%s-%s-%s-%s' % (
            company_vat_number, period, '7', period)
        lote12_content = BytesIO()
        with zipfile.ZipFile(lote12_content, 'w') as lote12_content_zip:
            lote12_content_zip.writestr('%s.%s' % (lote12_filename, ext),
                self.result.lote12_file)
        lote12_content = lote12_content.getvalue()
        lote12_file = (bytearray(lote12_content) if bytes == str
            else bytes(lote12_content))

        lote19_filename = 'AR-%s-%s-%s-%s' % (
            company_vat_number, period, '6', period)
        lote19_content = BytesIO()
        with zipfile.ZipFile(lote19_content, 'w') as lote19_content_zip:
            lote19_content_zip.writestr('%s.%s' % (lote19_filename, ext),
                self.result.lote19_file)
        lote19_content = lote19_content.getvalue()
        lote19_file = (bytearray(lote19_content) if bytes == str
            else bytes(lote19_content))

        message = self.result.message

        self.result.lote12_file = None
        self.result.lote19_file = None
        self.result.message = None

        return {
            'lote12_file': lote12_file,
            'lote12_filename': '%s.ZIP' % lote12_filename,
            'lote19_file': lote19_file,
            'lote19_filename': '%ss.ZIP' % lote19_filename,
            'message': message,
            }
