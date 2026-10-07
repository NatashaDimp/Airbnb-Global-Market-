import logging
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# ------------------------------------------------------------
# 1. CONFIG — the only section you should need to edit
# ------------------------------------------------------------
LISTINGS_CSV = "../data/Listings.csv"
REVIEWS_CSV = "../data/Reviews.csv"

# Format: postgresql+psycopg2://<username>:<password>@<host>:<port>/<database>
DB_CONNECTION_STRING = "postgresql+psycopg2://postgres:airbnb21@localhost:5432/airbnb_user"



# Reviews.csv has ~5.37 million rows — too big to load into memory
# in one go on most laptops, so we read and load it in chunks.
CHUNK_SIZE = 200_000

# The CSVs contain a few characters that aren't standard UTF-8
# (this is common with older exported datasets). "latin1" reads
# every byte without crashing — see the PDF guide's
# "Data Quality Checks" section for why this matters.
FILE_ENCODING = "latin1"

# ------------------------------------------------------------
# 2. LOGGING — prints timestamped progress messages
#    instead of plain print() statements, so you can see
#    exactly what happened and when if something goes wrong.
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("airbnb_etl")


# ------------------------------------------------------------
# 3. EXTRACT — read the raw CSV into a DataFrame
# ------------------------------------------------------------
def extract_listings(path: str) -> pd.DataFrame:
    logger.info("EXTRACT: reading Listings.csv ...")
    df = pd.read_csv(path, encoding=FILE_ENCODING, low_memory=False)
    logger.info("EXTRACT: loaded %s rows, %s columns", f"{len(df):,}", df.shape[1])
    return df
import pandas as pd
from sqlalchemy import create_engine

# 1. Connect to your PostgreSQL database
engine = create_engine(
    "postgresql+psycopg2://postgres:your_password@localhost:5432/airbnb_project"
)

# 2. Load your CSVs into DataFrames
df_listings = pd.read_csv("Listings.csv", encoding="utf-8")
df_reviews = pd.read_csv("Reviews.csv", encoding="utf-8")

# 3. Write Listings into raw schema
df_listings.to_sql(
    "listings",
    engine,
    schema="raw",
    if_exists="replace",
    index=False,
    chunksize=50_000,
    method="multi"
)
# ------------------------------------------------------------
# 4. DATA QUALITY CHECKS — look BEFORE you clean, so you know
#    what you're actually dealing with. This function doesn't
#    change any data — it only reports on it.
# ------------------------------------------------------------
def run_quality_checks(df: pd.DataFrame, label: str) -> None:
    logger.info("---- DATA QUALITY REPORT: %s ----", label)
    logger.info("Row count: %s", f"{len(df):,}")

    if "listing_id" in df.columns:
        dupes = df["listing_id"].duplicated().sum()
        logger.info("Duplicate listing_id rows: %s", dupes)

    missing_pct = (df.isna().mean() * 100).round(1).sort_values(ascending=False)
    top_missing = missing_pct[missing_pct > 0].head(8)
    if not top_missing.empty:
        logger.info("Columns with the most missing values (%%):\n%s", top_missing.to_string())

    if "price" in df.columns:
        zero_or_negative = (df["price"] <= 0).sum()
        logger.info("Listings priced at $0 or less (data errors): %s", zero_or_negative)

    logger.info("---- END REPORT: %s ----", label)


# ------------------------------------------------------------
# 5. TRANSFORM — fix the issues the quality report uncovered
# ------------------------------------------------------------
def clean_listings(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # a) True/False columns arrive as the letters "t" and "f".
    #    Convert them to real booleans so SQL and Power BI treat
    #    them correctly (not as text).
    bool_cols = [
        "host_is_superhost",
        "host_has_profile_pic",
        "host_identity_verified",
        "instant_bookable",
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"t": True, "f": False})

    # b) Turn the "host_since" text into a real date.
    df["host_since"] = pd.to_datetime(df["host_since"], errors="coerce")

    # c) Drop "district" — it's 86.8% empty across this dataset,
    #    so it can't reliably support any analysis.
    if "district" in df.columns:
        df = df.drop(columns=["district"])

    # d) Remove listings priced at $0 or less — these are data
    #    entry errors, not real prices (113 rows in this dataset).
    df = df[df["price"] > 0]

    # e) Cap extreme price outliers instead of deleting them.
    #    A few listings are priced above $600,000/night, which
    #    would distort every average in the dashboard. We keep
    #    the original price AND add a capped column for analysis.
    price_cap = df["price"].quantile(0.99)
    df["price_capped"] = np.where(df["price"] > price_cap, price_cap, df["price"])

    # f) Safety net: remove any exact duplicate listings.
    df = df.drop_duplicates(subset="listing_id")

    # g) Flag listings that have never been reviewed, instead of
    #    leaving their review-score columns as blank/NaN.
    df["has_reviews"] = df["review_scores_rating"].notna()

    return df


def clean_reviews_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    chunk = chunk.copy()
    chunk["date"] = pd.to_datetime(chunk["date"], errors="coerce")
    chunk = chunk.dropna(subset=["date"])
    chunk = chunk.drop_duplicates(subset="review_id")
    return chunk


# ------------------------------------------------------------
# 6. LOAD — write the cleaned data into PostgreSQL's raw schema
# ------------------------------------------------------------
    logger.info("LOAD: listings done.")
def load_listings(df: pd.DataFrame, engine) -> None:
    logger.info("LOAD: writing %s listing rows to raw.listings ...", f"{len(df):,}")
    df.to_sql("listings", engine, if_exists="replace", index=False, chunksize=50_000, method="multi")
    logger.info("LOAD: listings done.")


def load_reviews_in_chunks(path: str, engine) -> int:
    logger.info("LOAD: streaming Reviews.csv in chunks of %s rows ...", f"{CHUNK_SIZE:,}")
    total_loaded = 0
    first_chunk = True

    for chunk in pd.read_csv(path, encoding=FILE_ENCODING, chunksize=CHUNK_SIZE):
        clean_chunk = clean_reviews_chunk(chunk)
        clean_chunk.to_sql(
            "reviews",
            engine,
            schema="raw",
            if_exists="replace" if first_chunk else "append",
            index=False,
            method="multi",
        )
        first_chunk = False
        total_loaded += len(clean_chunk)
        logger.info("LOAD: %s review rows loaded so far ...", f"{total_loaded:,}")

    logger.info("LOAD: reviews done — %s total rows.", f"{total_loaded:,}")
    return total_loaded


# ------------------------------------------------------------
# 7. MAIN — runs the whole pipeline, top to bottom
# ------------------------------------------------------------
def main():
    engine = create_engine(DB_CONNECTION_STRING)

    # --- Listings ---
    listings_raw = extract_listings(LISTINGS_CSV)
    run_quality_checks(listings_raw, "Listings — BEFORE cleaning")

    listings_clean = clean_listings(listings_raw)
    run_quality_checks(listings_clean, "Listings — AFTER cleaning")

    load_listings(listings_clean, engine)

    # --- Reviews (streamed — file is too large to hold in memory) ---
    load_reviews_in_chunks(REVIEWS_CSV, engine)

    logger.info("PIPELINE COMPLETE. Raw layer is ready in PostgreSQL.")
    logger.info("Next: run the SQL scripts in /sql to build staging and analytics.")


if __name__ == "__main__":
    main()
