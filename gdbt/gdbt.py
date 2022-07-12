#!python3
import os, sys
import argparse
import re
import subprocess

def main(command, args):
    DIRNAMES_TO_IGNORE = {".venv", ".venv0", "dbt_modules"}
    for dirpath, dirnames, filenames in os.walk("."):
        if DIRNAMES_TO_IGNORE & set(os.path.normpath(dirpath.lower()).split(os.path.sep)):
            continue
        if any(filename == "dbt_project.yml" for filename in filenames):
            dbt_path = dirpath
            print("Switching to", os.path.abspath(dbt_path))
            os.chdir(dirpath)
            break

    output = subprocess.run(
        ["git", "status"],
        capture_output=True
    ).stdout.decode(sys.stdout.encoding)
    for branch in re.findall(r"On branch ([0-9a-zA-z/\-_]+)", output):
        prefix, _, suffix = branch.partition("/")
        branch_prefix, _, _ = suffix.partition(" ")
        #
        # If we have a branch named, eg, feature/rd-123 or issue/rd-456
        # then we want the rd-xxx element (the suffix). If we have an unadorned
        # issue number or any of master, staging or production, there won't be
        # a suffix and we want the prefix
        #
        env_branch = (branch_prefix or prefix).replace("-", "_")
        break
    else:
        env_branch = ""

    env_name = env_branch if env_branch in ('production', 'staging', 'master') else "aat"
    src_db_prefix = "aat_" if env_name in ("master", "aat") else "uat_" if env_name == "staging" else ""
    target = "aat" if env_name in ('aat', 'master') else env_branch

    environment = dict(os.environ)
    #
    # DBT_PROFILES_USER|PASSWORD (ie the Snowflake credentials)
    # are set in Windows as user env vars
    #
    dbt_profiles_dir = os.path.abspath(os.getcwd())
    if os.path.exists(os.path.join(dbt_profiles_dir, "profiles.yml")):
        environment["DBT_PROFILES_DIR"] = os.path.abspath(os.getcwd())
    environment["ENV_NAME"] = env_name
    environment["SRC_DB_PREFIX"] = src_db_prefix
    environment["ENV_BRANCH"] = env_branch

    for v in [
        "DBT_PROFILES_DIR",
        "ENV_NAME",
        "SRC_DB_PREFIX",
        "ENV_BRANCH"
    ]:
        print(v, "=>", environment.get(v))

    for dirpath, exe in [
        ("scripts", "dbt.exe"),
        ("bin", "dbt")
    ]:

        dbt_filepath = os.path.join(os.environ["VIRTUAL_ENV"], dirpath, exe)
        if os.path.exists(dbt_filepath):
            dbt_exe = dbt_filepath
            break
    else:
        raise RuntimeError("Unable to find a dbt executable in the virtual environment")

    #
    # If we're on a dev branch, but not master, set up the necessary databases
    #
    if env_name == "aat" and env_branch and command.lower() in ["run", "compile", "test", "docs", "seed"]:
        print("About to set up dev branch")
        subprocess.run([dbt_exe, "run-operation", "setup_dev_branch"], env=environment)

    subprocess.run([dbt_exe] + list(args) + ['--target=%s' % target], env=environment)

def command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    known_args, _ = parser.parse_known_args()
    main(known_args.command, sys.argv[1:])

if __name__ == '__main__':
    command_line()
