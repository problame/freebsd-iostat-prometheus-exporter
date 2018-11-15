from prometheus_client import start_http_server
from prometheus_client import Gauge
import random
import time
import csv
import subprocess
import argparse
import re

# FreeBSD 11.2
# iostat -d -x -I
#  extended device statistics  
#  device           r/i         w/i         kr/i         kw/i qlen   tsvc_t/i      sb/i  
#  ada0     152107298.0 125540885.0 5735055021.5 2229765260.0    0  1553713.6  533244.6 
#  ada1     125377350.0 110274911.0 5287982655.5 1927673808.0    0  1250686.8  501403.8 
#  ada2     150081271.0 125135072.0 5734430679.5 2229871320.0    0  1609626.7  540002.8 
#  ada3     127434730.0 110570626.0 5281861627.5 1931709652.0    0  1223981.7  496281.6 
#  ada4       7179450.0  12238803.0  256717844.5  302772572.0    0   162101.9  106368.8 
#  pass0          453.0         0.0        226.5          0.0    0        8.0       8.0 
#  pass1          451.0         0.0        225.5          0.0    0        7.3       7.3 
#  pass2          445.0         0.0        222.5          0.0    0        7.7       7.7 
#  pass3          439.0         0.0        219.5          0.0    0        7.4       7.4 
#  pass4          445.0         0.0        222.5          0.0    0       20.1      20.1 
#  pass5            0.0         0.0          0.0          0.0    0        0.0       0.0 

read_ops = Gauge('iostat_device_reads', '', ['device'])
write_ops = Gauge('iostat_device_writes', '', ['device'])
bytes_written = Gauge('iostat_device_bytes_written', '', ['device'])
bytes_read = Gauge('iostat_device_bytes_read', '', ['device'])

gauges = (
        # col name, gauge above, divisor
        ("r/i", read_ops,       1),
        ("w/i", write_ops,      1),
        ("kr/i", bytes_read,    1024),   
        ("kw/i", bytes_written, 1024),
)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="prometheus exporter for FreeBSD iostat(8)")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--addr", default="")
    parser.add_argument("--interval", type=int, default=5, help="interval at which iostat(8) is invoked to gather iostats since boot")
    parser.add_argument("--device-filter-regex", help="regex by which to filter rows by the device column, e.g. '^(?!pass).*' ")
    parser.add_argument("--debug", default=False, action='store_true')
    args = parser.parse_args()

    device_filter_regex = re.compile(args.device_filter_regex) if args.device_filter_regex else re.compile(".*")

    start_http_server(args.port, addr=args.addr)

    while True:
        iostat_out = subprocess.check_output(["iostat", "-d", "-x", "-I"])
        #print(iostat_out)
        iostat_out = iostat_out.decode("ascii")
        csv_lines = iostat_out.splitlines()[1:]
        #print(csv_lines)

        coltitles = csv_lines[0].split()
        #print(coltitles)

        rows = [] # of dicts
        for row in csv_lines[1:]:
            cols = row.split()
            assert(len(coltitles) == len(cols))
            #print(cols)
            rowdict = dict(list(zip(coltitles, cols)))
            rows.append(rowdict)

        rows = filter(lambda row: device_filter_regex.search(row['device']), rows)
        for row in rows:
            if args.debug:
                print(row)
            for (colname, gauge, divisor) in gauges:
                val = float(row[colname])
                val = val / divisor
                gauge.labels([row['device']]).set(val)

        time.sleep(args.interval)
