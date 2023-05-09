import argparse
import json
import sqlite3
import re
import pandas
import csv
from statistics import median
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from os import remove


weakening_sw_tests = ["messagePassing", "messagePassingBarrier1", "messagePassingBarrier2", "loadBuffer", "loadBufferBarrier1", "loadBufferBarrier2", "store", "storeBarrier1", "storeBarrier2", "readRMW", "readRMWBarrier1", "readRMWBarrier2", "storeBufferRMW", "storeBufferRMWBarrier1", "storeBufferRMWBarrier2", "twoPlusTwoWriteRMW", "twoPlusTwoWriteRMWBarrier1", "twoPlusTwoWriteRMWBarrier2"]

weakening_po_loc_tests = ["messagePassingCoherencyTuning", "loadBufferCoherencyTuning", "storeBufferCoherencyTuning", "storeCoherencyTuning", "readCoherencyTuning", "twoPlusTwoWriteCoherencyTuning"]

conformance_tests = ["messagePassingBarrier", "loadBufferBarrier", "storeBufferRMWBarrier", "storeBarrier", "readRMWBarrier", "twoPlusTwoWriteRMWBarrier", "rr", "rw", "wr", "ww"] + weakening_po_loc_tests

vulkan_weak_mem_tests = ["Message Passing Default", "Store Default", "Read Default", "Load Buffer Default", "Store Buffer Default", "2+2 Write Default"]

reversing_po_loc_tests = ["rrMutant", "rrRMWMutant", "rwMutant", "rwRMWMutant", "wrMutant", "wrRMWMutant", "wwMutant", "wwRMWMutant"]

all_tuning_tests = weakening_sw_tests + weakening_po_loc_tests + reversing_po_loc_tests

# Pattern for checking that key matches a number
iter_p = re.compile('\d+')

def load_stats(stats_path):
    """
    Load the file with the test run output
    """
    with open(stats_path, "r") as stats_file:
        dataset = json.loads(stats_file.read())
        return dataset


def total_behaviors(test_data):
    return test_data["seq"] + test_data["interleaved"] + test_data["weak"]

def run_query(cursor, vendor, is_legacy, mobile):
    query = "select rowid, results from tuning_results"
    if vendor:
        query += " where gpu_vendor = '{}'".format(vendor)
    if not mobile and not is_legacy:
        if vendor:
            query += " and "
        else:
            query += " where "
        query += "os != '{}'".format("Android")
    return cursor.execute(query)

# Make sure every test has completed the expected number of test instances
def checksum(dataset):
    for key in dataset:
        if iter_p.match(key):
            wg = dataset[key]["params"]["testingWorkgroups"]
            iterations = dataset[key]["params"]["iterations"]
            wg_size = dataset[key]["params"]["workgroupSize"]
            for test in dataset[key]:
                if test != "params":
                    expected = iterations * wg * wg_size
                    if total_behaviors(dataset[key][test]) != expected:
                        print("Checksum did not match! Iteration: {}, Test: {}, Expected: {}, Actual: {}".format(key, test, expected, total))
                        return False
    return True

def db_conn(db_path):
    con = sqlite3.connect(db_path)
    return con.cursor()

