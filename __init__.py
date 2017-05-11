from trytond.pool import Pool

from . import account
from . import configuration
from . import party


def register():
    Pool.register(
        account.WizardExportRN3811Start,
        account.WizardExportRN3811File,
        configuration.Configuration,
        party.Party,
        module='account_arba', type_='model')
    Pool.register(
        account.WizardExportRN3811,
        module='account_arba', type_='wizard')
