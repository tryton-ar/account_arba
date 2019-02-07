# The COPYRIGHT file at the top level of jhis repository contains the
# full copyright notices and license terms.

try:
    from trytond.modules.account_arba.tests.test_account_arba import suite
except ImportError:
    from .test_account_arba import suite

__all__ = ['suite']
