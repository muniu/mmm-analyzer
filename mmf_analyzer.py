#!/usr/bin/env python3

import datetime
from typing import Dict
import calendar
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class Fund:
    """
    Represents a Money Market Fund with its key attributes and validation.

    A Fund instance stores the essential characteristics of a money market fund
    including its name, interest rate, management fee, and minimum investment
    requirement. All numerical values are stored as Decimal for precise calculations.
    """

    name: str
    rate: Decimal
    mgt_fee: Decimal
    minimum_investment: Decimal

    def __post_init__(self):
        """Validate fund data after initialization"""
        if not isinstance(self.name, str) or not self.name:
            raise TypeError("Fund name must be a non-empty string")
        if not self.rate or not isinstance(self.rate, Decimal) or self.rate <= 0:
            raise ValueError(f"Invalid rate for fund {self.name}")
        if (
            not self.mgt_fee
            or not isinstance(self.mgt_fee, Decimal)
            or self.mgt_fee < 0
        ):
            raise ValueError(f"Invalid management fee for fund {self.name}")
        if (
            not self.minimum_investment
            or not isinstance(self.minimum_investment, Decimal)
            or self.minimum_investment < 0
        ):
            raise ValueError(f"Invalid minimum investment for fund {self.name}")


class MMFAnalyzer:
    """
    Money Market Fund (MMF) Analysis Tool for Kenyan investment funds.
    Provides comprehensive analysis of MMF investments, calculating returns
    with daily interest compounding, monthly contributions, management fees,
    and withholding tax considerations. Uses actual calendar days for precise
    calculations.
    """

    def __init__(self, data_file: str = "funds_data.json"):
        self.funds = self._load_funds(data_file)

    def _load_funds(self, data_file: str) -> list[Fund]:
        """Load fund data from JSON file with fallback to default data"""
        try:
            path = Path(data_file)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [
                        Fund(
                            name=fund["name"],
                            rate=Decimal(str(fund["rate"])),
                            mgt_fee=Decimal(str(fund["mgt_fee"])),
                            minimum_investment=Decimal(str(fund["minimum_investment"])),
                        )
                        for fund in data["funds"]
                    ]
            else:
                print(f"Data file {data_file} not found, using default data...")
                return self._get_default_funds()
        except Exception as e:
            print(f"Error loading fund data: {str(e)}")
            print("Using default fund data...")
            return self._get_default_funds()

    def _get_default_funds(self) -> list[Fund]:
        """Return default hardcoded funds if file loading fails"""
        return [
            Fund(
                name="My first example fund",
                rate=Decimal("16.91"),
                mgt_fee=Decimal("0.85"),
                minimum_investment=Decimal("1000"),
            ),
            Fund(
                name="My second example fund",
                rate=Decimal("16.86"),
                mgt_fee=Decimal("0.90"),
                minimum_investment=Decimal("100"),
            ),
        ]

    def validate_parameters(self, params: Dict) -> None:
        """Validate input parameters"""
        # Basic parameter validation
        if params["initial_capital"] <= 0:
            raise ValueError("Initial capital must be positive")
        if params["monthly_contribution"] < 0:
            raise ValueError("Monthly contribution cannot be negative")
        if params["investment_period"] <= 0:
            raise ValueError("Investment period must be positive")
        if not 0 <= params["withholding_tax"] <= 100:
            raise ValueError("Withholding tax must be between 0 and 100")

        # Minimum investment validation
        initial_capital = Decimal(str(params["initial_capital"]))
        available_funds = [
            fund for fund in self.funds if fund.minimum_investment <= initial_capital
        ]

        if not available_funds:
            # Find the lowest minimum investment requirement
            min_investment = min(fund.minimum_investment for fund in self.funds)
            raise ValueError(
                f"Initial capital of KES {initial_capital:,.2f} is below the minimum investment "
                f"requirement. Lowest available option is KES {min_investment:,.2f} "
                f"({next(f.name for f in self.funds if f.minimum_investment == min_investment)})"
            )

        # Optional: Add warning for funds that will be excluded
        excluded_funds = [
            fund for fund in self.funds if fund.minimum_investment > initial_capital
        ]
        if excluded_funds:
            print("\nNote: The following funds require higher minimum investment:")
            for fund in excluded_funds:
                print(f"- {fund.name}: KES {fund.minimum_investment:,.2f}")

    def add_months(self, date: datetime.date, months: int) -> datetime.date:
        """Add months to a date, handling year changes"""
        month = date.month - 1 + months
        year = date.year + month // 12
        month = month % 12 + 1
        day = min(date.day, calendar.monthrange(year, month)[1])
        return datetime.date(year, month, day)

    def get_month_days(self, date: datetime.date) -> int:
        """Get the number of days in a given month"""
        return calendar.monthrange(date.year, date.month)[1]

    def get_month_name(self, date: datetime.date) -> str:
        """Get the month name and year"""
        return date.strftime("%B %Y")

    def calculate_daily_interest(
        self, balance: Decimal, daily_rate: Decimal, withholding_tax: Decimal
    ) -> Decimal:
        """Calculate daily interest with tax"""
        daily_interest = balance * daily_rate
        return daily_interest * (1 - withholding_tax / 100)

    def calculate_management_fee(
        self, opening_balance: Decimal, closing_balance: Decimal, mgt_fee_rate: Decimal
    ) -> Decimal:
        """Calculate monthly management fee based on average balance"""
        average_balance = (opening_balance + closing_balance) / 2
        monthly_fee = (average_balance * mgt_fee_rate / 100) / 12
        return monthly_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_monthly_returns(
        self,
        fund: Fund,
        params: Dict,
        current_date: datetime.date,
        month: int,
        starting_balance: Decimal,
    ) -> Dict:
        """Calculate returns for a single month"""
        days_in_month = self.get_month_days(current_date)
        daily_rate = Decimal(str(fund.rate)) / 365 / 100
        withholding_tax = Decimal(str(params["withholding_tax"]))

        # Track opening balance for fee calculation
        opening_balance = starting_balance

        # Add monthly contribution at start of month (except first month)
        balance = starting_balance
        if month > 0:
            balance += Decimal(str(params["monthly_contribution"]))

        # Initialize accumulators
        month_interest = Decimal("0")
        daily_balances = []

        # Calculate daily interest
        for day in range(days_in_month):
            daily_interest = self.calculate_daily_interest(
                balance, daily_rate, withholding_tax
            )
            balance += daily_interest
            month_interest += daily_interest
            daily_balances.append(
                {
                    "date": current_date + datetime.timedelta(days=day),
                    "balance": balance,
                    "interest": daily_interest,
                }
            )

        # Calculate management fee if enabled
        monthly_fee = Decimal("0")
        if params["include_fees"]:
            monthly_fee = self.calculate_management_fee(
                opening_balance, balance, fund.mgt_fee
            )
            balance -= monthly_fee

        return {
            "balance": balance,
            "interest": month_interest,
            "fee": monthly_fee,
            "daily_balances": daily_balances,
        }

    def calculate_returns(self, fund: Fund, params: Dict) -> Dict:
        """Calculate returns with improved accuracy and timing"""
        # Convert numerical values to Decimal for precise calculations
        balance = Decimal(str(params["initial_capital"]))
        total_interest = Decimal("0")
        total_fees = Decimal("0")
        total_contribution = Decimal(str(params["initial_capital"]))

        current_date = params["start_date"]
        monthly_balances = [(self.get_month_name(current_date), balance)]
        daily_details = []

        try:
            # Calculate returns for each month
            for month in range(int(params["investment_period"])):
                monthly_result = self.calculate_monthly_returns(
                    fund, params, current_date, month, balance
                )

                # Update running totals
                balance = monthly_result["balance"]
                total_interest += monthly_result["interest"]
                total_fees += monthly_result["fee"]

                if month > 0:
                    total_contribution += Decimal(str(params["monthly_contribution"]))

                # Store monthly balance
                current_date = self.add_months(current_date, 1)
                monthly_balances.append((self.get_month_name(current_date), balance))

                # Extend daily details
                daily_details.extend(monthly_result["daily_balances"])

            # Calculate net return
            net_return = (
                (balance - total_contribution) / total_contribution * 100
                if total_contribution
                else Decimal("0")
            )

            return {
                "final_balance": float(balance),
                "total_interest": float(total_interest),
                "total_fees": float(total_fees),
                "total_contribution": float(total_contribution),
                "monthly_balances": monthly_balances,
                "daily_details": daily_details,
                "net_return_percent": float(net_return),
            }

        except Exception as e:
            raise ValueError(
                f"Error calculating returns for {fund.name}: {str(e)}"
            ) from e

    def get_user_input(self) -> Dict:
        """Get investment parameters from user with improved validation"""
        print("\n=== Money Market Fund Analysis Tool ===\n")

        params = {}
        numerical_inputs = [
            ("initial_capital", "Initial Capital (KES)", 100),
            ("monthly_contribution", "Monthly Contribution (KES)", 0),
            ("investment_period", "Investment Period (months)", 1),
            ("withholding_tax", "Withholding Tax (%)", 0, 100),
        ]

        for param, prompt, *limits in numerical_inputs:
            while True:
                try:
                    value = float(
                        input(f"{prompt}: ").replace(",", "")
                    )  # Handle comma-separated input
                    if len(limits) == 1:  # Only minimum limit
                        if value < limits[0]:
                            raise ValueError(f"Value must be at least {limits[0]}")
                    elif len(limits) == 2:  # Both minimum and maximum
                        if value < limits[0] or value > limits[1]:
                            raise ValueError(
                                f"Value must be between {limits[0]} and {limits[1]}"
                            )
                    params[param] = value
                    break
                except ValueError as e:
                    print(f"Invalid input: {str(e)}")

        bool_inputs = [
            ("include_fees", "Include management fees in calculation? (y/n)"),
            ("reinvest_dividends", "Reinvest dividends? (y/n)"),
        ]

        for param, prompt in bool_inputs:
            while True:
                response = input(f"{prompt}: ").lower()
                if response in ["y", "n"]:
                    params[param] = response == "y"
                    break
                print("Please enter 'y' or 'n'")

        params["start_date"] = datetime.date.today()
        self.validate_parameters(params)
        return params

    def format_currency(self, amount: float) -> str:
        """Format amount as Kenya Shillings"""
        try:
            return f"KES {amount:,.2f}"
        except Exception as e:
            raise ValueError(f"Error formatting currency: {str(e)}") from e

    def print_results(self, params: Dict) -> None:
        """Print comprehensive analysis results with error handling"""
        try:
            print("\n" + "=" * 80)
            print("Investment Analysis Results".center(80))
            print("=" * 80 + "\n")

            start_date = params["start_date"]
            end_date = self.add_months(start_date, int(params["investment_period"]))

            # Print Investment Parameters
            print("Investment Parameters:")
            print(f"Initial Capital: {self.format_currency(params['initial_capital'])}")
            print(
                f"Monthly Contribution: {self.format_currency(params['monthly_contribution'])}"
            )
            print(f"Investment Period: {int(params['investment_period'])} months")
            print(f"Start Date: {self.get_month_name(start_date)}")
            print(f"End Date: {self.get_month_name(end_date)}")
            print(f"Withholding Tax: {params['withholding_tax']}%")
            print(
                f"Management Fees: {'Included' if params['include_fees'] else 'Excluded'}"
            )
            print(
                f"Dividend Reinvestment: {'Yes' if params['reinvest_dividends'] else 'No'}"
            )

            # Calculate and sort results
            results = []
            print("\nCalculating returns for each fund...")
            for fund in self.funds:
                try:
                    result = self.calculate_returns(fund, params)
                    results.append((fund, result))
                except Exception as e:
                    print(
                        f"Warning: Could not calculate returns for {fund.name}: {str(e)}"
                    )

            if not results:
                raise ValueError("No valid results calculated for any fund")

            results.sort(key=lambda x: x[1]["final_balance"], reverse=True)

            # Print Fund Comparison
            print("\nFund Comparison:")
            print("-" * 110)
            header = (
                f"{'Fund Name':<35} "
                f"{'Rate':>8} "
                f"{'Final Balance':>20} "
                f"{'Interest':>15} "
                f"{'Net Return':>15}"
            )
            print(header)
            print("-" * 110)

            for fund, result in results:
                print(
                    f"{fund.name:<35}",
                    f"{fund.rate:>8.3f}%",
                    f"{self.format_currency(result['final_balance']):>20}",
                    f"{self.format_currency(result['total_interest']):>15}",
                    f"{result['net_return_percent']:>14.2f}%",
                )

            # Print Best Performing Fund Details
            best_fund, best_result = results[0]
            print("\nBest Performing Fund Details:")
            print("-" * 50)
            print(f"Fund: {best_fund.name}")
            print(f"Annual Interest Rate: {best_fund.rate}%")
            if params["include_fees"]:
                print(f"Management Fee Rate: {best_fund.mgt_fee}%")

            print("\nMonthly Balance Progression (Best Fund):")
            print("-" * 50)

            current_date = start_date
            for i, (month_name, balance) in enumerate(best_result["monthly_balances"]):
                days_in_month = self.get_month_days(current_date)
                print(
                    f"{month_name} ({days_in_month} days): {self.format_currency(balance)}"
                )
                if i < len(best_result["monthly_balances"]) - 1:
                    current_date = self.add_months(current_date, 1)

            # Print Final Results
            print("\nFinal Results:")
            print(
                f"Final Balance: {self.format_currency(best_result['final_balance'])}"
            )
            print(
                f"Total Interest Earned: {self.format_currency(best_result['total_interest'])}"
            )
            if params["include_fees"]:
                print(
                    f"Total Fees Paid: {self.format_currency(best_result['total_fees'])}"
                )
            print(
                f"Total Contribution: {self.format_currency(best_result['total_contribution'])}"
            )
            print(f"Net Return: {best_result['net_return_percent']:.2f}%")

            # Print Notes
            print("\nNotes:")
            print("- Interest is calculated daily and compounded monthly")
            print(
                f"- Returns are shown after {params['withholding_tax']}% withholding tax"
            )
            print("- Past performance does not guarantee future returns")
            if params["include_fees"]:
                print("- Management fees are deducted monthly")
            print("- Calculations account for actual number of days in each month")
            print("- Bank holidays are not considered in the calculations")

        except Exception as e:
            print(f"\nError generating results: {str(e)}")
            raise


def main():
    """
    Main entry point for the Money Market Fund Analysis Tool.

    Handles command line arguments, and manages the interactive analysis session,
    and program termination.

    Usage:
        python mmf_analyzer.py

    Example:
        python mmf_analyzer.py
    """
    try:
        analyzer = MMFAnalyzer()

        while True:
            try:
                params = analyzer.get_user_input()
                analyzer.print_results(params)

                while True:
                    response = input(
                        "\nWould you like to run another analysis? (y/n): "
                    ).lower()
                    if response in ["y", "n"]:
                        if response == "n":
                            print("\nThank you for using the MMF Analysis Tool!")
                            return
                        break
                    print("Please enter 'y' or 'n'")

            except ValueError as e:
                print(f"\nValidation error: {str(e)}")
                print("Please try again.\n")
            except Exception as e:
                print(f"\nAn error occurred: {str(e)}")
                print("Please try again.\n")

    except KeyboardInterrupt:
        print(
            "\n\nAnalysis terminated by user. Thank you for using the MMF Analysis Tool!"
        )
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        print("Please try restarting the application.")


if __name__ == "__main__":
    main()
