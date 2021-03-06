#! /usr/bin/python
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from kollaps.Kollapslib.NetGraph import NetGraph
from kollaps.Kollapslib.XMLGraphParser import XMLGraphParser
from kollaps.Kollapslib.EmulationManager import EmulationManager
from kollaps.Kollapslib.utils import print_and_fail
from kollaps.Kollapslib.CommunicationsManager import CommunicationsManager
import kollaps.Kollapslib.PathEmulation as PathEmulation

from random import randrange, seed, uniform

from threading import Thread, Timer
from sched import scheduler

import sys
from time import time, sleep
import gc

class CT:
    current_throughput = 50*1000*1000

def mock_init(controll_port):
    print("TC init called")
    print("Controll port is " + str(controll_port))


def mock_initialize_path(path):
    """
    :param path: NetGraph.Path
    :return:
    """
    if len(path.links) < 1:
        return
    destination = path.links[-1].destination  # type: NetGraph.Service
    bandwidth = int(path.max_bandwidth/1000)
    latency = path.latency
    drop = path.drop
    print("Initializing " + destination.name + ":" + str(destination.__hash__()) + " with "
          + str(latency) + "ms "
          + str(bandwidth) + "Kbps "
          + str(drop) + "drop")


def mock_update_usage():
    current_time = time()
    mock_update_usage.time_delta = current_time - mock_update_usage.last_time
    mock_update_usage.last_time = current_time
    #print("Updating data usage ###############################")

mock_sent_bytes = {}
def mock_query_usage(service):
    """
    :param service: NetGraph.Service
    :return: int  # in bytes
    """
    if service.name != "server":
        return 0
    Mbits = 50
    sent_delta = (CT.current_throughput/8)*mock_update_usage.time_delta
    if service in mock_sent_bytes:
        mock_sent_bytes[service] += sent_delta
    else:
        mock_sent_bytes[service] = sent_delta

    return mock_sent_bytes[service]


def mock_change_bandwidth(service, new_bandwidth):
    """
    :param service: NetGraph.Service
    :param new_bandwidth: int  # in Kbps
    :return:
    """
    print("Changing " + service.name + ":" + str(service.__hash__()) + " to " + str(int(new_bandwidth/1000)) + "Kbps")
    CT.current_throughput = new_bandwidth - 0.01*new_bandwidth


class MockFlowDisseminator:
    #def __init__(self, flow_collector, graph, event_scheduler, worker):
    def __init__(self, flow_collector, graph, event_scheduler):
        self.graph = graph  # type: NetGraph
        self.flow_collector = flow_collector

        link_count = len(self.graph.links)
        BYTE_LIMIT = 255
        SHORT_LIMIT = 65535
        INT_LIMIT = 4294967296
        if link_count <= BYTE_LIMIT:
            self.link_unit = "B"
        elif link_count <= SHORT_LIMIT:
            self.link_unit = "H"
        elif link_count <= INT_LIMIT:
            self.link_unit = "I"

        self.concurrency_timer = 5
        self.s = scheduler(time, sleep)
        self.thread = Thread(target=self.receive_flows, args=([1],))
        self.thread.start()

    def broadcast_flows(self, active_flows):
        """
        :param active_flows: List[NetGraph.Path]
        :return:
        """
        return
        print("Active Flows: " + str(len(active_flows)))
        for path in active_flows:
            print("    " + str(path.used_bandwidth))
            print("    " + str(len(path.links)))
            for link in path.links:
                print("        " + str(link.index))

    def receive_flows(self, data):
        if len(data) > 0:
            sleep(0.5)
        path = [0, 6, 8]
        #path = [0, 42, 44, 65]
        self.flow_collector(CT.current_throughput, path)
        #sleep(0.01)
        #bandwidthMbps = 10
        #path = [2, 4, 8]
        #self.flow_collector(bandwidthMbps*1000, path)
        #bandwidthMbps = 50
        #path = [0, 5, 8]
        #self.flow_collector(bandwidthMbps*1000, path)
        #bandwidthMbps = 51
        #path = [2, 4, 6]
        #self.flow_collector(bandwidthMbps*1000, path)
        #print("Active Concurrent Flow")
        #print("    " + str(bandwidthMbps*1000))
        #for i in path:
        #    print("    " + str(i))
        #self.concurrency_timer -= 1
        #if self.concurrency_timer > 0:
        Timer(0.05 + uniform(-0.005, 0.005), self.receive_flows, args=([],)).start()

def mock_register_callback(callback):
    pass

def setup_mocking():
    PathEmulation.init = mock_init
    PathEmulation.initialize_path = mock_initialize_path
    PathEmulation.update_usage = mock_update_usage
    PathEmulation.query_usage = mock_query_usage
    PathEmulation.register_usage_callback = mock_register_callback
    mock_update_usage.last_time = time()
    mock_query_usage.sent_bytes = 0
    PathEmulation.change_bandwidth = mock_change_bandwidth

    CommunicationsManager.__init__ = MockFlowDisseminator.__init__
    CommunicationsManager.broadcast_flows = MockFlowDisseminator.broadcast_flows
    CommunicationsManager.receive_flows = MockFlowDisseminator.receive_flows

def main():
    gc.set_debug(gc.DEBUG_STATS)
    setup_mocking()

    topology_file = sys.argv[1]

    graph = NetGraph()

    parser = XMLGraphParser(topology_file, graph)
    parser.fill_graph()
    print("Done parsing topology")

    #__debug_print_paths(graph)
    #return

    print("Skipping Resolving hostnames...")
    #graph.resolve_hostnames()
    #print("All hosts found!")


    seed(None)
    print("Randomly Determining the root of the tree...")
    sv = randrange(0, len(graph.services))
    while True:
        hosts = list(graph.services.values())[sv]
        h = randrange(0, len(hosts))
        root = list(graph.services.values())[sv][h]
        if root.supervisor:
            sv = randrange(0, len(graph.services))
            continue
        else:
            graph.root = root
            break
    '''
    for service in graph.services:
        graph.root = graph.services[service][0]
        if graph.root.supervisor:
            continue
        break
    '''

    if graph.root is None:
        print_and_fail("Failed to identify current service instance in topology!")

    print("Calculating shortest paths...")
    graph.calculate_shortest_paths()

    for node in graph.paths:
        path = graph.paths[node]
        print("##############################")
        print(graph.root.name + " -> " + node.name + ":" + str(node.__hash__()))
        print("latency: " + str(path.latency))
        print("drop: " + str(path.drop))
        print("bandwidth: " + str(path.max_bandwidth))
        print("------------------------------")
        for link in path.links:
            print("   " + link.source.name + " hop " + link.destination.name + " i:" + str(link.index))

    print("Initializing network emulation conditions...")

    scheduler = parser.parse_schedule(graph.root, graph)

    manager = EmulationManager(graph, scheduler)
    manager.initialize()

    print("Starting experiment!")
    # Enter the emulation loop
    manager.emulation_loop()


if __name__ == '__main__':
    main()
