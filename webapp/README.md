# Carbon Catalog App

This is a Python web application that displays a catalog of entries fetched from an SQLite database. The application uses the Flask framework for the backend and the Carbon Design framework for the frontend.

## Features

- Fetches 10 random entries from an SQLite database.
- Displays entries as catalog tiles using Carbon Design components.
- Responsive design for various screen sizes.

## Project Structure

```
carbon-catalog-app
├── app
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routes.py
│   └── utils.py
├── instance
│   └── catalog.db
├── static
│   ├── css
│   │   └── main.css
│   ├── js
│   │   └── main.js
├── templates
│   ├── base.html
│   ├── index.html
│   └── components
│       └── catalog_tile.html
├── tests
│   ├── __init__.py
│   ├── test_models.py
│   └── test_routes.py
├── .env
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd carbon-catalog-app
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up the database:
   - Ensure that the `catalog.db` file is present in the `instance` directory.
   - If you need to create the database schema, run the necessary migration scripts or setup scripts.

5. Run the application:
   ```
   python run.py
   ```

6. Open your web browser and navigate to `http://127.0.0.1:5000` to view the application.

## Usage

Once the application is running, you will see a catalog of random entries displayed as tiles. Each tile represents an entry from the database, styled using the Carbon Design framework.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
