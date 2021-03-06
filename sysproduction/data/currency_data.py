from sysdata.private_config import get_private_then_default_key_value
from sysproduction.data.get_data import dataBlob
from syscore.objects import  arg_not_supplied
from sysdata.fx.spotfx import currencyValue

class currencyData(object):
    """
    Translate between currency values
    """
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("arcticFxPricesData")
        self.data = data

    def total_of_list_of_currency_values_in_base(self, list_of_currency_values):
        value_in_base = [self.currency_value_in_base(currency_value) for currency_value in list_of_currency_values]

        return sum(value_in_base)

    def currency_value_in_base(self, currency_value: currencyValue):
        value = currency_value.value
        fx_rate = self.get_last_fx_rate_to_base(currency_value.currency)
        base_value = value * fx_rate

        return base_value

    def get_last_fx_rate_to_base(self, currency:str):
        """

        :param currency: eg GBP
        :return: eg fx rate for GBPUSD if base was USD
        """
        base = self.get_base_currency()
        currency_pair = currency+base

        return self.get_last_fx_rate_for_pair(currency_pair)

    def get_base_currency(self):
        """

        :return: eg USD
        """
        return get_private_then_default_key_value('base_currency')

    def get_last_fx_rate_for_pair(self, currency_pair:str ):
        """

        :param currency_pair: eg AUDUSD

        :return: float
        """
        fx_data = self.data.arctic_fx_prices.get_fx_prices(currency_pair)
        return fx_data.values[-1]

