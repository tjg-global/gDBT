#!python3
import os, sys
import re
import subprocess

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
    branch_prefix, _, _ = suffix.replace("-", "_").partition(" ")
    #
    # If we have a branch named, eg, feature/rd-123 or issue/rd-456
    # then we want the rd-xxx element (the suffix). If we have an unadorned
    # issue number or any of master, staging or production, there won't be
    # a suffix and we want the prefix
    #
    env_branch = branch_prefix or prefix
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

dbt_exe = os.path.expandvars("%VIRTUAL_ENV%\scripts\dbt.exe")
if env_name == "aat" and sys.argv[1].lower() in ["run", "compile", "test", "docs"]:
    print("About to set up dev branch")
    subprocess.run([dbt_exe, "run-operation", "setup_dev_branch"], env=environment)

subprocess.run([dbt_exe] + sys.argv[1:] + ['--target=%s' % target], env=environment)
