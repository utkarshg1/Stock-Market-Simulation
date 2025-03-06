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

# Import matplotlib and its Qt backend for embedding
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
        # GBM formula: dS = μSdt + σSdW
        drift = (self.mu - 0.5 * self.sigma**2) * self.dt
        diffusion = self.sigma * np.random.normal(0, np.sqrt(self.dt))
        self.price *= np.exp(drift + diffusion)
        self.price_updated.emit(round(self.price, 2))


class PortfolioManager(QObject):
    # Signal that emits both cash and shares when updated
    portfolio_updated = Signal(float, int)

    def __init__(self, filename="cash.json"):
        super().__init__()
        self.filename = filename
        self._cash, self._shares = self.load_portfolio()

    def load_portfolio(self):
        try:
            with open(self.filename, "r") as f:
                data = json.load(f)
                cash = data.get("cash", 10000.0)
                shares = data.get("shares", 0)
                return cash, shares
        except (FileNotFoundError, json.JSONDecodeError):
            return 10000.0, 0

    @property
    def cash(self):
        return self._cash

    @cash.setter
    def cash(self, value):
        self._cash = round(value, 2)
        self.save_portfolio()
        self.portfolio_updated.emit(self._cash, self._shares)

    @property
    def shares(self):
        return self._shares

    @shares.setter
    def shares(self, value):
        self._shares = int(value)
        self.save_portfolio()
        self.portfolio_updated.emit(self._cash, self._shares)

    def save_portfolio(self):
        with open(self.filename, "w") as f:
            json.dump({"cash": self._cash, "shares": self._shares}, f)


class StockTradingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_price = 100.0
        self.price_history = [self.current_price]  # Track price changes over time
        self.portfolio_manager = PortfolioManager()  # Now handles both cash and shares
        self.stock_simulator = StockSimulator()
        self.init_ui()
        self.setup_timers()

    def init_ui(self):
        self.setWindowTitle("Stock Market Simulator")
        self.setGeometry(100, 100, 1200, 800)

        # Title label with cool styling
        title_label = QLabel("Stock Market Simulator")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #333; padding: 10px;"
        )

        # Portfolio labels (cash and shares)
        self.cash_label = QLabel(f"Cash: ${self.portfolio_manager.cash:.2f}")
        self.cash_label.setStyleSheet("font-size: 18px;")
        self.shares_label = QLabel(f"Shares Owned: {self.portfolio_manager.shares}")
        self.shares_label.setStyleSheet("font-size: 18px;")

        # Create a larger matplotlib figure and canvas for the price graph
        self.figure = Figure(figsize=(10, 6))
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Stock Price Movement")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Price")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        self.update_graph()  # Plot the initial price

        # Trade panel widgets with styling
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter shares quantity")
        self.quantity_input.setStyleSheet("font-size: 16px; padding: 5px;")
        self.buy_button = QPushButton("Buy")
        self.buy_button.setStyleSheet(
            "font-size: 16px; padding: 5px; background-color: #4CAF50; color: white;"
        )
        self.sell_button = QPushButton("Sell")
        self.sell_button.setStyleSheet(
            "font-size: 16px; padding: 5px; background-color: #f44336; color: white;"
        )

        # Layouts
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Title section
        main_layout.addWidget(title_label)

        # Portfolio info panel (cash and shares)
        info_layout = QHBoxLayout()
        info_layout.addWidget(self.cash_label)
        info_layout.addStretch()
        info_layout.addWidget(self.shares_label)
        main_layout.addLayout(info_layout)

        # Graph section
        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.canvas)
        main_layout.addLayout(graph_layout)

        # Trade panel
        trade_layout = QHBoxLayout()
        trade_layout.addWidget(self.quantity_input)
        trade_layout.addWidget(self.buy_button)
        trade_layout.addWidget(self.sell_button)
        main_layout.addLayout(trade_layout)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Connect signals
        self.buy_button.clicked.connect(self.buy_stock)
        self.sell_button.clicked.connect(self.sell_stock)
        self.portfolio_manager.portfolio_updated.connect(self.update_portfolio_display)
        self.stock_simulator.price_updated.connect(self.update_price_display)

    def setup_timers(self):
        # Update the stock price every second
        self.price_timer = QTimer()
        self.price_timer.timeout.connect(self.stock_simulator.update_price)
        self.price_timer.start(1000)

    def update_portfolio_display(self, cash, shares):
        self.cash_label.setText(f"Cash: ${cash:.2f}")
        self.shares_label.setText(f"Shares Owned: {shares}")

    def update_price_display(self, price):
        self.current_price = price
        self.price_history.append(price)
        self.update_graph()

    def update_graph(self):
        self.ax.clear()  # Clear previous graph
        self.ax.plot(self.price_history, color="blue")
        self.ax.set_title("Stock Price Movement")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Price")
        self.canvas.draw()

    def buy_stock(self):
        try:
            quantity = int(self.quantity_input.text())
            total_cost = self.current_price * quantity
            if total_cost <= self.portfolio_manager.cash:
                self.portfolio_manager.cash -= total_cost
                self.portfolio_manager.shares += quantity
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StockTradingApp()
    window.showMaximized()  # Launch maximized for a larger display
    sys.exit(app.exec())
