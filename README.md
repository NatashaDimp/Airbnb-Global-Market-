# Airbnb End-to-End Data Pipeline

A full data engineering + analytics pipeline: raw CSV files are extracted and
cleaned in **Python**, loaded into a three-layer **PostgreSQL** warehouse,
transformed with **SQL**, and visualised in **Power BI**.

```
Airbnb CSV files
       │
       ▼
  Python ETL  (extract, data quality checks, clean, load)
       │
       ▼
 PostgreSQL — raw → staging → analytics
       │
       ▼
      SQL (views for reporting)
       │
       ▼
   Power BI
       │
       ▼
   Dashboard
```

## Dataset

Global Airbnb listings and reviews across 10 cities (Paris, New York, Sydney,
Rome, Rio de Janeiro, Istanbul, Mexico City, Bangkok, Cape Town, Hong Kong).

| File | Rows | Description |
|---|---|---|
| `Listings.csv` | 279,712 | One row per listing: host, location, price, room type, review scores |
| `Reviews.csv` | 5,373,143 | One row per review: listing, reviewer, date |

Not included in this repo (see `.gitignore`) — download from the original
source and place both files in `/data`.

## Project structure

```
airbnb-data-pipeline/
├── data/                      # raw CSVs (not committed — see .gitignore)
├── etl/
│   └── airbnb_etl.py          # extract, quality-check, clean, load to raw
├── sql/
│   ├── 01_create_raw_schema.sql
│   ├── 02_staging_transform.sql
│   └── 03_analytics_layer.sql
├── powerbi/
│   └── airbnb_dashboard.pbix  # add your saved Power BI file here
├── requirements.txt
└── README.md
```

## How to run it

1. Install PostgreSQL and create a database called `airbnb_project`.
2. `pip install -r requirements.txt`
3. Run `sql/01_create_raw_schema.sql` in pgAdmin (or `psql`).
4. Edit the `DB_CONNECTION_STRING` at the top of `etl/airbnb_etl.py`.
5. Run `python etl/airbnb_etl.py` — this populates the `raw` schema.
6. Run `sql/02_staging_transform.sql`, then `sql/03_analytics_layer.sql`.
7. Open Power BI Desktop → Get Data → PostgreSQL database → connect to the
   `analytics` schema views → build the dashboard.

Full beginner-friendly walkthrough with time estimates:
`Airbnb_End_to_End_Pipeline_Guide.pdf`.

## Data quality issues found and handled

- 113 listings priced at $0 or less → removed (data entry errors).
- Prices ranged up to $625,216/night → capped at the 99th percentile
  ($6,500) in a separate `price_capped` column so outliers don't distort
  averages, while the original `price` is kept for reference.
- `district` column was 86.8% empty → dropped.
- File encoding wasn't standard UTF-8 → read with `latin1` encoding.
- `host_is_superhost`, `host_has_profile_pic`, `host_identity_verified`,
  `instant_bookable` arrived as `"t"`/`"f"` text → converted to real booleans.
- ~32.8% of listings have no review scores yet → flagged with a
  `has_reviews` column instead of leaving blanks.

## Tools used

Python (pandas, SQLAlchemy) · PostgreSQL · SQL · Power BI
