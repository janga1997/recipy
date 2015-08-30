import wrapt
import os
import datetime
import sys
import getpass
import platform
import sys
from tinydb import TinyDB
import uuid

from git import Repo

from recipyCommon.config import option_set
from recipyCommon.utils import open_or_create_db

RUN_ID = {}
CONFIG = None
store_diff = True


def get_origin(repo):
    try:
        return repo.remotes.origin.url
    except:
        return None

def new_run():
    log_init()

def log_init():
    global RUN_ID

    # Open the database
    db = open_or_create_db()

    # Create the unique ID for this run
    guid = str(uuid.uuid4())

    # Get the path of the script we're running
    scriptpath = os.path.realpath(sys.argv[0])

    # Get general metadata, environment info, etc
    run = {"unique_id": guid,
        "author": getpass.getuser(),
        "description": "",
        "inputs": [],
        "outputs": [],
        "script": scriptpath,
        "command": sys.executable,
        "environment": [platform.platform(), "python " + sys.version.split('\n')[0]],
        "date": datetime.datetime.utcnow()}

    if not option_set('ignored metadata', 'git'):
        try:
            repo = Repo(scriptpath, search_parent_directories=True)
            run["gitrepo"] = repo.working_dir
            run["gitcommit"] =  repo.head.commit.hexsha
            run["gitorigin"] = get_origin(repo)

            if not option_set('ignored metadata', 'diff'):
                whole_diff = ''
                diffs = repo.index.diff(None, create_patch=True)
                for diff in diffs:
                    whole_diff += "\n\n\n" + str(diff.diff)

                run['diff'] = whole_diff
        except (InvalidGitRepositoryError, ValueError):
            # We can't store git info for some reason, so just skip it
            pass

    # Put basics into DB
    RUN_ID = db.insert(run)
    print("recipy run inserted, with ID %s" % (guid))
    db.close()

def log_input(filename, source):
    filename = os.path.abspath(filename)
    if option_set('general', 'debug'):
        print("Input from %s using %s" % (filename, source))
    #Update object in DB
    db = open_or_create_db()
    db.update(append("inputs", filename), eids=[RUN_ID])
    db.close()

def log_output(filename, source):
    filename = os.path.abspath(filename)
    if option_set('general', 'debug'):
        print("Output to %s using %s" % (filename, source))
    #Update object in DB
    db = open_or_create_db()
    db.update(append("outputs", filename), eids=[RUN_ID])
    db.close()

def log_update(field, filename, source):
    filename = os.path.abspath(filename)
    print("Adding %s to %s using $s" % (field, filename, source))
    db = open_or_create_db()
    db.update(append(field, filename), eids=[RUN_ID])
    db.close()

def append(field, value):
    """
    Append a given value to a given array field.
    Keep an eye on https://github.com/msiemens/tinydb/issues/66
    """
    def transform(element):
        element[field].append(value)

    return transform


