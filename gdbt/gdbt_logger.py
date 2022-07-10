import os, sys
import csv
import datetime
import json
import subprocess

import snowflake.connector

def snowflake_connection(database, username=None, password=None):
    return snowflake.connector.connect(
        user=username or os.environ["DBT_PROFILES_USER"],
        password=password or os.environ["DBT_PROFILES_PASSWORD"],
        account="global.eu-west-1",
        database=database,
        warehouse="team_technology",
        role="dev_engineer",
    )

def main(job_id):
    print("Using prefix", job_id)

    db = snowflake_connection("dw")
    db.cursor().execute("USE WAREHOUSE DWH_ETL_XSMALL;")

    for line in sys.stdin:
        try:
            djson = json.loads(line)
        except json.decoder.JSONDecodeError:
            print("Can't decode as JSON; skipping:", line.strip())
            continue

        ts = datetime.datetime.strptime(djson.get("ts"), "%Y-%m-%dT%H:%M:%S.%fZ")
        code = djson.get("code")
        invocation_id = djson.get("invocation_id")
        message = djson.get("msg")
        print(invocation_id, ts, code, message)

        with db.cursor() as q:
            q.execute(
                "INSERT INTO admin.logs (job_id, invocation_id, logged_at, message) VALUES (%s, %s, %s, %s)",
                [job_id, invocation_id, ts, message]
            )


def commandline():
    main(*sys.argv[1:])

if __name__ == '__main__':
    commandline()