def stats_per_test(dataset, is_legacy):
    result = {}
    test_results = {}
    bug_results = {}
    time = 0
    weak_test_instances = 0
    weak_behaviors = 0
    # Sometimes the computer goes to sleep. We don't want to count all the time it was asleep, so as a hack we just double the next test's time
    multiplier = 1
    for key in dataset:
        # Only match keys that are iteration numbers
        if iter_p.match(key):
            for test_key in dataset[key]:
                if test_key != "params":
                    test_data = dataset[key][test_key]
                    if "durationSeconds" in test_data:
                        # Looking through the data, there is no case where tests consistently take longer than a minute, so should be a case
                        # that the computer went to sleep
                        if test_data["durationSeconds"] > 60:
                            multiplier += 1
                        else:
                            time += test_data["durationSeconds"] * multiplier
                            multiplier = 1
                    total = total_behaviors(test_data)
                    weak = test_data["weak"]
                    if test_key in weakening_sw_tests or test_key in weakening_po_loc_tests or test_key in conformance_tests:
                        weak_test_instances += total
                        weak_behaviors += weak
                    elif is_legacy and test_key in vulkan_weak_mem_tests:
                        weak_test_instances += total
                        weak_behaviors += weak
                    behavior_rate = weak/total
                    # Only calculate best rates for non-conformance tests
                    if len(dataset[key].keys()) > 2:
                        # We find the best parameter configuration based on the ratio of weak behaviors to total behaviors
                        if test_key not in test_results or behavior_rate > test_results[test_key]["behavior_rate"]:
                            test_results[test_key] = {
                                "iteration": key,
                                "behavior_rate": behavior_rate
                            }
                    else:
                        # For conformance tests, look for bugs
                        if behavior_rate > 0 and test_key in conformance_tests:
                            if test_key not in bug_results or behavior_rate > bug_results[test_key]["behavior_rate"]:
                                bug_results[test_key] = {
                                    "iteration": key,
                                    "behavior_rate": behavior_rate
                                }
    result["tests"] = test_results
    result["bugs"] = bug_results
    result["time"] = time
    result["weakTestInstances"] = weak_test_instances
    result["weakBehaviors"] = weak_behaviors
    #print("GPU: " + device_str(dataset["platformInfo"]["gpu"]) + " time: " + str(time))
    return result


def init_weak_mem_counts(is_legacy):
    res = {}
    if is_legacy:
        tests = vulkan_weak_mem_tests
    else:
        tests = weakening_po_loc_tests
    for test in tests:
        res[test] = 0
    return res

def init_weak_mem_rates(is_legacy):
    res = {}
    if is_legacy:
        tests = vulkan_weak_mem_tests
    else:
        tests = weakening_po_loc_tests
    for test in tests:
        res[test] = []
    return res

def init_weak_mem_maxes(is_legacy):
    res = {}
    if is_legacy:
        tests = vulkan_weak_mem_tests
    else:
        tests = weakening_po_loc_tests
    for test in tests:
        res[test] = {
            "rowid": 0,
            "rate": 0,
            "device": ""
        }
    return res

def init_weak_mem_mins(is_legacy):
    res = {}
    if is_legacy:
        tests = vulkan_weak_mem_tests
    else:
        tests = weakening_po_loc_tests
    for test in tests:
        res[test] = {
            "rowid": 0,
            "rate": 1,
            "device": ""
        }
    return res


def update_weak_mem_rates(results, key, rowid, data, stats, is_legacy):
    if is_legacy:
        tests = vulkan_weak_mem_tests
    else:
        tests = weakening_po_loc_tests
    for test in tests:
        results[key]["rates"][test].append(stats["tests"][test]["behavior_rate"])
        if stats["tests"][test]["behavior_rate"] > 0:
            results[key]["counts"][test] += 1
        if stats["tests"][test]["behavior_rate"] > results[key]["maxRates"][test]["rate"]:
            results[key]["maxRates"][test] = {
                "rowid": rowid,
                "rate": stats["tests"][test]["behavior_rate"],
                "device": device_str(data["platformInfo"]["gpu"])
            }
        if stats["tests"][test]["behavior_rate"] < results[key]["minRates"][test]["rate"]:
            results[key]["minRates"][test] = {
                "rowid": rowid,
                "rate": stats["tests"][test]["behavior_rate"],
                "device": device_str(data["platformInfo"]["gpu"])
            }


def init_group_by(results, key, is_legacy):
    # rates is the average rate of weak behaviors per test, while count is
    # the number of devices that show weak behaviors per test
    results[key] = {
        "total": 0,
        "weakTestInstances": 0,
        "weakBehaviors": 0,
        "time": 0,
        "times": [],
        "rates": init_weak_mem_rates(is_legacy),
        "counts": init_weak_mem_counts(is_legacy),
        "maxRates": init_weak_mem_maxes(is_legacy),
        "minRates": init_weak_mem_mins(is_legacy),
        "devices": {},
        "uniqueDevices": 0,
        "platforms": {}
    }

