import os, sys
import csv
import datetime
import json
import subprocess
import time

import snowflake.connector

def snowflake_connection(database, username=None, password=None):
    return snowflake.connector.connect(
        user=username or os.environ["DBT_PROFILES_USER"],
        password=password or os.environ["DBT_PROFILES_PASSWORD"],
        account="global.eu-west-1",
        database=database,
        role="dev_engineer"
    )

def datetime_from_iso(iso):
    suffix = "Z" if iso.endswith("Z") else ""
    return datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%f" + suffix)

MERGE_SQL = """MERGE INTO
  admin.nodes
USING
(
  SELECT
    %s AS name,
    %s AS status,
    %s AS last_built_by_job_id,
    %s AS last_started_at,
    %s AS last_finished_at
) AS params
ON
  params.NAME = nodes.NAME
WHEN MATCHED THEN UPDATE SET
  status = params.status,
  last_built_by_job_id = params.last_built_by_job_id,
  last_started_at = COALESCE(params.last_started_at, nodes.last_started_at),
  last_finished_at = params.last_finished_at
WHEN NOT MATCHED THEN INSERT
(
  NAME,
  status,
  last_built_by_job_id,
  last_started_at,
  last_finished_at
)
VALUES
(
  params.NAME,
  params.status,
  params.last_built_by_job_id,
  params.last_started_at,
  params.last_finished_at
)
;"""

def main(job_id=None):
    job_id = job_id or os.getlogin() + "-" + time.strftime("%Y%m%d-%H%M%S")
    print("Using Job Id", job_id)

    db = snowflake_connection("dw")
    db.cursor().execute("USE WAREHOUSE DWH_ETL_XSMALL;")

    open("logging.json", "w").close()

    for line in sys.stdin:
        with open("logging.json", "a") as f:
            f.write(line)

        try:
            djson = json.loads(line)
        except json.decoder.JSONDecodeError:
            print("Can't decode as JSON:", line.strip())
            continue

        ts = datetime_from_iso(djson["ts"])
        code = djson.get("code")
        invocation_id = djson.get("invocation_id")
        message = djson.get("msg")
        print(invocation_id, ts, code, message)

        with db.cursor() as q:
            q.execute(
                "INSERT INTO admin.logs (job_id, invocation_id, logged_at, message) VALUES (%s, %s, %s, %s)",
                [job_id, invocation_id, ts, message]
            )

        data = djson['data']
        if code in ("Q033", "Q012"):
            node_info = data['node_info']
            node_name = node_info['node_name']
            node_started_at = node_info.get('node_started_at')
            node_finished_at = node_info.get('node_finished_at')
            started_at = datetime_from_iso(node_started_at) if node_started_at else None
            status = data.get("status") or node_info.get('node_status')
            finished_at = datetime_from_iso(node_finished_at) if node_finished_at else None
            if status.lower().startswith("success") and not finished_at:
                finished_at = datetime.datetime.now()

            with db.cursor() as q:
                q.execute(MERGE_SQL, [node_name, status, job_id, started_at, finished_at])


def command_line():
    main(*sys.argv[1:])

if __name__ == '__main__':
    commandline()
