import numpy
import Gnuplot
import re

timestamp_re = re.compile(r"^\d+$")
throughput_re = re.compile(r"\[.*\]\s*(\d+)\.\d+-\d+\.\d+\s+sec\s+[0-9\.]+\s+\w+\s+([0-9\.]+)\s+(\w+)/sec\s+(\d+)\s+[0-9\.]+\s+\w+")
Kbps_re = re.compile(r"^Kbits")
Mbps_re = re.compile(r"^Mbits")
bps_re = re.compile(r"^bits")


def parse_iperf(file):
    start_timestamp = 0
    Kbps = []
    lines = file.readlines()
    for line in lines:
        if timestamp_re.match(line):
            start_timestamp = int(line.strip())
        elif throughput_re.match(line):
            matches = throughput_re.findall(line)[0]
            multiplier = 1
            if Kbps_re.match(matches[2]):
                multiplier = 1
            elif Mbps_re.match(matches[2]):
                multiplier = 1000
            elif bps_re.match(matches[2]):
                multiplier = 1.0/1000.0
            else:
                raise Exception("Throughput not in Kbps or Mbps or bps")
            Kbps.append((int(matches[0])+start_timestamp, float(matches[1])*multiplier))

    return Kbps

def overlap(*d):
    lower_bound = 0
    upper_bound = d[0][-1][0]
    for dataset in d:
        if dataset[0][0] > lower_bound:
            lower_bound = dataset[0][0]
        if dataset[-1][0] < upper_bound:
            upper_bound = dataset[-1][0]

    for dataset in d:
        while True:
            if dataset[0][0] < lower_bound:
                dataset.pop(0)
            elif dataset[-1][0] > upper_bound:
                dataset.pop(-1)
            else:
                break

def trim(n, *d):
    for dataset in d:
        del dataset[:n]
        del dataset[-n:]


def main():
    # client1_file = "0505de112bc529cd58065605de043de2c54e42e307b4cf0ad5ecb30cf97da90d.log"
    # client2_file = "8f1ca8f9ae1d79895f49c7fc285fbe9adc6305d25d2d50e3fc5e5d10cd9981b1.log"
    # client3_file = "0183ccfa2687d762f62ed01beb2ba4c4cc50afeb4c9c5b01e6d9a7320d70806f.log"

    client1_file = "c1.log"
    client2_file = "c2.log"
    client3_file = "c3.log"

    f = open(client1_file)
    d1 = parse_iperf(f)
    f.close()

    f = open(client2_file)
    d2 = parse_iperf(f)
    f.close()

    f = open(client3_file)
    d3 = parse_iperf(f)
    f.close()

    overlap(d1, d2, d3)
    trim(60, d1, d2, d3)

    t = numpy.array([x[0] for x in d1])
    c1 = numpy.array([x[1] for x in d1])
    c2 = numpy.array([x[1] for x in d2])
    c3 = numpy.array([x[1] for x in d3])
    s = c1+c2+c3

    data = [("Client1", c1, 17777),
            ("Client2", c2, 22222),
            ("Client3", c3, 10000),
            ("Total", s, 50000)]

    g = Gnuplot.Gnuplot()
    gd1 = Gnuplot.Data(c1, title="client1", with_="lines")
    gd2 = Gnuplot.Data(c2, title="client2", with_="lines")
    gd3 = Gnuplot.Data(c3, title="client3", with_="lines")
    gdsum = Gnuplot.Data(s, title="Total", with_="lines")

    g.plot(gd1, gd2, gd3, gdsum)

    for d in data:
        print(d[0])
        print(" expected: " + str(d[2]))
        print(" mean:     " + str(d[1].mean()))
        print(" max:      " + str(d[1].max()))
        print(" min:      " + str(d[1].min()))
        print(" dev:      " + str(d[1].std()))

if __name__ == '__main__':
    main()