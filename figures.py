import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from analyze import *
import argparse
import os

if not os.path.exists("figures"):
    os.makedirs("figures")

VULKAN_DB_PATH = "dbs/vulkan.db"
WEBGPU_DB_PATH = "dbs/gpuharbor.db"

matplotlib.rcParams['text.usetex'] = True

vulkan_devices = ["Adreno 610", "Adreno 640", "Adreno 642L", "Adreno 660", "Mali - G71", "Mali - G78", "GE8320", "Tegra X1"]

vulkan_vendors = ["PowerVR", "Arm", "Qualcomm", "NVIDIA"]

vulkan_db_vendor_order = ["PowerVR", "arm", "qualcomm", "nvidia"]

webgpu_vendors = ["Intel", "Apple", "NVIDIA", "AMD"]

webgpu_db_vendor_order = ["intel", "apple", "nvidia", "amd"]

def pct(value, total=1):
    return value/total * 100

def round_number(num):
    if num == int(num):
        res = int(num)
    else:
        res = round(num, 2)
    return "{}\%".format(res)

def build_table(labels, mp_data, lb_data, sb_data, s_data, r_data, w_data):
    for i in range(len(labels)):
        print("{} & {} & {} & {} & {} & {} & {} \\\\".format(labels[i], round_number(mp_data[i]), round_number(lb_data[i]), round_number(sb_data[i]), round_number(s_data[i]), round_number(r_data[i]), round_number(w_data[i])))

def vulkan_rates():
    cursor = db_conn(VULKAN_DB_PATH)
    data = analyze(cursor, "indiv", None, True, False)
    mp_rates = []
    lb_rates = []
    sb_rates = []
    s_rates = []
    r_rates = []
    w_rates = []
    for key in data:
        rates = data[key]["avgRates"]
        mp_rates.append(pct(rates["Message Passing Default"]))
        lb_rates.append(pct(rates["Load Buffer Default"]))
        sb_rates.append(pct(rates["Store Buffer Default"]))
        s_rates.append(pct(rates["Store Default"]))
        r_rates.append(pct(rates["Read Default"]))
        w_rates.append(pct(rates["2+2 Write Default"]))

    build_table(vulkan_devices, mp_rates, lb_rates, sb_rates, s_rates, r_rates, w_rates)

def webgpu_rates():
    cursor = db_conn(WEBGPU_DB_PATH)
    data = analyze(cursor, "vendor", None, False, False)
    all_data = analyze(cursor, "all", None, False, False)
    mp_rates = []
    lb_rates = []
    sb_rates = []
    s_rates = []
    r_rates = []
    w_rates = []
    for key in webgpu_db_vendor_order:
        rates = data[key]["avgRates"]
        mp_rates.append(pct(rates["messagePassingCoherencyTuning"]))
        lb_rates.append(pct(rates["loadBufferCoherencyTuning"]))
        sb_rates.append(pct(rates["storeBufferCoherencyTuning"]))
        s_rates.append(pct(rates["storeCoherencyTuning"]))
        r_rates.append(pct(rates["readCoherencyTuning"]))
        w_rates.append(pct(rates["twoPlusTwoWriteCoherencyTuning"]))

    rates = all_data["all"]["avgRates"]
    mp_rates.append(pct(rates["messagePassingCoherencyTuning"]))
    lb_rates.append(pct(rates["loadBufferCoherencyTuning"]))
    sb_rates.append(pct(rates["storeBufferCoherencyTuning"]))
    s_rates.append(pct(rates["storeCoherencyTuning"]))
    r_rates.append(pct(rates["readCoherencyTuning"]))
    w_rates.append(pct(rates["twoPlusTwoWriteCoherencyTuning"]))

    labels = webgpu_vendors + ["All"]

    x = np.arange(len(labels))
    y = np.arange(0, 11, 2)
    width = 0.1

    def make_fig(mp, lb, sb, s, r, w, label, fig_name):

        fig, ax = plt.subplots(1, 1, figsize=(6, 3))

        ax.bar(x - 2.5 * width, mp, width, label="MP")
        ax.bar(x - 1.5 * width, lb, width, label="LB")
        ax.bar(x - .5 * width, sb, width, label="SB")
        ax.bar(x + .5 * width, s, width, label="S")
        ax.bar(x + 1.5 * width, r, width, label="R")
        ax.bar(x + 2.5 * width, w, width, label="2+2W")

        y = [0, .1, 1, 5]
        pct_labels=["", "0.1\%", "1\%", "5\%"]
        ax.set_xticks(x, labels, fontsize=12)
        ax.set_yscale('symlog')
        ax.set_yticks(y, pct_labels, fontsize=10)
        ax.set_ylabel("{} Weak Behavior Percentage".format(label), fontsize=12)

        fig.legend(loc=(0.15, 0.7), fontsize=10, ncol=2)
        plt.tight_layout(rect=[0,0,1,1])
        plt.savefig("figures/webgpu-{}.pdf".format(fig_name))

    print("Writing WebGPU weak behavior rates")
    make_fig(mp_rates, lb_rates, sb_rates, s_rates, r_rates, w_rates, "Average", "rates")