def update_group_by(results, key, rowid, data, stats, is_legacy):
    results[key]["total"] += 1
    results[key]["time"] += stats["time"]
    results[key]["times"].append(stats["time"])
    results[key]["weakTestInstances"] += stats["weakTestInstances"]
    results[key]["weakBehaviors"] += stats["weakBehaviors"]
    update_weak_mem_rates(results, key, rowid, data, stats, is_legacy)
    vendor_arch = arch_str(data["platformInfo"]["gpu"])
    description = description_str(data["platformInfo"]["gpu"])
    new_arch = False
    if vendor_arch not in results[key]["devices"]:
        results[key]["devices"][vendor_arch] = {}
        results[key]["uniqueDevices"] += 1
        new_arch = True
    if description not in results[key]["devices"][vendor_arch]:
        results[key]["devices"][vendor_arch][description] = 1
        if not new_arch:
            results[key]["uniqueDevices"] += 1
    else:
        results[key]["devices"][vendor_arch][description] += 1
    if not is_legacy:
        platform = data["platformInfo"]["os"]["vendor"]
        if not platform:
            platform = "unknown"
        if platform not in results[key]["platforms"]:
            results[key]["platforms"][platform] = 1
        else:
            results[key]["platforms"][platform] += 1


def arch_str(gpu_info):
    if "architecture" in gpu_info:
        return gpu_info["vendor"] + " " + gpu_info["architecture"]
    else:
        return gpu_info["vendor"]

def description_str(gpu_info):
    if "description" in gpu_info:
        return gpu_info["description"]
    return ""

def device_str(gpu_info):
    if "architecture" in gpu_info:
        arch_str = gpu_info["architecture"]
    else:
        arch_str = ""
    if "description" in gpu_info and gpu_info["description"]:
        return gpu_info["vendor"] + " " + arch_str + " " + gpu_info["description"]
    if arch_str:
        return gpu_info["vendor"] + " " + arch_str
    else:
        return gpu_info["vendor"]

def analyze(cursor, group_by, vendor, is_legacy, mobile):
    results = {}
    for row in run_query(cursor, vendor, is_legacy, mobile):
        data = json.loads(row[1])
        stats = stats_per_test(data, is_legacy)
        if group_by == "indiv":
            # Every row gets its own total
            init_group_by(results, row[0], is_legacy)
            update_group_by(results, row[0], row[0], data, stats, is_legacy)
        elif group_by == "vendor":
            # Group by vendor
            vendor = data["platformInfo"]["gpu"]["vendor"]
            if vendor not in results:
                init_group_by(results, vendor, is_legacy)
            update_group_by(results, vendor, row[0], data, stats, is_legacy)
        elif group_by == "all":
            if "all" not in results:
                init_group_by(results, "all", is_legacy)
            update_group_by(results, "all", row[0], data, stats, is_legacy)
    for key in results:
        results[key]["avgRates"] = {}
        results[key]["medianRates"] = {}
        # Get the median and average rates per test
        for test in results[key]["rates"]:
            results[key]["avgRates"][test] = sum(results[key]["rates"][test])/results[key]["total"]
            results[key]["medianRates"][test] = median(results[key]["rates"][test])
    return results

def analyze_rowid(cursor, rowid, is_legacy):
    cursor.execute("select results from tuning_results where rowid = ?", [rowid])
    res = cursor.fetchone()
    data = json.loads(res[0])
    stats = stats_per_test(data, is_legacy)
    stats["platformInfo"] = data["platformInfo"]
    return stats

def find_bugs(cursor, vendor, is_legacy, mobile):
    bugs = {}
    for row in run_query(cursor, vendor, is_legacy ,mobile):
        data = json.loads(row[1])
        stats = stats_per_test(data, is_legacy)
        if stats["bugs"]:
            bugs[row[0]] = {
                "bugs": stats["bugs"],
                "device": device_str(data["platformInfo"]["gpu"])
            }
            if not is_legacy:
                bugs[row[0]]["platform"] = data["platformInfo"]["os"]["vendor"]
    totals = {}
    if not is_legacy:
        totals = {}
        for test in conformance_tests:
            totals[test] = 0
        for key in bugs:
            for test in conformance_tests:
                if test in bugs[key]["bugs"]:
                    totals[test] += 1
    return {
        "bugs": bugs,
        "totals": totals
    }

