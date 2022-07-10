import os, sys
import csv
import json
import subprocess

import snowflake.connect

def snowflake_connection(database="admin", username=None, password=None):
    return snowflake.connect(
        user=username or os.environ["DBT_PROFILES_USER"],
        password=password or os.environ["DBT_PROFILES_PASSWORD"],
        account="global.eu-west-1",
        database=database,
        warehouse="team_technology",
        role="dev_engineer",
    )

def main(job_prefix):
    print("Using prefix", job_prefix)

    with open("dbt.csv", "w", newline="") as f:
        csv.writer(f).writerow(["Job Id", "Logged At", "Code", "Message"])

    for line in sys.stdin:
        try:
            djson = json.loads(line)
        except json.decoder.JSONDecodeError:
            print("Can't decode as JSON; skipping")
            print(line)
        ts = djson.get("ts")
        code = djson.get("code")
        invocation_id = djson.get("invocation_id")
        message = djson.get("msg")
        print(invocation_id, ts, code, message)

        with open("dbt.csv", "a", newline="") as f:
            csv.writer(f).writerow([job_prefix + "-" + invocation_id, ts, code, message])

def commandline():
    main(*sys.argv[1:])

if __name__ == '__main__':
    commandline()
