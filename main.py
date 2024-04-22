from BullPutSpread import BullPutSpread
import tkinter as tk

class BullPutSpreadApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Bull Put Spread Calculator")
        self.bps = BullPutSpread('SPY')
        self.bps.set_short_put(self.bps.get_strikes(self.bps.get_maturities()[0])[0], self.bps.get_maturities()[0])
        self.bps.set_long_put(self.bps.get_strikes(self.bps.get_maturities()[0])[0], self.bps.get_maturities()[0])
        self.create_widgets()
        
    def create_widgets(self) -> None:
        self.ticker_label = tk.Label(self, text="Ticker")
        self.ticker_label.grid(row=0, column=0)
        self.ticker_entry = tk.Entry(self)
        self.ticker_entry.grid(row=0, column=1)
        self.ticker_entry.insert(0, 'SPY')
        self.ticker_underlying_price_label = tk.Label(self, text=f"Spot Price: {round(self.bps.underlying_price, 2)}")
        self.ticker_underlying_price_label.grid(row=1, column=0)

        self.maturity_label = tk.Label(self, text="Maturity")
        self.maturity_label.grid(row=2, column=0)
        self.maturity_var = tk.StringVar(self)
        self.maturity_var.set(self.bps.get_maturities()[0])
        self.maturity_option = tk.OptionMenu(self, self.maturity_var, *self.bps.get_maturities(), command=self.set_maturity)
        self.maturity_option.grid(row=2, column=1)
        self.plot_iv_button = tk.Button(self, text="Plot IV", command=self.plot_iv)
        self.plot_iv_button.grid(row=2, column=2)
        self.plot_delta_button = tk.Button(self, text="Plot Delta", command=self.plot_delta)
        self.plot_delta_button.grid(row=2, column=3)

        self.short_put_label = tk.Label(self, text="Short Put Strike")
        self.short_put_label.grid(row=3, column=0)
        self.short_put_var = tk.StringVar(self)
        self.short_put_var.set(self.bps.get_strikes(self.maturity_var.get())[0])
        self.short_put_option = tk.OptionMenu(self, self.short_put_var, *self.bps.get_strikes(self.maturity_var.get()), command=self.set_short_put_strike)
        self.short_put_option.grid(row=3, column=1)

        self.long_put_label = tk.Label(self, text="Long Put Strike")
        self.long_put_label.grid(row=4, column=0)
        self.long_put_var = tk.StringVar(self)
        self.long_put_var.set(self.bps.get_strikes(self.maturity_var.get())[0])
        self.long_put_option = tk.OptionMenu(self, self.long_put_var, *self.bps.get_strikes(self.maturity_var.get()), command=self.set_long_put_strike)
        self.long_put_option.grid(row=4, column=1)

        self.calculate_button = tk.Button(self, text="Graph Payoff", command=self.graph_payoff)
        self.calculate_button.grid(row=6, column=0)
        self.update_button = tk.Button(self, text="Update", command=self.set_ticker)
        self.update_button.grid(row=6, column=1)
        self.pnl_label = tk.Label(self, text=f"Max Profit: {round(self.bps.get_max_profit(), 2)}, Max Loss: {round(self.bps.get_max_loss(), 2)}")
        self.pnl_label.grid(row=6, column=2)

        self.short_put_price_label = tk.Label(self, text=f"Short Put Price: {round(100*self.bps.strategy['short_put']['price'], 2)}")
        self.short_put_price_label.grid(row=3, column=2)
        self.short_put_delta_label = tk.Label(self, text=f"Short Put Delta: {round(self.bps.get_delta('short_put'), 2)}")
        self.short_put_delta_label.grid(row=3, column=3)
        self.long_put_price_label = tk.Label(self, text=f"Long Put Price: {round(100*self.bps.strategy['long_put']['price'], 2)}")
        self.long_put_price_label.grid(row=4, column=2)
        self.long_put_delta_label = tk.Label(self, text=f"Long Put Delta: {round(self.bps.get_delta('long_put'), 2)}")
        self.long_put_delta_label.grid(row=4, column=3)

    def set_maturity(self, *args) -> None:
        selected_maturity = self.maturity_var.get()
        self.short_put_option['menu'].delete(0, 'end')
        self.long_put_option['menu'].delete(0, 'end')
        for strike in self.bps.get_strikes(selected_maturity):
            self.short_put_option['menu'].add_command(label=strike, command=tk._setit(self.short_put_var, strike, self.refresh))
            self.long_put_option['menu'].add_command(label=strike, command=tk._setit(self.long_put_var, strike, self.refresh))
        self.short_put_var.set(self.bps.get_strikes(selected_maturity)[0])
        self.long_put_var.set(self.bps.get_strikes(selected_maturity)[0])
        self.refresh()

    def set_long_put_strike(self, *args) -> None:
        self.bps.set_long_put(float(self.long_put_var.get()), self.maturity_var.get())
        self.refresh()

    def set_short_put_strike(self, *args) -> None:
        self.bps.set_short_put(float(self.short_put_var.get()), self.maturity_var.get())
        self.refresh()

    def set_ticker(self, *args) -> None:
        ticker = self.ticker_entry.get()
        self.bps = BullPutSpread(ticker)
        self.bps.set_short_put(self.bps.get_strikes(self.bps.get_maturities()[0])[0], self.bps.get_maturities()[0])
        self.bps.set_long_put(self.bps.get_strikes(self.bps.get_maturities()[0])[0], self.bps.get_maturities()[0])

        # Update the dropdown menus
        self.maturity_option['menu'].delete(0, 'end')
        for maturity in self.bps.get_maturities():
            self.maturity_option['menu'].add_command(label=maturity, command=tk._setit(self.maturity_var, maturity, self.set_maturity))
        self.maturity_var.set(self.bps.get_maturities()[0])
        self.short_put_option['menu'].delete(0, 'end')
        self.long_put_option['menu'].delete(0, 'end')
        for strike in self.bps.get_strikes(self.maturity_var.get()):
            self.short_put_option['menu'].add_command(label=strike, command=tk._setit(self.short_put_var, strike, self.refresh))
            self.long_put_option['menu'].add_command(label=strike, command=tk._setit(self.long_put_var, strike, self.refresh))
        self.short_put_var.set(self.bps.get_strikes(self.maturity_var.get())[0])
        self.long_put_var.set(self.bps.get_strikes(self.maturity_var.get())[0])
        self.refresh()

    def refresh(self, *args) -> None:
        self.bps.set_short_put(float(self.short_put_var.get()), self.maturity_var.get())
        self.bps.set_long_put(float(self.long_put_var.get()), self.maturity_var.get())
        self.ticker_underlying_price_label.config(text=f"Spot Price: {round(self.bps.underlying_price, 2)}")
        self.short_put_price_label.config(text=f"Short Put Price: {round(100*self.bps.strategy['short_put']['price'], 2)}")
        self.long_put_price_label.config(text=f"Long Put Price: {round(100*self.bps.strategy['long_put']['price'], 2)}")
        self.pnl_label.config(text=f"Max Profit: {round(self.bps.get_max_profit(), 2)}, Max Loss: {round(self.bps.get_max_loss(), 2)}")
        self.short_put_delta_label.config(text=f"Short Put Delta: {round(self.bps.get_delta('short_put'), 2)}")
        self.long_put_delta_label.config(text=f"Long Put Delta: {round(self.bps.get_delta('long_put'), 2)}")

    def graph_payoff(self) -> None:
        self.bps.set_short_put(float(self.short_put_var.get()), self.maturity_var.get())
        self.bps.set_long_put(float(self.long_put_var.get()), self.maturity_var.get())
        self.bps.plot_payoff()
        self.ticker_underlying_price_label.config(text=f"Spot Price: {round(self.bps.underlying_price, 2)}")

        self.update()

    def plot_iv(self) -> None:
        self.bps.plot_iv(self.maturity_var.get())

        self.update()

    def plot_delta(self) -> None:
        self.bps.plot_delta(self.maturity_var.get())

        self.update()

app = BullPutSpreadApp()

app.mainloop()