#!python3
import os, sys
import argparse
import re
import subprocess

def name_is_macro(name):
    #
    # By the time we get here our cwd should be the dbt root folder
    #
    macros_dirpath = "macros"
    return os.path.exists(os.path.join(macros_dirpath, name + ".sql"))

def find_dbt_root():
    DIRNAMES_TO_IGNORE = {".venv", ".venv0", "dbt_modules"}
    for dirpath, dirnames, filenames in os.walk("."):
        if DIRNAMES_TO_IGNORE & set(os.path.normpath(dirpath.lower()).split(os.path.sep)):
            continue
        if any(filename == "dbt_project.yml" for filename in filenames):
            dbt_path = dirpath
            print("Switching to", os.path.abspath(dbt_path))
            os.chdir(dirpath)
            return
    else:
        raise RuntimeError("Unable to find a dbt project")

def find_git_branch():
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
        return (branch_prefix or prefix).replace("-", "_")
    else:
        return ""

def find_dbt_executable():
    for dirpath, exe in [
        ("scripts", "dbt.exe"),
        ("bin", "dbt")
    ]:
        dbt_filepath = os.path.join(os.environ["VIRTUAL_ENV"], dirpath, exe)
        if os.path.exists(dbt_filepath):
            return dbt_filepath
    else:
        raise RuntimeError("Unable to find a dbt executable in the virtual environment")

def check_git_executable():
    try:
        subprocess.run(["git"], capture_output=True) # Don't bother checking the output
    except FileNotFoundError:
        raise RuntimeError("Unable to find Git")
    except OSError:
        raise RuntimeError("Unable to run Git")

def find_parameters(args):
    """Detect parameters of the form --abc=123

    Return a dictionary of name:value pairs
    """
    for arg in args:
        match = re.match(r"--([^=]+)=(\S+)", arg)
        if match:
            yield match.groups()

def run_macro(command, dbt_exe, environment, args):
    run_commands = [dbt_exe, "run-operation", command]
    vars = list(find_parameters(args))
    if vars:
        run_commands.append("--args")
        yaml_args = ", ".join("%s: %s" % var for var in vars)
        run_commands.append("{%s}" % yaml_args)
    subprocess.run(run_commands, env=environment)

def main(command, args):
    command = command.lower()
    find_dbt_root()
    dbt_exe = find_dbt_executable()
    check_git_executable()
    env_branch = find_git_branch()

    env_name = env_branch if env_branch in ('production', 'staging', 'master') else "aat"
    src_db_prefix = "aat_" if env_name in ("master", "aat") else "uat_" if env_name == "staging" else ""
    target = "aat" if env_name in ('aat', 'master', 'dev') else env_branch

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

    #
    # Check if we're being asked to run a macro
    #
    if name_is_macro(command):
        print("About to run macro", command)
        run_macro(command, dbt_exe, environment, args)

    else:
        #
        # If we're on a dev branch, but not master, set up the necessary databases
        #
        if env_name == "aat" and env_branch and command in ["run", "compile", "test", "docs", "seed"]:
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
