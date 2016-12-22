# -*- encoding: utf-8 -*-
from decimal import Decimal
import stdnum.ar.cuit as cuit
from trytond.model import fields, ModelView
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool
#from trytond.modules.account_invoice_ar.invoice import TIPO_COMPROBANTE
import logging
logger = logging.getLogger(__name__)

__all__ = ['WizardExportRN3811Start', 'WizardExportRN3811File',
    'WizardExportRN3811']


class ExportArbaMixin(object):

    def _format_string(self, text, length, fill=' ', align='<'):
        """
        Formats the string into a fixed length ASCII (iso-8859-1) record.

        Note:
            'Todos los campos alfanuméricos y alfabéticos se presentarán alineados
            a la izquierda y rellenos de blancos por la derecha, en mayúsculas sin
            caracteres especiales, y sin vocales acentuadas.
            Para los caracteres específicos del idioma se utilizará la codificación
            ISO-8859-1. De esta forma la letra “Ñ” tendrá el valor ASCII 209 (Hex.
            D1) y la “Ç”(cedilla mayúscula) el valor ASCII 199 (Hex. C7).'
        """
        #
        # Turn text (probably unicode) into an ASCII (iso-8859-1) string
        #
    #   if isinstance(text, (unicode)):
    #       ascii_string = text.encode('iso-8859-1', 'ignore')
    #   else:
    #       ascii_string = str(text or '')
        ascii_string = unicode(text).encode('ascii', 'replace')
        # Cut the string if it is too long
        if len(ascii_string) > length:
            ascii_string = ascii_string[:length]
        # Format the string
        # ascii_string = '{0:{1}{2}{3}s}'.format(ascii_string, fill, align, length)
        # for python >= 2.6
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
        #
        # Replace accents
        #
        replacements = [('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U')]
        for orig, repl in replacements:
            ascii_string.replace(orig, repl)
        # Sanity-check
        assert len(ascii_string) == length, \
            ("The formated string must match the given length")
        # Return string
        return ascii_string


    def _format_number(self, number, int_length, dec_length=0,
            include_sign=False):
        """
        Formats the number into a fixed length ASCII (iso-8859-1) record.
        Note:
            'Todos los campos numéricos se presentarán alineados a la derecha
            y rellenos a ceros por la izquierda sin signos y sin empaquetar.'
        """
        #
        # Separate the number parts
        # (-55.23 => int_part=55, dec_part=0.23, sign='-')
        #
        if number == '':
            number = 0
        _number = str(float(number))

        int_part = int(float(_number))
        dec_part = _number[_number.find('.') + 1:]
        sign = int_part < 0 and '-' or ''
        #
        # Format the string
        #
        ascii_string = ''
        if int_length > 0:
            ascii_string += '%.*d' % (int_length, abs(int_part))
        if dec_length > 0:
            ascii_string += '.' + str(dec_part) + (dec_length - 1 - len(str(dec_part))) * '0'
        if include_sign:
            ascii_string = sign + ascii_string[len(sign):]
        # Sanity-check
        assert len(ascii_string) == int_length + dec_length, \
            ("The formated string (%s) must match the given length" % (
                ascii_string,))
        # Return the string
        return ascii_string


    def _format_integer(self, value, length):
        res = ''.join([x for x in value if x in map(str, range(10))])[:length]
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
        if (vat_number.isdigit()
                and len(vat_number) == 11
                and cuit.is_valid(vat_number)):
            return True
        return False

    def taxes(self, invoice):
        """ Acumula los importes de las líneas de cada factura.
        Devuelve:
          diccionario
        """
        res = {}
        keys = ['iva', 'iibb', 'nacional', 'municipal', 'otros_tributos',
                'exentos']
        for k in keys:
            res[k] = Decimal('0.0')

        for line in invoice.taxes:
            tax = line.tax
            if 'iva' in tax.group.code.lower():
                res['iva'] += line.amount
            elif 'iibb' in tax.group.code.lower():
                res['iibb'] += line.amount
            elif 'nacional' in tax.group.code.lower():
                res['nacional'] += line.amount
            elif 'municipal' in tax.group.code.lower():
                res['municipal'] += line.amount
            elif 'otros_tributos' in tax.group.code.lower():
                res['otros_tributos'] += line.amount
            elif 'exentos' in tax.group.code.lower():
                res['exentos'] += line.base

        return res


class RN3811(ExportArbaMixin):
    """ Registro general de campos.

    Resolución Normativa Nº 038/11
    http://www.arba.gov.ar/Apartados/Agentes/InstructivoMarcoNormativo.asp
    """
    _EOL = '\r\n'

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


class LoteImportacion12(RN3811):
    """ Registro de campos que conforman una alícuota de un comprobante.

    Resolución Normativa Nº 038/11
    1.2. Percepciones Act. 7 método Percibido (quincenal)
    """

    def __init__(self):
        """ Declara los campos según el tipo de informe.
        """
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
        """ Devuelve lista de campos ordenados """
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


