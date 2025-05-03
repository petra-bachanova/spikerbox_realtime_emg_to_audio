import serial.tools.list_ports


def find_com_ports():
    """
    List available COM ports
    """
    ports = serial.tools.list_ports.comports()
    com_list = []
    for port, desc, hwid in sorted(ports):
        com_list.append("{}: {}".format(port, desc))

    return com_list
