
import subprocess
import sys
import struct
import socket
import docker
from subprocess import Popen


BYTE_LIMIT = 255
SHORT_LIMIT = 65535
# INT_LIMIT = 4294967296
DOCKER_SOCK = "/var/run/docker.sock"

TOPOLOGY = "/topology.xml"


class ENVIRONMENT:
    NETWORK_INTERFACE = 'NETWORK_INTERFACE'
    BROADCAST = 'BROADCAST_ADDRESS'
    POOL_PERIOD = 'NEED_POOL_PERIOD'
    ITERATION_COUNT = 'NEED_ITERATION_COUNT'


class CONTAINER:
    id = None
    pid = ""
    client = None  # type: docker.DockerClient
    ll = None  # type: docker.APIClient
    container = None
    process = None


def fail(message):
    print("An error occured, terminating!", file=sys.stderr)
    print("Error Message: " + message, file=sys.stderr)
    sys.stderr.flush()
    exit(-1)


def error(message):
    print("ERROR: " + message, file=sys.stderr)
    sys.stderr.flush()


def message(m):
    print(m, file=sys.stdout)
    sys.stdout.flush()


def start_experiment():
    # Temporary hack to start the experiment
    #subprocess.run('echo "done" > /tmp/readypipe', shell=True)
    inspect = CONTAINER.ll.inspect_container(CONTAINER.id)
    cmd = inspect['Config']['Cmd']
    image = inspect['Image']
    image_inspect = CONTAINER.ll.inspect_image(image)
    entrypoint = image_inspect['Config']['Entrypoint']
    if entrypoint is None:
        entrypoint = [""]
    if cmd is None:
        cmd = image_inspect['Config']['Cmd']
    elif len(cmd) == 0:
        cmd = image_inspect['Config']['Cmd']
    if cmd is None:
        command = ' '.join(entrypoint)
    else:
        command = ' '.join(entrypoint + cmd)
    #arg = ['/bin/sh'] + ['-c'] + [command]
    command.replace('"', '\\"')
    command.replace("'", "\\'")
    arg = ['echo ' + command + ' > /tmp/NEED_hang']
    message(arg[0])
    CONTAINER.container.exec_run(['/bin/sh'] + ['-c'] + arg, detach=True)


def stop_experiment():
    # kill all but pid 1 (this might create zombies)
    Popen(
        ["nsenter", "-t", str(CONTAINER.pid), "-p", "-m", "/bin/sh", "-c", "kill -2 -1"]
    ).wait()
    return


def crash_experiment():
    # kill all but pid 1 (this might create zombies)
    Popen(
        ["nsenter", "-t", str(CONTAINER.pid), "-p", "-m", "/bin/sh", "-c", "kill -9 -1"]
    ).wait()
    return


def setup_container(id, pid):
    CONTAINER.id = id
    CONTAINER.pid = pid
    CONTAINER.client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
    CONTAINER.ll = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
    CONTAINER.container = CONTAINER.client.containers.get(id)


def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]


def int2ip(addr):
    return socket.inet_ntoa(struct.pack("!I", addr))


# def get_own_ip():
#     return str(socket.gethostbyname(socket.gethostname()))

def get_own_ip(graph):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_ip = None
    # Connect to at least 2 to avoid using our loopback ip
    for int_ip in graph.hosts_by_ip:
        s.connect((int2ip(int_ip), 1))
        new_ip = s.getsockname()[0]
        if new_ip == last_ip:
            break
        last_ip = new_ip
    return last_ip


# def identified_print(who, msg):
#     print("[Py (" + who + ") " + get_own_ip() + "] " + msg, file=sys.stdout)
#     sys.stdout.flush()

def identified_print(graph, msg):
    print("[Py (" + graph.root.name + ") " + get_own_ip(graph) + "] " + msg, file=sys.stdout)
    sys.stdout.flush()
