"""SQL support for hybrid retrieval and structured data queries."""
import logging
import os
from typing import List, Optional

from sqlalchemy import create_engine
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def get_db_engine():
    """Create a SQLAlchemy engine for the configured Postgres database."""
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "rag_db")
    database_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(database_url)


def get_sql_database(engine=None, include_tables=None):
    """
    Return a LlamaIndex SQLDatabase wrapper over the Postgres engine.
    
    By default it exposes the core business tables used in this demo.
    """
    if engine is None:
        engine = get_db_engine()
    if include_tables is None:
        include_tables = [
            "tiers",
            "discounts",
            "taxes",
            "customers",
            "subscriptions",
            "revenue",
        ]
    return SQLDatabase(engine, include_tables=include_tables)


def create_sql_query_engine() -> NLSQLTableQueryEngine:
    """Create a SQL query engine for structured database retrieval."""

    sql_database = get_sql_database()


    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["papers",
            "authors",
            "paper_authors",
            "keywords",
            "paper_keywords",
            "citations"],
        verbose=True,
    )
    logger.info("✓ SQL query engine created successfully")
    return query_engine
