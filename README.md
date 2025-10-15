# Burn-up Chart System

An improved burn-up chart system with history protection and smart annotation positioning.

## Features

- 🔒 **History Protection**: Safe daily updates that don't modify historical data
- 🎯 **Smart Annotation Positioning**: Intelligent collision avoidance for task annotations
- 📊 **Professional Charts**: Clean, readable burn-up charts with Plotly
- 📉 **Plan Comparison**: Visualize initial vs. current plan lines alongside actual progress
- 🗄️ **SQLite Database**: Persistent data storage with proper schema
- 📈 **Progress Tracking**: Smooth actual progress generation and planning
- 🔧 **Type Safety**: Full type hints throughout the codebase
- ✅ **Testing**: Comprehensive unit tests with high coverage
- 🎨 **Code Quality**: Lint-compliant code (isort, pylint, black)

## Installation

### From Source

```bash
git clone <repository-url>
cd burnup-chart-system
pip install -e .
```

### Development Installation

```bash
git clone <repository-url>
cd burnup-chart-system
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from burnup_manager import BurnUpManager

# Initialize the manager
manager = BurnUpManager()

# Check system status
manager.check_status()

# Initialize project (run once)
manager.initialize_project("plan.xlsx")

# Daily updates (safe mode)
manager.daily_update("plan.xlsx")

# Generate and display chart
chart = manager.show_improved_chart("YFB", "plan.xlsx")

# Check protection status
manager.show_protection_status("YFB")
```

### Overwrite Task Dates from the Command Line

Use the dedicated helper script to adjust task schedules that are already stored
in the historical database:

```bash
python update_task_dates.py \
  --db burnup_history.db \
  --project "Demo Project" \
  --task "Implement Feature" \
  --start-date 2024-02-01 \
  --end-date 2024-02-20
```

The command exits with status code `0` on success, `1` when the provided dates
are invalid, and `2` if no matching task records are found.

### Data Format

Your Excel/CSV file should contain the following columns (the loader will
automatically fall back between `.xlsx` and `.csv` versions of the same file
name when only one exists):

- `Project Name`: Name of the project
- `Task Name`: Name of the task
- `Start Date`: Task start date (YYYY-MM-DD)
- `End Date`: Task end date (YYYY-MM-DD)
- `Actual`: Actual progress (0.0 to 1.0)
- `Assign`: Person assigned to the task
- `Status`: Task status
- `Show Label`: Optional, 'v' to show annotation (default: 'v')

## Architecture

The system is organized into several focused modules:

### Core Components

- **`burnup_manager.py`**: High-level API for system operations
- **`burnup_system.py`**: Main business logic and workflow coordination
- **`database_model.py`**: Database operations and data persistence
- **`chart_generator.py`**: Chart creation and annotation positioning
- **`progress_calculator.py`**: Progress calculations and algorithms
- **`data_loader.py`**: Data loading and validation utilities

### Key Features

#### Smart Annotation Positioning

The system uses an intelligent algorithm to position task annotations:

1. **Date Grouping**: Groups tasks by proximity (±5 days)
2. **Fan Distribution**: Spreads annotations in a fan pattern
3. **Collision Avoidance**: Automatically adjusts positions to prevent overlaps
4. **Horizontal Offset**: Smart positioning with date offsets

#### History Protection

- Historical data is **never modified** after creation
- Daily updates only affect today's records
- Backfilled data is clearly marked
- Complete audit trail of all changes

## Development

### Code Quality Tools

The project uses several tools to maintain code quality:

```bash
# Format code
black .

# Sort imports
isort .

# Lint code
pylint *.py

# Type checking
mypy .

# Run tests
pytest
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test file
python -m pytest test_burnup_system.py
```

### Project Structure

```
burnup-chart-system/
├── burnup_manager.py          # High-level API
├── burnup_system.py           # Main system logic
├── database_model.py          # Database operations
├── chart_generator.py         # Chart generation
├── progress_calculator.py     # Progress calculations
├── data_loader.py            # Data loading utilities
├── main.py                   # Entry point
├── test_burnup_system.py     # Unit tests
├── setup.py                  # Package setup
├── pyproject.toml           # Tool configuration
└── README.md                # This file
```

## Configuration

### Database Configuration

By default, the system uses SQLite with a file named `burnup_history.db`. You can specify a different database path:

```python
manager = BurnUpManager(db_path="custom_database.db")
```

### Chart Configuration

Charts are highly customizable through the `ChartGenerator` class. Key features:

- Responsive annotation positioning
- Customizable colors and styles
- Professional template
- Interactive tooltips
- Export capabilities

## API Reference

### BurnUpManager

Main interface for the burn-up system.

#### Methods

- `initialize_project(file_path)`: Initialize project with historical data
- `daily_update(file_path)`: Safe daily update
- `show_improved_chart(project_name, file_path)`: Generate and display chart
- `show_protection_status(project_name)`: Display protection status
- `check_status()`: Check system status

### BurnUpSystem

Core system implementation.

#### Methods

- `initialize_project(file_path)`: Project initialization
- `daily_update_safe(file_path)`: Safe daily updates
- `create_burnup_chart(project_name, file_path, filter_options)`: Chart generation with `DateFilterOptions`
- `show_protection_status(project_name)`: Status display

### DatabaseModel

Database operations and persistence.

#### Methods

- `insert_progress_record(progress_record)`: Insert progress record using `ProgressRecord`
- `get_historical_actual_data(project_name)`: Get historical data
- `get_task_annotations(project_name)`: Get task annotations
- `has_historical_data(project_name)`: Check for existing data

## Troubleshooting

### Common Issues

1. **File Not Found**: Ensure your data file exists and is in the correct format
2. **No Historical Data**: Run `initialize_project()` before daily updates
3. **Database Locked**: Close any other applications using the database file
4. **Import Errors**: Ensure all dependencies are installed

### Debug Mode

Enable debug output by setting the logging level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd burnup-chart-system

# Install development dependencies
pip install -e ".[dev]"

# Run pre-commit checks
black .
isort .
pylint *.py
mypy .
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### Version 2.0.0

- 🔧 Complete refactoring with proper separation of concerns
- ✅ Full type hints and documentation
- 🎨 Lint-compliant code (isort, pylint, black)
- 🧪 Comprehensive unit tests
- 🏗️ Modular architecture
- 📦 Proper packaging and setup
- 🎯 Improved smart annotation positioning
- 🔒 Enhanced history protection

### Version 1.0.0

- Initial implementation
- Basic burn-up chart functionality
- SQLite database integration
- Smart annotation positioning
- History protection features
