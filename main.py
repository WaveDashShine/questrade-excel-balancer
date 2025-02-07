from enum import Enum
import pandas as pd
import os
import copy
from dataclasses import dataclass, fields

CASH_TO_INVEST = 17000
CURRENT_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
PATH_TO_EXCEL_FILE = os.path.join(CURRENT_DIR_PATH, "InvestmentSummary.xlsx")
POSITIONS_SHEET_NAME = "Positions"


class AssetClassification(Enum):
    STOCKS_USA_SMALL_CAP = 10
    STOCKS_USA_SP500 = 11
    STOCKS_EMERGING_MARKET = 12
    STOCKS_INTERNATIONAL = 13
    BONDS_CORP = 20
    BONDS_EMERGING_MARKET = 21
    REAL_ESTATE = 30


# roughly from random walk down wall street
# TODO: move to YAML
class PercentageTargets:
    STOCKS_USA_SMALL_CAP = 0.10
    STOCKS_USA_SP500 = 0.40
    STOCKS_EMERGING_MARKET = 0.05
    STOCKS_INTERNATIONAL = 0.25
    BONDS_CORP = 0.10
    BONDS_EMERGING_MARKET = 0.05
    REAL_ESTATE = 0.05


def get_percentage_target(classification: AssetClassification) -> float:
    match classification:
        case AssetClassification.STOCKS_USA_SMALL_CAP:
            return PercentageTargets.STOCKS_USA_SMALL_CAP
        case AssetClassification.STOCKS_USA_SP500:
            return PercentageTargets.STOCKS_USA_SP500
        case AssetClassification.STOCKS_EMERGING_MARKET:
            return PercentageTargets.STOCKS_EMERGING_MARKET
        case AssetClassification.STOCKS_INTERNATIONAL:
            return PercentageTargets.STOCKS_INTERNATIONAL
        case AssetClassification.BONDS_CORP:
            return PercentageTargets.BONDS_CORP
        case AssetClassification.BONDS_EMERGING_MARKET:
            return PercentageTargets.BONDS_EMERGING_MARKET
        case AssetClassification.REAL_ESTATE:
            return PercentageTargets.REAL_ESTATE
    raise RuntimeError(f"{classification} case does not match any percentage target")


class Asset:
    def __init__(self, symbol: str,
                 market_price: float,
                 quantity: int,
                 description: str = ""):
        self.symbol: str = symbol.upper()
        self.market_price: float = round(market_price, 2)
        self.quantity: int = quantity
        self.description = description
        self.classification: AssetClassification = self._get_classification()

    def get_value(self):
        return self.quantity * self.market_price

    def _get_classification(self) -> AssetClassification:
        if self.symbol in ["VNQ"]:
            return AssetClassification.REAL_ESTATE
        elif self.symbol in ["VWO"]:
            return AssetClassification.STOCKS_EMERGING_MARKET
        elif self.symbol in ["VCIT"]:
            return AssetClassification.BONDS_CORP
        elif self.symbol in ["VTWO"]:
            return AssetClassification.STOCKS_USA_SMALL_CAP
        elif self.symbol in ["VXUS"]:
            return AssetClassification.STOCKS_INTERNATIONAL
        elif self.symbol in ["VOO"]:
            return AssetClassification.STOCKS_USA_SP500
        elif self.symbol in ["VWOB"]:
            return AssetClassification.BONDS_EMERGING_MARKET

    def print(self, description: bool = True, classification: bool = False):
        print(self.symbol, self.quantity, f"@ ${self.market_price}", "\n" if description or classification else "",
              self.description if description else "", self.classification if classification else "")


class PortFolio:
    def __init__(self, assets: list[Asset]):
        self.assets: list = assets
        self.total_value = 0
        self.update_total_value()

    def update_total_value(self):
        self.total_value = sum([asset.get_value() for asset in self.assets])

    def get_percent_classification(self, classification: AssetClassification) -> float:
        # TODO: if runtime is bad, memoize this with some variable to keep track of outdatedness
        asset_value = sum([asset.get_value() for asset in self.assets if asset.classification == classification])
        return asset_value / self.total_value

    def get_difference_from_target(self) -> float:
        difference: float = 0
        for asset in self.assets:
            classification = asset.classification
            percent_classification = self.get_percent_classification(classification=classification)
            percent_target = get_percentage_target(classification=classification)
            difference += abs(percent_classification - percent_target)

        return round(difference, 3)

    def buy_symbol(self, symbol: str, shares: int):
        if matching_asset := self.get_asset(symbol=symbol):
            matching_asset.quantity += shares
            self.update_total_value()
        else:
            raise RuntimeError(f"No owned shares: {symbol}")

    def get_asset(self, symbol) -> Asset | None:
        if matching_asset_list := [asset for asset in self.assets if asset.symbol == symbol]:
            return matching_asset_list[0]
        else:
            return None

    def print_assets(self):
        for asset in self.assets:
            asset.print()
            print(self.get_percent_classification(asset.classification), "\n")


