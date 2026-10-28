"""Small stateless storefront used to demonstrate the AWS architecture."""

from __future__ import annotations

import json
import os
import socket
from functools import lru_cache

import boto3
import pymysql
from flask import Flask, Response

app = Flask(__name__)
REGION = os.getenv("AWS_REGION", "us-east-1")
SECRET_ARN = os.environ["DB_SECRET_ARN"]
DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.getenv("DB_NAME", "appdb")
STATIC_URL = os.getenv("STATIC_ASSETS_URL", "").rstrip("/")


@lru_cache(maxsize=1)
def database_credentials() -> dict[str, str]:
    response = boto3.client("secretsmanager", region_name=REGION).get_secret_value(
        SecretId=SECRET_ARN
    )
    return json.loads(response["SecretString"])


def database_connection():
    credentials = database_credentials()
    return pymysql.connect(
        host=DB_HOST,
        user=credentials["username"],
        password=credentials["password"],
        database=DB_NAME,
        connect_timeout=3,
        read_timeout=3,
        write_timeout=3,
        autocommit=True,
    )


def page_count() -> int:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS page_counter "
                "(counter_name VARCHAR(32) PRIMARY KEY, visits BIGINT NOT NULL)"
            )
            cursor.execute(
                "INSERT INTO page_counter (counter_name, visits) VALUES ('home', 1) "
                "ON DUPLICATE KEY UPDATE visits = visits + 1"
            )
            cursor.execute(
                "SELECT visits FROM page_counter WHERE counter_name = 'home'"
            )
            return int(cursor.fetchone()[0])


@app.get("/healthz")
def healthz() -> Response:
    return Response("ok\n", status=200, mimetype="text/plain")


@app.get("/")
def home() -> Response:
    try:
        visits = page_count()
        db_message = f"Database connected · {visits:,} page views"
        db_class = "healthy"
        status = 200
    except Exception as exc:  # Keep the failure visible to a learner without leaking secrets.
        app.logger.exception("Database request failed")
        db_message = f"Database temporarily unavailable ({type(exc).__name__})"
        db_class = "degraded"
        status = 503

    css = f"{STATIC_URL}/site.css" if STATIC_URL else "/site.css"
    body = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ScaleLab | AWS reference app</title>
    <link rel="stylesheet" href="{css}">
  </head>
  <body>
    <main class="shell">
      <div class="eyebrow"><span class="pulse"></span> AWS SOLUTIONS ARCHITECT ASSOCIATE</div>
      <h1>ScaleLab</h1>
      <p class="lede">A small, stateless web app behind a multi-AZ load balancer.</p>
      <section class="status-card">
        <div class="status-icon">✓</div>
        <div><p class="label">LIVE STATUS</p><p class="status {db_class}">{db_message}</p></div>
      </section>
      <div class="details">
        <div><span>Served by</span><strong>{socket.gethostname()}</strong></div>
        <div><span>Data layer</span><strong>Amazon RDS · Multi-AZ</strong></div>
        <div><span>Compute</span><strong>EC2 Auto Scaling</strong></div>
      </div>
      <footer>Designed for availability, secure operations, and measured scale.</footer>
    </main>
  </body>
</html>"""
    return Response(body, status=status, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
