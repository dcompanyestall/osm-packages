import wgconfig
import os
from command import Command
import json

import logging
# Logger
logging.basicConfig(
    format="%(module)-15s:%(levelname)-10s| %(message)s",
    level=logging.INFO
)

class WGAux:
    def __init__(self, tunnel_charm):
        self.tunnel_charm = tunnel_charm

    def execute_command(self, command):
        result, error = None, None
        #self.unit.status = MaintenanceStatus(initial_status)
        logging.info(command.initial_status)
        try:
            proxy = self.tunnel_charm.get_ssh_proxy()
            result, error = proxy.run(command.command)
            logging.info(command.ok_status)
            ret = {"output": result, "errors": error}
            logging.info(ret)
            #self.unit.status = MaintenanceStatus(command.ok_status)
            return ret
        except Exception as e:
            logging.error(command.error_status)
            logging.error("[{}] Action failed {}. Stderr: {}".format(command.command, e, error))
            #self.unit.status = BlockedStatus(command.error_status)
            raise Exception("[{}] Action failed {}. Stderr: {}".format(command.command, e, error))


    def execute_commands_list(self, commands_list):
        for c in commands_list:
            self.execute_command(c)


    def execute_scp(self, source_file, destination_file, initial_status, ok_status, error_status):
        result, error = None, None
        #self.unit.status = MaintenanceStatus(initial_status)
        logging.info(initial_status)
        try:
            proxy = self.tunnel_charm.get_ssh_proxy()
            proxy.scp(source_file, destination_file)
            logging.info(ok_status)
            ret = {"source": source_file, "destination": destination_file}
            logging.info(ret)
            #self.unit.status = MaintenanceStatus(ok_status)
            return True
        except Exception as e:
            logging.error(error_status)
            logging.error("[SCP {} -> {}] Action failed {}. Stderr: {}".format(source_file, destination_file, e, error))
            #self.unit.status = BlockedStatus(error_status)
            raise Exception("[SCP {} -> {}] Action failed {}. Stderr: {}".format(source_file, destination_file, e, error))

    
    def get_wg_config_to_local(self):
        forward_interface = self.tunnel_charm.model.config["forward_interface"]
        destination_file_local = "/tmp/wireguard/wg.conf"
        source_file_vnf = "/etc/wireguard/{}.conf".format(forward_interface)

        if not os.path.exists("/tmp/wireguard/wg.conf"):
            if not os.path.exists("/tmp/wireguard/"):
                os.mkdir("/tmp/wireguard")
            open("/tmp/wireguard/wg.conf", 'a').close()
            logging.info("Local wireguard configuration file created")

        # 1. Obtain the wg config file from the VNF
        command = Command(
            "sudo cat {} ".format(source_file_vnf),
            "Performing a cat on the wireguard configuration file on the VNF...",
            "Performed a cat on the wireguard configuration file on the VNF",
            "Could not perform a cat on the wireguard configuration file on the VNF"
        )
        ret = self.execute_command(command)

        #2. Write the wg config file to local
        with open(destination_file_local, "w") as f:
                f.write(ret["output"]+"\n")


    def update_wg_config_on_vnf(self):
        forward_interface = self.tunnel_charm.model.config["forward_interface"]
        source_file = "/tmp/wireguard/wg.conf"
        destination_file = "~/{}.conf".format(forward_interface)

        # 1 - move config file to vnf's home directory
        try:
            logging.info("Updating wireguard configuration file on VNF...")
            ret = self.execute_scp(
                source_file,
                destination_file,
                "Copying wireguard configuration file to the VNF's home directory...",
                "Copied wireguard configuration file to the VNF's home directory",
                "Could not copy wireguard configuration file to the VNF's home directory!"
            )

            if not ret:
                raise Exception("Could not copy wireguard configuration file to the VNF!")

            # 2 - update config file
            command = Command(
                "sudo mv {} /etc/wireguard/".format(destination_file),
                "Moving wireguard configuration file to /etc/wireguard/...",
                "Moved wireguard configuration file to /etc/wireguard/",
                "Could not move wireguard configuration file to /etc/wireguard/"
            )
            self.execute_command(command)
            logging.info("Updated wireguard configuration file on VNF")
            return True

        except Exception as e:
            logging.error("Unable to update wireguard config on vnf")
            #self.unit.status = BlockedStatus(error_status)
            raise Exception(("Unable to update wireguard config on vnf"))