def webgpu_similarity():
    def _round(val):
        return round(val, 3)
    cursor = db_conn(WEBGPU_DB_PATH)
    print("Vendor & Avg & Median & Min & Max \\\\")
    for i in range(len(webgpu_db_vendor_order)):
        vendor = webgpu_db_vendor_order[i]
        sim = similarity(cursor, vendor, False)
        print("{} & {} & {} & {} & {} \\\\".format(webgpu_vendors[i], _round(sim["avg"]), _round(sim["median"]), _round(sim["min"]), _round(sim["max"])))
    sim = similarity(cursor, None, False)
    print("All & {} & {} & {} & {} \\\\".format(_round(sim["avg"]), _round(sim["median"]), _round(sim["min"]), _round(sim["max"])))

def webgpu_kmeans():
    def vendor_value(counts, vendor):
        if vendor in counts:
            return counts[vendor]
        return 0
    cursor = db_conn(WEBGPU_DB_PATH)
    sim_res = similarity(cursor, None, False)
    distortions = []
    for i in range(1, 11):
        kmeans_res = kmeans(sim_res, i)
        distortions.append(kmeans_res["inertia"])
    good_kmeans = kmeans(sim_res, 6)
    for i in range(len(webgpu_db_vendor_order)):
        vendor = webgpu_db_vendor_order[i]
        print("{} & {} & {} & {} & {} & {} & {} \\\\".format(webgpu_vendors[i], vendor_value(good_kmeans["0"]["counts"], vendor), vendor_value(good_kmeans["1"]["counts"], vendor), vendor_value(good_kmeans["2"]["counts"], vendor), vendor_value(good_kmeans["3"]["counts"], vendor), vendor_value(good_kmeans["4"]["counts"], vendor), vendor_value(good_kmeans["5"]["counts"], vendor)))

def vulkan_summary():
    def round_millions(value):
        return round(value/1000000, 1)
    def round_thousands(value):
        return round(value/1000, 1)

    cursor = db_conn(VULKAN_DB_PATH)
    data = analyze(cursor, "vendor", None, True, False)
    all_data = analyze(cursor, "all", None, True, False)
    for i in range(len(vulkan_db_vendor_order)):
        vendor = vulkan_db_vendor_order[i]
        print("& {} & {} ({}) & {}m & {}k \\\\".format(vulkan_vendors[i], data[vendor]["total"], data[vendor]["uniqueDevices"], round_millions(data[vendor]["weakTestInstances"]), round_thousands(data[vendor]["weakBehaviors"])))
    print("All & {} ({}) & {}m & {}k".format(all_data["all"]["total"], all_data["all"]["uniqueDevices"], round_millions(all_data["all"]["weakTestInstances"]), round_thousands(all_data["all"]["weakBehaviors"])))

