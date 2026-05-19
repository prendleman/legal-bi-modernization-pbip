"""Databricks integration for the Sidley BI modernization demo.

Pushes generated CSVs into a Unity Catalog volume and registers them as
Delta gold tables backing the PBIP semantic model. Designed for a real
workspace, but defaults to --dry-run so the demo runs anywhere.

Configuration order of precedence:
1. Environment variables (DATABRICKS_HOST, DATABRICKS_TOKEN, ...)
2. databricks.config.json next to this file
3. Hard-coded safe defaults (catalog=sidley_demo, schema=gold, volume=landing)

Required env / config keys for live execution:
    DATABRICKS_HOST            e.g. https://adb-1234.5.azuredatabricks.net
    DATABRICKS_TOKEN           personal access token
    DATABRICKS_WAREHOUSE_ID    SQL warehouse id (for COPY INTO)
    DATABRICKS_HTTP_PATH       /sql/1.0/warehouses/<id>  (auto-derived if absent)
    DATABRICKS_CATALOG         default: sidley_demo
    DATABRICKS_SCHEMA          default: gold
    DATABRICKS_VOLUME          default: landing
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


GOLD_TABLES = [
    "dim_date",
    "dim_office",
    "dim_practice",
    "dim_client",
    "dim_attorney",
    "dim_matter",
    "fact_billings",
    "fact_time_entries",
    "fact_legacy_report_inventory",
    "fact_requirements_backlog",
    "fact_refresh_log",
]


@dataclass
class DatabricksConfig:
    host: str = ""
    token: str = ""
    warehouse_id: str = ""
    http_path: str = ""
    catalog: str = "sidley_demo"
    schema: str = "gold"
    volume: str = "landing"
    extra: dict = field(default_factory=dict)

    @property
    def full_volume_path(self) -> str:
        return f"/Volumes/{self.catalog}/{self.schema}/{self.volume}"

    def fq(self, table: str) -> str:
        return f"`{self.catalog}`.`{self.schema}`.`{table}`"

    def resolved_http_path(self) -> str:
        if self.http_path:
            return self.http_path
        if self.warehouse_id:
            return f"/sql/1.0/warehouses/{self.warehouse_id}"
        return ""

    def is_complete(self) -> bool:
        return bool(self.host and self.token and (self.warehouse_id or self.http_path))


def load_config(config_path: Optional[Path] = None) -> DatabricksConfig:
    cfg = DatabricksConfig()
    if config_path and config_path.exists():
        try:
            file_cfg = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON in {config_path}: {exc}") from exc
        for key, value in file_cfg.items():
            if hasattr(cfg, key) and value not in (None, ""):
                setattr(cfg, key, value)

    env_map = {
        "DATABRICKS_HOST": "host",
        "DATABRICKS_TOKEN": "token",
        "DATABRICKS_WAREHOUSE_ID": "warehouse_id",
        "DATABRICKS_HTTP_PATH": "http_path",
        "DATABRICKS_CATALOG": "catalog",
        "DATABRICKS_SCHEMA": "schema",
        "DATABRICKS_VOLUME": "volume",
    }
    for env_key, attr in env_map.items():
        env_val = os.environ.get(env_key)
        if env_val:
            setattr(cfg, attr, env_val)

    if cfg.host and not cfg.host.startswith(("http://", "https://")):
        cfg.host = "https://" + cfg.host
    cfg.host = cfg.host.rstrip("/")
    return cfg


class DatabricksClient:
    """Thin facade over databricks-sdk + databricks-sql-connector.

    All write operations honor `dry_run`. When dry_run=True, every SDK call
    and SQL statement is logged at INFO level but never executed, so the
    full pipeline can be rehearsed locally without credentials.
    """

    def __init__(
        self,
        config: DatabricksConfig,
        dry_run: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.cfg = config
        self.dry_run = dry_run
        self.log = logger or logging.getLogger("databricks_client")
        self._workspace = None
        self._sql_conn = None

    def __enter__(self) -> "DatabricksClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._sql_conn is not None:
            try:
                self._sql_conn.close()
            except Exception:
                pass
            self._sql_conn = None

    def _require_live(self, action: str) -> None:
        if self.dry_run:
            return
        if not self.cfg.is_complete():
            raise RuntimeError(
                f"Cannot {action}: missing host/token/warehouse. "
                "Set DATABRICKS_HOST, DATABRICKS_TOKEN, and "
                "DATABRICKS_WAREHOUSE_ID (or DATABRICKS_HTTP_PATH), "
                "or pass --dry-run."
            )

    def _workspace_client(self):
        if self._workspace is not None:
            return self._workspace
        try:
            from databricks.sdk import WorkspaceClient
        except ImportError as exc:
            raise RuntimeError(
                "databricks-sdk is not installed. Run: pip install databricks-sdk"
            ) from exc
        self._workspace = WorkspaceClient(host=self.cfg.host, token=self.cfg.token)
        return self._workspace

    def _sql_connection(self):
        if self._sql_conn is not None:
            return self._sql_conn
        try:
            from databricks import sql as dbsql
        except ImportError as exc:
            raise RuntimeError(
                "databricks-sql-connector is not installed. "
                "Run: pip install databricks-sql-connector"
            ) from exc
        self._sql_conn = dbsql.connect(
            server_hostname=self.cfg.host.replace("https://", "").replace("http://", ""),
            http_path=self.cfg.resolved_http_path(),
            access_token=self.cfg.token,
        )
        return self._sql_conn

    def _execute_sql(self, statement: str) -> None:
        compact = " ".join(statement.split())
        if len(compact) > 240:
            compact = compact[:237] + "..."
        self.log.info("[SQL] %s", compact)
        if self.dry_run:
            return
        conn = self._sql_connection()
        with conn.cursor() as cur:
            cur.execute(statement)

    def ensure_catalog_schema_volume(self) -> None:
        self._require_live("create catalog/schema/volume")
        self.log.info(
            "Ensuring catalog=%s schema=%s volume=%s",
            self.cfg.catalog,
            self.cfg.schema,
            self.cfg.volume,
        )
        self._execute_sql(
            f"CREATE CATALOG IF NOT EXISTS `{self.cfg.catalog}` "
            f"COMMENT 'Sidley BI modernization demo'"
        )
        self._execute_sql(
            f"CREATE SCHEMA IF NOT EXISTS `{self.cfg.catalog}`.`{self.cfg.schema}` "
            f"COMMENT 'Curated gold layer for the legal BI modernization demo'"
        )
        self._execute_sql(
            f"CREATE VOLUME IF NOT EXISTS "
            f"`{self.cfg.catalog}`.`{self.cfg.schema}`.`{self.cfg.volume}` "
            f"COMMENT 'CSV landing zone for gold tables'"
        )

    def upload_csvs(self, data_dir: Path, tables: Iterable[str] = GOLD_TABLES) -> None:
        self._require_live("upload CSVs to UC volume")
        target_root = self.cfg.full_volume_path
        self.log.info("Uploading CSVs from %s -> %s", data_dir, target_root)
        if self.dry_run:
            for table in tables:
                src = data_dir / f"{table}.csv"
                self.log.info("[FILES.upload] %s -> %s/%s.csv", src, target_root, table)
            return
        ws = self._workspace_client()
        for table in tables:
            src = data_dir / f"{table}.csv"
            if not src.exists():
                raise FileNotFoundError(src)
            target = f"{target_root}/{table}.csv"
            self.log.info("Uploading %s", target)
            with src.open("rb") as fh:
                ws.files.upload(target, fh, overwrite=True)

    def create_gold_tables(self, ddl_path: Path) -> None:
        self._require_live("create gold tables")
        if not ddl_path.exists():
            raise FileNotFoundError(ddl_path)
        self.log.info("Executing gold-layer DDL from %s", ddl_path)
        statements = [
            s.strip()
            for s in ddl_path.read_text(encoding="utf-8").split(";")
            if s.strip() and not s.strip().startswith("--")
        ]
        for stmt in statements:
            self._execute_sql(stmt)

    def load_gold_from_volume(self, tables: Iterable[str] = GOLD_TABLES) -> None:
        self._require_live("load gold tables from volume")
        for table in tables:
            stmt = (
                f"COPY INTO {self.cfg.fq(table)} "
                f"FROM '{self.cfg.full_volume_path}/{table}.csv' "
                f"FILEFORMAT = CSV "
                f"FORMAT_OPTIONS ('header' = 'true', 'inferSchema' = 'false') "
                f"COPY_OPTIONS ('mergeSchema' = 'false', 'force' = 'true')"
            )
            self._execute_sql(stmt)

    def run_full_pipeline(self, data_dir: Path, ddl_path: Path) -> None:
        self.ensure_catalog_schema_volume()
        self.create_gold_tables(ddl_path)
        self.upload_csvs(data_dir)
        self.load_gold_from_volume()
        mode = "DRY RUN" if self.dry_run else "LIVE"
        self.log.info("Databricks pipeline complete (%s)", mode)


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
