import argparse
import json
import sqlite3
import re

def load_stats(stats_path):
    with open(stats_path, "r") as stats_file:
        dataset = json.loads(stats_file.read())
        return dataset

def db_conn(db_path):
    return sqlite3.connect(db_path)

def create_table(cursor):
    cursor.execute("""
      create table if not exists tuning_results (
        name text,
        email text,
        gpu_vendor text,
        browser text,
        os text,
        framework text,
        random_seed text,
        results text
      )
""")

def insert_res(con, data):
    cursor = con.cursor()
    create_table(cursor)
    if "userInfo" in data:
        name = data["userInfo"]["name"]
        email = data["userInfo"]["email"]
    else:
        name = ""
        email = ""
    if "browser" in data["platformInfo"]:
        browser = data["platformInfo"]["browser"]["vendor"]
    else:
        browser = ""
    if "os" in data["platformInfo"]:
        oper_sys = data["platformInfo"]["os"]["vendor"]
    else:
        oper_sys = ""
    data = {
        "name": name,
        "email": email,
        "gpu_vendor": data["platformInfo"]["gpu"]["vendor"],
        "browser": browser,
        "os": oper_sys,
        "framework": data["platformInfo"]["framework"],
        "random_seed": data["randomSeed"],
        "results": json.dumps(data)
    }
    cursor.execute("""
        INSERT INTO tuning_results
            (name, email, gpu_vendor, browser, os, framework, random_seed, results)
        VALUES
            (:name, :email, :gpu_vendor, :browser, :os, :framework, :random_seed, :results)
""", data)
    con.commit()

def create_legacy_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tuning_results (
            gpu_vendor text,
            results text
      )
""")

def insert_legacy_res(con, data):
    cursor = con.cursor()
    create_table(cursor)
    data = {
        "gpu_vendor": data["platformInfo"]["gpu"]["vendor"],
        "results": json.dumps(data)
    }
    cursor.execute("""
        INSERT INTO tuning_results
            (gpu_vendor, results)
        VALUES
            (:gpu_vendor, :results)
""", data)
    con.commit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", help="Path to sqlite database")
    parser.add_argument("data_path", help="Path to data to insert")
    parser.add_argument("--legacy", action="store_true", help="Insert legacy Android app results")
    args = parser.parse_args()
    con = db_conn(args.db_path)
    stats = load_stats(args.data_path)
    if args.legacy:
        insert_legacy_res(con, stats)
    else:
        insert_res(con, stats)

if __name__ == "__main__":
    main()
