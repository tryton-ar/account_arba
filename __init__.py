# This file is part of the account_arba module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import company
from . import party
from . import arba


def register():
    Pool.register(
        company.Company,
        party.Party,
        party.Cron,
        arba.ExportARBARN3811Start,
        arba.ExportARBARN3811Result,
        module='account_arba', type_='model')
    Pool.register(
        arba.ExportARBARN3811,
        module='account_arba', type_='wizard')