def similarity(cursor, vendor, mobile):
    data_file = open("temp.csv", 'w')
    csv_writer = csv.writer(data_file)
    vendor_indices = []
    for row in run_query(cursor, vendor, False, mobile):
        data = json.loads(row[1])
        csv_data = [device_str(data["platformInfo"]["gpu"])]
        vendor_indices.append(data["platformInfo"]["gpu"]["vendor"])
        for key in data:
            # Only match keys that are iteration numbers, and are tuning runs
            if iter_p.match(key) and len(data[key].keys()) > 2:
                for test_key in all_tuning_tests:
                    test_data = data[key][test_key]
                    csv_data += [test_data["interleaved"], test_data["weak"]]
        csv_writer.writerow(csv_data)
    data_file.close()
    df = pandas.read_csv("temp.csv", header=None, index_col = 0)
    remove("temp.csv")

    similarity = pandas.DataFrame(cosine_similarity(df))
    similarity.index = df.index
    similarity.columns = df.index

    all_sims = []
    for i in range(len(similarity.values)):
        for j in range(i):
            all_sims.append(similarity.values[i][j])
    return {
        "similarity": similarity,
        "vendor_indices": vendor_indices,
        "avg": sum(all_sims)/len(all_sims),
        "median": median(all_sims),
        "max": max(all_sims),
        "min": min(all_sims)
    }

def kmeans(similarity, num_clusters):
    sim_df = similarity["similarity"]
    vendor_indices = similarity["vendor_indices"]
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10).fit(sim_df)
    kmeans_res = {}
    labels = kmeans.labels_
    gpu_names = list(sim_df.index)
    for i in range(len(labels)):
        label = str(labels[i])
        if label not in kmeans_res:
            kmeans_res[label] = {
                "counts": {},
                "devices": []
            }
        if vendor_indices[i] not in kmeans_res[label]["counts"]:
            kmeans_res[label]["counts"][vendor_indices[i]] = 0
        kmeans_res[label]["counts"][vendor_indices[i]] += 1
        kmeans_res[label]["devices"].append(gpu_names[i])
    kmeans_res["inertia"] = kmeans.inertia_
    return kmeans_res

def correlate(dataset):
    data_file = open("temp.csv", 'w')
    csv_writer = csv.writer(data_file)
    first = True
    for key in dataset:
        if iter_p.match(key):
            row = []
            if first:
                for test_key in dataset[key]:
                    if test_key != "params":
                        row.append(test_key)
                first = False
                csv_writer.writerow(row)
                row = []
            for test_key in dataset[key]:
                if test_key != "params":
                    row.append(dataset[key][test_key]["weak"])
            csv_writer.writerow(row)
    data_file.close()
    df = pandas.read_csv("temp.csv")
    remove("temp.csv")
    return df.corr()


def print_json(value):
    print(json.dumps(value, indent=2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", help="Path to sqlite database")
    parser.add_argument("--rowid", help="Specify a specific row to analyze")
    parser.add_argument("--bugs", action="store_true", help="Show all bugs found")
    parser.add_argument("--mobile", action="store_true", help="Analyze mobile results")
    parser.add_argument("--checksum", action="store_true", help="Perform checksums when analyzing")
    parser.add_argument("--legacy", action="store_true", help="Analyzing legacy results requires some hacks")
    parser.add_argument("--avg", help="Average weak behaviors by grouping. Options: indiv, vendor, arch, all")
    parser.add_argument("--vendor", help="Only return results from this vendor")
    parser.add_argument("--similarity", action="store_true", help="Calculate similarity between datasets")
    parser.add_argument("--kmeans", help="Calculate kmeans clusters")
    parser.add_argument("--corr", help="Calculate the correlation between weak behaviors of the specified dataset")
    args = parser.parse_args()
    cursor = db_conn(args.db_path)
    if args.rowid:
        print_json(analyze_rowid(cursor, int(args.rowid), args.legacy))
    elif args.bugs:
        print_json(find_bugs(cursor, args.vendor, args.legacy, args.mobile))
    elif args.avg:
        print_json(analyze(cursor, args.avg, args.vendor, args.legacy, args.mobile))
    elif args.similarity:
        res = similarity(cursor, args.vendor, args.mobile)
        res["similarity"].to_csv("similarity.csv")
    elif args.kmeans:
        sim_res = similarity(cursor, args.vendor, args.mobile)
        print_json(kmeans(sim_res, int(args.kmeans)))
    elif args.corr:
        print(correlate(load_stats(args.corr)))

if __name__ == "__main__":
    main()
