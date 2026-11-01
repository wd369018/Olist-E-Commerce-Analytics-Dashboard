# Olist Commerce Intelligence

An interactive **Streamlit** analytics dashboard for the Olist Brazilian e-commerce dataset. It turns the Olist datasets into eight focused pages covering revenue, customers, products and sellers, delivery, satisfaction, payments and source data quality.

Every number is calculated from the source datasets. The versioned `data/parquet/` files are the default deployment source; SQLite and raw CSV inputs are optional local alternatives. Streamlit caches the prepared data between reruns and invalidates it when the source files change.

## Quick start (Windows / VS Code)

From the project folder:

```powershell
cd "C:\Users\wd369\Downloads\E-commerce-new-project"
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Streamlit opens `http://localhost:8501` in your browser. Keep the terminal running while you use the dashboard.

> Use the Windows Python launcher **`py`** if `python` is not available. The project was tested with Python 3.14.3, Streamlit 1.57.0, pandas 3.0.3, NumPy 2.4.4, Plotly 7.0.0 and PyArrow 24.0.0.

## Deployment

The committed `data/parquet/` datasets are the default production source. On Streamlit Community Cloud, select **Python 3.14** under **Advanced settings** when deploying; Cloud currently defaults to Python 3.12 and configures the runtime version in the deployment settings. The requirements are pinned to the dependency versions tested with Python 3.14.3. Install them and start Streamlit directly:

```sh
python -m pip install -r requirements.txt
streamlit run app.py
```

No SQLite database initialization or data conversion is needed at startup when the committed Parquet datasets are present. The package metadata for the pinned NumPy, pandas, Streamlit and PyArrow versions includes Python 3.14 support, and the complete test suite passes on Python 3.14.3. Python 3.14.10 itself is not installed in the current verification environment; Community Cloud selects the Python minor release and supplies its current patch release. Use `.env.example` as a template for the supported variable names. Streamlit does not load `.env` files automatically, so set variables in your shell or hosting provider's environment settings; keep any local `.env` file out of version control.

If Parquet needs to be rebuilt from raw CSV files, run the conversion once during the image/build or release step:

```sh
python -m scripts.prepare_data --csv-dir <csv-folder> --output-dir <parquet-folder>
```

At runtime, set `OLIST_PARQUET_DIR` to that prepared directory. `OLIST_CSV_DIR` optionally identifies the CSV source directory when conversion is needed. Setting `OLIST_DB_PATH` explicitly selects SQLite instead of Parquet; use it only when deploying an existing, non-empty SQLite database. Do not generate a database on every production startup, especially on ephemeral or multi-replica hosts.

## Appearance

The **☀️ Light / 🌙 Dark** switch in the top-right corner changes the whole workspace: cards, tables, charts, navigation, the sidebar and Streamlit's native widgets. The choice is kept in the URL (`?theme=dark`), session state and browser localStorage, so it survives a refresh, a bookmark or moving between pages. The first visit follows the browser theme.

## Pages

| Page | What it answers |
| --- | --- |
| **Executive Overview** | Headline revenue, orders, customers, delivery and satisfaction, plus status mix, top categories and state revenue. |
| **Sales Analytics** | Monthly revenue/order trend, category contribution, category mix over time, state concentration and performance tables. |
| **Customer Analytics** | Purchase frequency, RFM segments, new vs returning customers, customer value distribution, state summary and top customers. |
| **Product & Seller Analytics** | Category revenue, seller footprint, top products and sellers, product price/volume economics and category economics. |
| **Delivery Operations** | Delivery time, late rate, carrier vs transit time, delay distribution, late delivery by state/category and monthly operations trend. |
| **Customer Satisfaction** | Review distribution, score trend, delivery delay vs review score, highest/lowest rated categories and review coverage. |
| **Payments Analytics** | Payment method mix, installment behaviour, order payment distribution, monthly value and payment reconciliation. |
| **Data Quality** | Source-wide profiling: missing cells, duplicate keys, invalid date sequences, referential integrity and coverage gaps. |

All pages except **Data Quality** respond to the sidebar filters. Data Quality always profiles the full source so that filtering cannot hide a data problem.

## Filters

The sidebar provides four shared filters:

- **Purchase period** — inclusive order purchase date range.
- **Order status** — one or more statuses; leaving it empty includes every status.
- **Customer state** — one or more Brazilian states.
- **Product category** — one or more translated product categories.

The purchase period uses a calendar range picker. Selecting the start date first applies that single day immediately and keeps the choice while the end date is being picked; it never silently resets to the full range. Dates are treated as timezone-free calendar days and filtered inclusively.

Buttons:

- **Reset** restores the full date range and clears status/state/category selections.
- **Reload** clears Streamlit's data cache and reloads the selected source.

### Category-filter semantics

When categories are selected, an order is kept only if it contains at least one selected category. Revenue, items, products and sellers then describe **only the selected-category items**. Order counts, payments and reviews still describe the full orders that contain those items. A note appears on affected pages. This keeps category revenue accurate without pretending an order contained only the selected category.