def webgpu_summary():
    def round_billions(value):
        return round(value/1000000000, 1)
    def round_millions(value):
        return round(value/1000000, 1)

    cursor = db_conn(WEBGPU_DB_PATH)
    data = analyze(cursor, "vendor", None, False, False)
    all_data = analyze(cursor, "all", None, False, False)
    for i in range(len(webgpu_db_vendor_order)):
        vendor = webgpu_db_vendor_order[i]
        print("& {} & {} ({}) & {}b & {}m \\\\".format(webgpu_vendors[i], data[vendor]["total"], data[vendor]["uniqueDevices"], round_billions(data[vendor]["weakTestInstances"]), round_millions(data[vendor]["weakBehaviors"])))
    print("All & {} ({}) & {}b & {}m".format(all_data["all"]["total"], all_data["all"]["uniqueDevices"], round_billions(all_data["all"]["weakTestInstances"]), round_millions(all_data["all"]["weakBehaviors"])))

def webgpu_timing():
    cursor = db_conn(WEBGPU_DB_PATH)
    data = analyze(cursor, "vendor", None, False, False)
    times = []
    for vendor in webgpu_db_vendor_order:
        times.append(data[vendor]["times"])
    fig, ax = plt.subplots(1, 1, figsize=(6, 3))
    ax.hist(times, bins="fd", label=webgpu_vendors, stacked=True)
    x = np.arange(0, 8100, 900)
    x_labels = [0, 15, 30, 45, 60, 75, 90, 120, 150]
    ax.set_xticks(x, x_labels, fontsize=12)
    ax.set_ylabel("Number of Results", fontsize=12)
    ax.set_xlabel("Testing Time (minutes)", fontsize=12)
    fig.legend(loc=(0.8, 0.66), fontsize=10, ncol=1)
    plt.tight_layout(rect=[0,0,1,1])
    print("Writing WebGPU timing information")
    plt.savefig("figures/webgpu-timing.pdf")

def bug_corr():
    g71_corr = correlate(load_stats("corr-analysis/mali_g71_mp_co.json"))
    g78_corr = correlate(load_stats("corr-analysis/mali_g78_mp_co.json"))
    shield_corr = correlate(load_stats("corr-analysis/shield_mp_co.json"))

    print("Arm Mali G71: MP/MP-CO Correlation: {}".format(round(g71_corr.loc['messagePassingCoherency', 'messagePassingCoherencyTuning'], 3)))
    print("Arm Mali G78: MP/MP-CO Correlation: {}".format(round(g78_corr.loc['messagePassingCoherency', 'messagePassingCoherencyTuning'], 3)))
    print("NVIDIA Tegra X1: MP/MP-CO Correlation: {}".format(round(shield_corr.loc['messagePassingCoherency', 'messagePassingCoherencyTuning'], 3)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--webgpu-summary", action="store_true", help="Calculate summary of WebGPU devices/tests")
    parser.add_argument("--webgpu-timing", action="store_true", help="Calculate summary of WebGPU test timing")
    parser.add_argument("--webgpu-rates", action="store_true", help="Calculate WebGPU weak rate behavior")
    parser.add_argument("--webgpu-similarity", action="store_true", help="Calculate WebGPU device similarity statistics")
    parser.add_argument("--webgpu-kmeans", action="store_true", help="Calculate WebGPU kmeans clustering")
    parser.add_argument("--vulkan-summary", action="store_true", help="Calculate summary of Vulkan devices/tests")
    parser.add_argument("--vulkan-rates", action="store_true", help="Calculate Vulkan weak rate behavior")
    parser.add_argument("--bug-corr", action="store_true", help="Calculate correlation between mutants and bugs")

    args = parser.parse_args()
    if args.webgpu_summary:
        webgpu_summary()
    elif args.webgpu_timing:
        webgpu_timing()
    elif args.webgpu_rates:
        webgpu_rates()
    elif args.webgpu_similarity:
        webgpu_similarity()
    elif args.webgpu_kmeans:
        webgpu_kmeans()
    elif args.vulkan_summary:
        vulkan_summary()
    elif args.vulkan_rates:
        vulkan_rates()
    elif args.bug_corr:
        bug_corr()

if __name__ == "__main__":
    main()