def parse_positions_to_dict(positions) -> dict:
    positions_dict = {}
    for position in positions.iterrows():
        row = position[1]
        column_names = row.keys()
        asset_dict = {}
        for index in range(len(column_names)):
            value = position[1][index]
            column_name = column_names[index]
            asset_dict[column_name] = value
        symbol = str(asset_dict.get("Equity Symbol")).upper()
        if symbol.startswith("V"):  # only care for vanguard ETFs
            positions_dict[asset_dict.get("Equity Symbol")] = asset_dict
    return positions_dict


def generate_portfolio(positions_dict: dict) -> PortFolio:
    asset_list: list[Asset] = []
    for key, asset_dict in positions_dict.items():
        asset = Asset(symbol=asset_dict.get("Equity Symbol"),
                      market_price=asset_dict.get("Market Price"),
                      quantity=asset_dict.get("Quantity"),
                      description=asset_dict.get("Equity Description"))
        asset_list.append(asset)
    return PortFolio(assets=asset_list)


def rebalance_portfolio(portfolio: PortFolio) -> PortFolio:
    cash = CASH_TO_INVEST
    working_portfolio = copy.deepcopy(portfolio)
    previous_portfolio = working_portfolio
    symbol_list = [asset.symbol for asset in portfolio.assets]
    index = 0
    while cash > 0:
        print(f"{index}--------")
        diff_asset_dict = {}
        for symbol in symbol_list:
            new_assets = copy.deepcopy(working_portfolio.assets)
            new_portfolio = PortFolio(assets=new_assets)
            new_portfolio.buy_symbol(symbol=symbol, shares=1)
            diff_key = str(new_portfolio.get_difference_from_target())
            if diff_asset_dict.get(diff_key):
                new_portfolio.buy_symbol(symbol=symbol, shares=1)
            diff_asset_dict[diff_key] = new_portfolio

        min_diff = min(diff_asset_dict.keys())
        print(min_diff)
        previous_portfolio = working_portfolio
        working_portfolio = diff_asset_dict.get(min_diff)
        cost_to_buy = round(working_portfolio.total_value - previous_portfolio.total_value, 2)
        cash = cash - cost_to_buy
        print(f"${cash}")
        index += 1

    return previous_portfolio  # do not overspend


def get_difference_portfolio(starting_portfolio: PortFolio, new_portfolio: PortFolio) -> PortFolio:
    newly_bought_assets = []
    for asset in new_portfolio.assets:
        starting_asset = starting_portfolio.get_asset(symbol=asset.symbol)
        if starting_asset:
            bought_quantity = asset.quantity - starting_asset.quantity
            if bought_quantity > 0:
                newly_bought_asset: Asset = Asset(symbol=asset.symbol,
                                                  market_price=asset.market_price,
                                                  quantity=bought_quantity,
                                                  description=asset.description)
                newly_bought_assets.append(newly_bought_asset)
        else:
            newly_bought_assets.append(asset)
    return PortFolio(assets=newly_bought_assets)


def print_summary(starting_portfolio: PortFolio, new_portfolio: PortFolio):
    print("================================================")
    new_portfolio.print_assets()
    print("================================================")
    print(f"Final deviation from target: {new_portfolio.get_difference_from_target()}")
    difference_portfolio = get_difference_portfolio(starting_portfolio=starting_portfolio, new_portfolio=new_portfolio)
    print(f"Total Cost: ${difference_portfolio.total_value}")
    for asset in difference_portfolio.assets:
        asset.print(description=False)


def main():
    print(PATH_TO_EXCEL_FILE)
    with pd.ExcelFile(PATH_TO_EXCEL_FILE) as xls:
        positions = pd.read_excel(xls, POSITIONS_SHEET_NAME)
        positions_dict = parse_positions_to_dict(positions=positions)

    starting_portfolio = generate_portfolio(positions_dict=positions_dict)
    new_portfolio = rebalance_portfolio(portfolio=starting_portfolio)
    print_summary(starting_portfolio=starting_portfolio, new_portfolio=new_portfolio)


if __name__ == '__main__':
    main()
