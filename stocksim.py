import sys
import json
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
)
from PySide6.QtCore import QTimer, QObject, Signal, Qt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class StockSimulator(QObject):
    price_updated = Signal(float)

    def __init__(self, initial_price=100.0, mu=0.1, sigma=0.2, dt=1 / 252):
        super().__init__()
        self.price = initial_price
        self.mu = mu  # Drift
        self.sigma = sigma  # Volatility
        self.dt = dt  # Time step (daily)

    def update_price(self):
        # Geometric Brownian Motion formula: dS = μSdt + σSdW
        drift = (self.mu - 0.5 * self.sigma**2) * self.dt
        diffusion = self.sigma * np.random.normal(0, np.sqrt(self.dt))
        self.price *= np.exp(drift + diffusion)
        self.price_updated.emit(round(self.price, 2))


class PortfolioManager(QObject):
    portfolio_updated = Signal(float, int)

    def __init__(self, initial_cash=10000.0, initial_shares=0):
        super().__init__()
        self._cash = initial_cash
        self._shares = initial_shares

    @property
    def cash(self):
        return self._cash

    @cash.setter
    def cash(self, value):
        self._cash = round(value, 2)
        self.portfolio_updated.emit(self._cash, self._shares)

    @property
    def shares(self):
        return self._shares

    @shares.setter
    def shares(self, value):
        self._shares = int(value)
        self.portfolio_updated.emit(self._cash, self._shares)


class StockTradingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.price_history = []
        self.buy_events = []
        self.sell_events = []

        # Load saved data
        self.cash, self.shares, self.initial_price = self.load_data()
        self.portfolio_manager = PortfolioManager(self.cash, self.shares)
        self.stock_simulator = StockSimulator(initial_price=self.initial_price)
        self.current_price = self.initial_price
        self.price_history.append(self.current_price)

        self.init_ui()
        self.setup_timers()

    def load_data(self):
        try:
            with open("portfolio.json", "r") as f:
                data = json.load(f)
                return (
                    data.get("cash", 10000.0),
                    data.get("shares", 0),
                    data.get("stock_price", 100.0),
                )
        except (FileNotFoundError, json.JSONDecodeError):
            return (10000.0, 0, 100.0)

    def save_data(self, cash, shares):
        data = {
            "cash": cash,
            "shares": shares,
            "stock_price": self.stock_simulator.price,
        }
        with open("portfolio.json", "w") as f:
            json.dump(data, f)

    def init_ui(self):
        self.setWindowTitle("Stock Market Simulator")
        self.setGeometry(100, 100, 1200, 800)

        # Title label
        title_label = QLabel("Stock Market Simulator")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #333; padding: 10px;"
        )

        # Portfolio info
        self.cash_label = QLabel(f"Cash: ${self.portfolio_manager.cash:.2f}")
        self.cash_label.setStyleSheet("font-size: 18px;")
        self.shares_label = QLabel(f"Shares Owned: {self.portfolio_manager.shares}")
        self.shares_label.setStyleSheet("font-size: 18px;")
        # Added stock price label (formatted to 2 decimals)
        self.price_label = QLabel(f"Stock Price: ${self.current_price:.2f}")
        self.price_label.setStyleSheet("font-size: 18px;")

        # Matplotlib graph
        self.figure = Figure(figsize=(10, 6))
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Stock Price Movement")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Price")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.update_graph()

        # Trading controls
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter shares quantity")
        self.quantity_input.setStyleSheet("font-size: 16px; padding: 5px;")
        self.buy_button = QPushButton("Buy")
        self.sell_button = QPushButton("Sell")

        # Layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        main_layout.addWidget(title_label)

        info_layout = QHBoxLayout()
        info_layout.addWidget(self.cash_label)
        info_layout.addStretch()
        info_layout.addWidget(self.shares_label)
        info_layout.addStretch()
        info_layout.addWidget(self.price_label)  # Add price label in the info layout
        main_layout.addLayout(info_layout)

        main_layout.addWidget(self.canvas)

        trade_layout = QHBoxLayout()
        trade_layout.addWidget(self.quantity_input)
        trade_layout.addWidget(self.buy_button)
        trade_layout.addWidget(self.sell_button)
        main_layout.addLayout(trade_layout)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Connections
        self.buy_button.clicked.connect(self.buy_stock)
        self.sell_button.clicked.connect(self.sell_stock)
        self.portfolio_manager.portfolio_updated.connect(self.update_portfolio_display)
        self.stock_simulator.price_updated.connect(self.update_price_display)
        self.portfolio_manager.portfolio_updated.connect(self.save_data)

    def setup_timers(self):
        self.price_timer = QTimer()
        self.price_timer.timeout.connect(self.stock_simulator.update_price)
        self.price_timer.start(1000)

    def update_portfolio_display(self, cash, shares):
        self.cash_label.setText(f"Cash: ${cash:.2f}")
        self.shares_label.setText(f"Shares Owned: {shares}")

    def update_price_display(self, price):
        self.current_price = price
        self.price_history.append(price)
        # Update stock price label with 2 decimal precision
        self.price_label.setText(f"Stock Price: ${price:.2f}")
        self.update_graph()

    def update_graph(self):
        self.ax.clear()
        x = list(range(len(self.price_history)))
        self.ax.plot(x, self.price_history, color="blue", label="Price")

        # Plot buy/sell markers
        if self.buy_events:
            x_buy = [pt[0] for pt in self.buy_events]
            y_buy = [pt[1] for pt in self.buy_events]
            self.ax.scatter(x_buy, y_buy, marker="^", s=100, color="green", label="Buy")
        if self.sell_events:
            x_sell = [pt[0] for pt in self.sell_events]
            y_sell = [pt[1] for pt in self.sell_events]
            self.ax.scatter(
                x_sell, y_sell, marker="v", s=100, color="red", label="Sell"
            )

        if self.buy_events or self.sell_events:
            self.ax.legend()
        self.canvas.draw()

    def buy_stock(self):
        try:
            quantity = int(self.quantity_input.text())
            total_cost = self.current_price * quantity
            if total_cost <= self.portfolio_manager.cash:
                self.portfolio_manager.cash -= total_cost
                self.portfolio_manager.shares += quantity
                self.buy_events.append(
                    (len(self.price_history) - 1, self.current_price)
                )
            else:
                self.show_error("Insufficient funds!")
        except ValueError:
            self.show_error("Invalid quantity!")

    def sell_stock(self):
        try:
            quantity = int(self.quantity_input.text())
            if quantity <= self.portfolio_manager.shares:
                total_revenue = self.current_price * quantity
                self.portfolio_manager.cash += total_revenue
                self.portfolio_manager.shares -= quantity
                self.sell_events.append(
                    (len(self.price_history) - 1, self.current_price)
                )
            else:
                self.show_error("Not enough shares!")
        except ValueError:
            self.show_error("Invalid quantity!")

    def show_error(self, message):
        error_label = QLabel(message)
        error_label.setStyleSheet("color: red; font-size: 16px;")
        error_label.setAlignment(Qt.AlignCenter)
        self.statusBar().addWidget(error_label)
        QTimer.singleShot(3000, lambda: self.statusBar().removeWidget(error_label))

    def closeEvent(self, event):
        self.save_data(self.portfolio_manager.cash, self.portfolio_manager.shares)
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StockTradingApp()
    window.showMaximized()
    sys.exit(app.exec())