## Metric definitions

| Metric | Definition |
| --- | --- |
| **Orders** | Distinct orders placed in the selected period and filters. |
| **Product revenue** | Sum of item prices, **excluding freight**, on orders that are not `canceled` or `unavailable`. |
| **Gross revenue** | Item prices **plus freight** on non-canceled/non-unavailable orders. |
| **Average order value (AOV)** | Product revenue ÷ valid orders that contain at least one item. |
| **Cancellation rate** | Canceled orders ÷ all orders in scope. |
| **Delivery rate** | Delivered orders ÷ all orders in scope. |
| **Repeat rate** | Customers with 2+ valid orders ÷ customers with at least one valid order. |
| **Delivery time** | Purchase timestamp → customer delivery timestamp, in days, for delivered orders with valid non-negative dates. |
| **Late delivery** | A delivered order whose actual delivery timestamp is later than its estimated delivery timestamp. |
| **Average review score** | Mean of the **latest review per order**, restricted to scores 1–5. |
| **Five-star rate** | Reviews with score 5 ÷ valid reviews. |
| **Low-score rate** | Reviews with score 1 or 2 ÷ valid reviews. |
| **Review coverage** | Valid reviews ÷ orders in scope. |
| **Payment total** | Sum of all payment records for orders in scope (payments, unlike product revenue, include freight). |
| **Installment order share** | Orders with a maximum installment count above 1 ÷ orders with payment records. |

### RFM scoring

- **Recency (R):** days since the customer's last valid order, measured from the latest purchase timestamp in the selection.
- **Frequency (F):** absolute number of valid orders per `customer_unique_id`, scored `1 → 1 order`, `2 → 2 orders`, `3 → 3–4`, `4 → 5–7`, `5 → 8+`. Absolute bins are used because roughly 97% of Olist customers ordered only once, which makes quantile bins uninformative.
- **Monetary (M):** product revenue per customer, ranked into five buckets.
- **Segments:** Champions, Loyal customers, New customers, Promising, Potential loyalists, At risk, Hibernating and Lost.

## Data source and modelling

The dashboard resolves the data source in this order:

1. `OLIST_DB_PATH` environment variable, if set (SQLite database).
2. `OLIST_PARQUET_DIR`, if set, or the committed `data/parquet/` directory when all required datasets are available.
3. CSV-to-Parquet conversion from `OLIST_CSV_DIR` (defaults to the project root), when the Parquet dataset is incomplete.
4. `processed/olist_ecommerce.db`, then `olist_ecommerce.db` (optional local SQLite fallback).

SQLite connections use `mode=ro` and are closed after each load. The deployed dashboard needs no SQLite schema initialization: its analytics source is the versioned Parquet dataset. A complete Parquet directory is read without writing to the application filesystem, which is suitable for read-only and ephemeral deployments. CSV files are only read during conversion; the dashboard never modifies or deletes the source data. The raw CSV and SQLite files are ignored by Git; the committed Parquet files are intentionally exempted from the dataset ignore rule because they are required by the hosted app.

