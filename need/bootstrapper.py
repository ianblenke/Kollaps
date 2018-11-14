import docker
# from docker.types import Mount
from time import sleep
from sys import argv
from subprocess import Popen
# from shutil import copy


def main():
    DOCKER_SOCK = "/var/run/docker.sock"
    TOPOLOGY = "/topology.xml"

    if len(argv) < 3:
        print("If you are calling " + argv[0] + " from your workstation stop.")
        print("This should only be used inside containers")
        return

    mode = argv[1]
    label = argv[2]


    #Connect to the local docker daemon
    client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
    LowLevelClient = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)

    if mode == "-s":
        while True:
            try:
                #If we are bootstrapper:
                us = None
                while not us:
                    containers = client.containers.list()
                    for container in containers:
                        if "boot"+label in container.labels:
                            us = container
                    sleep(1)

                boot_image = us.image

                inspect_result = LowLevelClient.inspect_container(us.id)
                env = inspect_result["Config"]["Env"]

                # create a "God" container that is in the host's Pid namespace, and our network namespace
                client.containers.run(image=boot_image,
                                      entrypoint="/usr/bin/python3",
                                      command=["/usr/bin/NEEDbootstrapper", "-g", label, str(us.id)],
                                      privileged=True,
                                      pid_mode="host",
                                      remove=True,
                                      environment=env,
                                      volumes_from=[us.id],
                                      network_mode="container:"+us.id,  # share the network stack with this container
                                      labels=["god"+label],
                                      detach=False,
                                      stderr=True,
                                      stdout=True)
                return
            except:
                sleep(5)
                continue #If we get any exceptions try again

    # We are the god container
    # First thing to do is copy over the topology
    while True:
        try:
            bootstrapper_id = argv[3]
            bootstrapper_pid = LowLevelClient.inspect_container(bootstrapper_id)["State"]["Pid"]
            Popen(["/bin/sh", "-c",
                  "nsenter -t " + str(bootstrapper_pid) + " -m cat " + TOPOLOGY + " | cat > " + TOPOLOGY]
                  ).wait()
            break
        except:
            sleep(5)
            continue

    # Figure out who we are
    us = None
    while True:
        try:
            for container in client.containers.list():
                if "god"+label in container.labels:
                    us = container
                    break
            break
        except:
            sleep(5)
            continue

    # We are finnally ready to proceed
    print("Bootstrapping all local containers with label " + label)

    already_bootstrapped = {}
    instance_count = 0

    while True:
        try:
            # check if containers need bootstrapping
            bootstrapper = None
            containers = client.containers.list()
            for container in containers:
                if label in container.labels and container.id not in already_bootstrapped and container.status == "running":
                    try:
                        id = container.id
                        inspect_result = LowLevelClient.inspect_container(id)
                        pid = inspect_result["State"]["Pid"]
                        print("Bootstrapping " + container.name + " ...")
                        emucore_instance = Popen(
                            ["nsenter", "-t", str(pid), "-n",
                             "/usr/bin/python3", "/usr/bin/NEEDemucore", TOPOLOGY, str(id), str(pid)]
                        )
                        instance_count += 1
                        print("Done bootstrapping " + container.name)
                        already_bootstrapped[container.id] = emucore_instance
                    except:
                        print("Bootstrapping failed... will try again.")

                # Check for termination
                if container.id == bootstrapper_id and container.status == "running":
                    bootstrapper = container
            #Retrieve return codes
            for key in already_bootstrapped:
                already_bootstrapped[key].poll()
            #Clean up and stop
            if bootstrapper is None:
                for key in already_bootstrapped:
                    if already_bootstrapped[key].poll() is not None:
                        already_bootstrapped[key].kill()
                        already_bootstrapped[key].wait()
                us.stop()
            sleep(5)
        except:
            sleep(5)
            continue


if __name__ == '__main__':
    main()