from trytond.pool import Pool

from . import account
from . import configuration
from . import party
from . import invoice


def register():
    Pool.register(
        account.WizardExportRN3811Start,
        account.WizardExportRN3811File,
        configuration.Configuration,
        configuration.ConfigurationPassword,
        configuration.ConfigurationCert,
        party.Party,
        invoice.Invoice,
        module='account_arba', type_='model')
    Pool.register(
        account.WizardExportRN3811,
        module='account_arba', type_='wizard')
