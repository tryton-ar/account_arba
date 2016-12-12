from trytond.pool import Pool

from . import account


def register():
    Pool.register(
        account.WizardExportRN3811Start,
        account.WizardExportRN3811File,
        module='account_arba', type_='model')
    Pool.register(
        account.WizardExportRN3811,
        module='account_arba', type_='wizard')