class WizardExportRN3811Start(ModelView):
    'Wizard Export RN3811 Start'
    __name__ = 'account.export.rn3811.start'
    start_date = fields.Date('Start date', required=True)
    end_date = fields.Date('End date', required=True)
    csv_format = fields.Boolean('CSV format',
        help='Check this box if you want export to csv format.')


class WizardExportRN3811File(ModelView):
    'Wizard Export RN3811 File'
    __name__ = 'account.export.rn3811.file'
    lote12_file = fields.Binary(u'1.2. Percepciones Act. 7 método Percibido' \
        '(quincenal)', readonly=True)


class WizardExportRN3811(Wizard):
    'Wizard Export RN3811'
    __name__ = 'account.export.rn3811'

    start = StateView('account.export.rn3811.start',
        'account_arba.export_rn3811_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Export', 'export', 'tryton-ok', default=True),
            ])
    export = StateTransition()
    result = StateView('account.export.rn3811.file',
        'account_arba.export_rn3811_file_view_form', [
            Button('Done', 'end', 'tryton-ok', default=True),
            ])

    def default_result(self, fields):
        lote12_file = self.result.lote12_file

        self.result.lote12_file = False

        return {
            'lote12_file': lote12_file,
            }

    def transition_export(self):
        """
        Action that exports the data into a formated text file.
        """
        pool = Pool()
        Invoice = pool.get('account.invoice')

        #invoice_type = {}
        #invoice_type['compras'] = ['in_invoice', 'in_credit_note']
        ventas = ['out_invoice', 'out_credit_note']

        domain = [
            ('state', 'in', ['posted', 'paid']),
            ('type', 'in', ventas),
            ('invoice_date', '>=', self.start.start_date),
            ('invoice_date', '<=', self.start.end_date),
        ]

        invoices = Invoice.search(domain, order=[
                ('number', 'ASC'),
                ('invoice_date', 'ASC'),
                ])

        # Add the records
        file_contents_lote12 = ''
        for invoice in invoices:
            aux_record, add_line = self._get_formated_record_lote12(invoice)
            if add_line:
                file_contents_lote12 += aux_record

        #
        # Generate the file and save as attachment
        #
        # tipo_archivo = self.start.csv_format and 'csv' or 'txt'
        # 'REGINFO_CV_%s_CBTE.%s'
        self.result.lote12_file = unicode(
            file_contents_lote12).encode('utf-8')
        return 'result'

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------


    def _get_formated_record_lote12(self, invoice):
        """ RN Nº 3811
        1.2. Percepciones Act. 7 método Percibido (quincenal)

        Devuelve tupla con dos posiciones con los siguientes valores:
         - Campos del Comprobante concatenados en una cadena de texto.
         - add_line (False or True)
        """
        Cbte = LoteImportacion12()
        tax_amounts = Cbte.taxes(invoice)
        if tax_amounts['iibb'] == Decimal('0'):
            logger.info(u'La factura %s no tiene impuestos con IIBB',
                invoice.number)
            return ('', False)

        logger.info(u'La factura %s tiene impuestos con IIBB',
            invoice.number)

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
            Cbte.cuit_contribuyente = ''.rjust(13)

        # -- Campo 2: Fecha de percepción. --
        # | Cantidad: 10 | Dato: Fecha |
        # | Formato: dd/mm/aaaa |
        Cbte.fecha_percepcion = (invoice.invoice_date
            and invoice.invoice_date.strftime('%d/%m/%Y') or None)
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
        Cbte.nro_sucursal = Cbte._format_number(invoice.number.split('-')[0],
               4, 0, include_sign=False)

        # -- Campo 6: Numero Emision. --
        # | Cantidad: 8 | Dato: Numerico |
        # | Formato: Mayor o igual a cero. Completar con ceros a la izq ' ' |
        Cbte.nro_emision = Cbte._format_number(invoice.number.split('-')[1],
               8, 0, include_sign=False)

        # -- Campo 7: Monto imponible. --
        # | Cantidad: 12,2 | Dato: Numerico |
        # | Formato: Seprador Decimal (,) o (.).
        # | Mayor a cero, o Excepto para Nota de crédito, donde el
        # | importe debe ser negativo y la base debe ser menor o igual a cero.
        # | Completar con ceros a la izquierda. En las notas de crédito el
        # | signo negativo ocupará la primera posición a la izq. |

        # -- Campo 8: Importe percepcion. --
        # | Cantidad: 11 | Dato: Numérico |
        if invoice.type == 'out_invoice':
            Cbte.monto_imponible = Cbte._format_number(invoice.untaxed_amount,
                   9, 3, include_sign=True)
            Cbte.importe_percepcion = Cbte._format_number(tax_amounts['iibb'],
                   8, 3, include_sign=True)
        elif invoice.type == 'out_credit_note':
            Cbte.monto_imponible = Cbte._format_number(invoice.untaxed_amount * -1,
                   9, 3, include_sign=True)
            Cbte.importe_percepcion = Cbte._format_number(tax_amounts['iibb'] * -1,
                   8, 3, include_sign=True)

        # -- Campo 9: Tipo de operacion
        # | Cantidad: 1 | Dato: Texto |
        Cbte.tipo_operacion = 'A'

        return (Cbte.a_text(self.start.csv_format), True)