For startup commands, CSV preparation, environment-variable setup, and SQLite override behaviour, see [Deployment](#deployment). The complete committed Parquet dataset is selected without conversion or writes. SQLite connections are read-only.

Tables used (source row counts):

| Table | Rows |
| --- | ---: |
| `olist_orders_dataset` | 99,441 |
| `olist_customers_dataset` | 99,441 |
| `olist_order_items_dataset` | 112,650 |
| `olist_order_payments_dataset` | 103,886 |
| `olist_order_reviews_dataset` | 99,224 |
| `olist_products_dataset` | 32,951 |
| `olist_sellers_dataset` | 3,095 |
| `product_category_name_translation` | 71 |

`olist_geolocation_dataset` exists in the database but is not needed for the dashboard's metrics.

### Preventing duplicate counting

The source stores **one row per item, payment and review**, so joining them directly to orders would multiply revenue, order counts and review counts. The data layer instead:

1. Aggregates item rows to one row per order (revenue, freight, item count, product count, seller count).
2. Aggregates payment rows to one row per order (value, record count, maximum installments, primary method).
3. Deduplicates reviews to the **latest review per order**.
4. Joins those order-level frames to the one-row-per-order table.
5. Builds category/state/seller metrics from de-duplicated `(dimension, order_id)` pairs where an order can touch several groups.

This is covered by tests that assert no order or revenue inflation.

### Data-quality caveats handled by the app

- Some source files store missing dates, categories and review comments as the text value **`"0"`**. These are normalised to null/missing before use.
- Invalid or missing timestamps are parsed to null; negative delivery durations are excluded from delivery metrics.
- Eight delivered orders have no customer delivery date; late-rate and delivery-time averages use only delivered orders with valid dates.
- 610 products have no usable category; they are labelled **Uncategorized**.
- A small number of orders have multiple reviews; only the latest is counted.
- Repeated `customer_unique_id` values are expected (customers can place multiple orders); `customer_id` is order-specific.
- Coverage gaps exist (orders without items, payments or reviews). Payment reconciliation is shown on the Payments page when category filtering is off.

The **Data Quality** page reports the current source-wide snapshot, including sentinel values, missing timestamps, impossible date sequences, duplicate keys and foreign-key orphans. Critical key collisions and orphan counts are separated from expected duplicates such as repeated `customer_unique_id`.

## Project structure

```text
E-commerce-new-project/
├── app.py                      # Streamlit entry point, sidebar filters, navigation
├── dashboard/
│   ├── charts.py               # Reusable Plotly chart builders
│   ├── config.py               # Paths, palette, labels, metric help, DB resolution
│   ├── context.py              # Cached data access and session-filter handling
│   ├── data.py                 # Read-only SQLite loading and order-level modelling
│   ├── filters.py              # Filter model and non-duplicating context construction
│   ├── formatting.py           # Currency, percentage and number formatting
│   ├── metrics.py              # KPIs, RFM, delivery, satisfaction, payment metrics
│   ├── quality.py              # Source-wide data-quality checks
│   ├── ui.py                   # CSS, headers, KPI cards, callouts, tables
│   ├── pages/                  # Eight thin Streamlit page entry points
│   └── views/                  # Page layouts and visualisations
├── tests/                      # Data, filter, metric, quality and AppTest suites
├── data/parquet/               # Versioned, read-only deployment datasets
├── scripts/prepare_data.py     # Optional CSV-to-Parquet preparation command
├── .streamlit/config.toml      # Light/dark native themes and local server settings
├── requirements.txt
├── pytest.ini
└── README.md
```

## Configuration

The default deployment source requires no environment variables. To use a prepared Parquet directory:

```powershell
$env:OLIST_PARQUET_DIR = "D:\data\parquet"
py -m streamlit run app.py
```

To select a non-empty SQLite database instead:

```powershell
$env:OLIST_DB_PATH = "D:\data\olist_ecommerce.db"
py -m streamlit run app.py
```

SQLite must contain the Olist source tables used by the dashboard. `.env.example` lists supported variables; configure them in the shell or hosting provider rather than relying on a local `.env` file.

## Tests

```powershell
py -m pytest -q
```

The suite currently contains **94 tests** and takes about two minutes on this machine. It exercises every dashboard page, filters, empty selections and an entirely empty Parquet source, data loading and metrics.

Useful subsets:

```powershell
py -m pytest tests/test_metrics.py -q
py -m pytest tests/test_filters.py tests/test_quality.py -q
py -m pytest tests/test_context.py -q
py -m pytest tests/test_app.py -q
```

Coverage includes:

- Sentinel cleaning, date parsing, review de-duplication and item/payment aggregation.
- Filter semantics, empty selections, category filtering and invalid date ranges.
- Date normalisation for single-day, reversed, clamped, invalid and timezone-aware selections.
- Theme tokens, mode normalisation, light/dark contrast and the responsive stylesheet contract.
- KPI formulas, RFM segmentation, delivery edge cases, satisfaction and payment metrics.
- Data-quality profiling and referential integrity.
- AppTest smoke tests for the app shell, every page in both themes, filter updates, a canceled-only scenario, an empty date range, dark mode and a single-day selection.

The `missing ScriptRunContext` messages sometimes printed by Streamlit during bare AppTest runs are harmless test-mode warnings.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| **Dashboard cannot load the datasets** | Confirm all required Parquet files exist in `data/parquet/`, or set `OLIST_PARQUET_DIR` to a complete dataset directory. To use SQLite instead, set `OLIST_DB_PATH` to a non-empty database with the required Olist tables. |
| **`python` is not recognized** | Use `py` instead, e.g. `py -m streamlit run app.py`. |
| **`streamlit` is not recognized** | Install dependencies with `py -m pip install -r requirements.txt`, then run `py -m streamlit run app.py`. |
| **First load is slow** | The Parquet datasets are loaded once and cached. Cache keys include source file size and modification time, so replacing files at the same path triggers a reload. |
| **Port 8501 is already in use** | Run on another port: `py -m streamlit run app.py --server.port 8502`. |
| **Filters return no data** | Widen the date range, clear status/state/category selections, or press **Reset**. A page with zero rows shows an empty-state message rather than an error. |
| **Figures look stale** | The app detects changes to dataset files at the same path. Press **Reload** to clear all Streamlit data caches if needed. |

## Notes

- The default analytics source is the versioned Parquet dataset. SQLite connections are read-only.
- Raw CSV files and local databases are excluded from version control; the deployment Parquet dataset is committed.
- Currency is Brazilian real (**R$**). Revenue figures are nominal, not inflation-adjusted.
- The final months of the Olist source are incomplete; monthly charts label them as provisional where relevant.
- Data attribution: **Olist Brazilian E-Commerce Public Dataset** (originally published on Kaggle for educational and research use).
