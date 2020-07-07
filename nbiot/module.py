import time
import serial
import binascii
from collections import namedtuple
import logging

from .socket import UDPSocket

logger = logging.getLogger(__name__)

Stats = namedtuple("Stats", "type name value")


class CMEError(Exception):
    """CME ERROR on Module"""


class ATError(Exception):
    """AT Command Error"""


class ATTimeoutError(ATError):
    """Making an AT Action took to long"""


class ConnectionTimeoutError(ATTimeoutError):
    """Module did not connect within the specified time"""


class PingError(Exception):
    """Something went wrong during ping."""


class SaraN211Module:
    """
    Represents a Ublox SARA N211 module.
    Power-optimized NB-IoT (LTE Cat NB1) module.
    """

    BAUDRATE = 9600
    RTSCTS = False

    AT_ENABLE_NETWORK_REGISTRATION = "AT+CEREG=1"
    AT_ENABLE_SIGNALING_CONNECTION_URC = "AT+CSCON=1"
    AT_ENABLE_POWER_SAVING_MODE = "AT+CPSMS=1"
    AT_DISABLE_POWER_SAVING_MODE = "AT+CPSMS=0"
    AT_ENABLE_POWER_SAVING_MODE_URC = "AT+NPSMR=1"
    AT_DISABLE_POWER_SAVING_MODE_URC = "AT+NPSMR=0"
    AT_ENABLE_ALL_RADIO_FUNCTIONS = "AT+CFUN=1"
    AT_REBOOT = "AT+NRB"
    AT_CLOSE_SOCKET = "AT+NSOCL"

    AT_GET_IP = "AT+CGPADDR"

    AT_SEND_TO = "AT+NSOST"
    AT_CHECK_CONNECTION_STATUS = "AT+CSCON?"
    AT_RADIO_INFORMATION = 'AT+NUESTATS="RADIO"'

    REBOOT_TIME = 0

    SUPPORTED_SOCKET_TYPES = ["UDP"]

    def __init__(self, serial_port: str, roaming=False, echo=False):
        self._serial_port = serial_port
        self._serial = serial.Serial(
            self._serial_port, baudrate=self.BAUDRATE, rtscts=self.RTSCTS, timeout=5
        )
        self.echo = echo
        self.roaming = roaming
        self.ip = None
        self.connected = False
        self.sockets = {}
        self.available_messages = list()
        self.imei = None
        self.imsi = None
        self.iccid = None
        self.apn = None
        # TODO: make a class containing all states
        self.registration_status = 0
        self.radio_signal_power = None
        self.radio_total_power = None
        self.radio_tx_power = None
        self.radio_tx_time = None
        self.radio_rx_time = None
        self.radio_cell_id = None
        self.radio_ecl = None
        self.radio_snr = None
        self.radio_earfcn = None
        self.radio_pci = None
        self.radio_rsrq = None
        self.radio_rsrp = None

    def reboot(self):
        """
        Rebooting the module. Will run the AT_REBOOT command and also flush the
        serial port to get rid of trash input from when the module restarted.
        """
        logger.info("Rebooting module")
        self._at_action(self.AT_REBOOT)
        logger.info("waiting for module to boot up")
        time.sleep(self.REBOOT_TIME)
        self._serial.flushInput()  # Flush the serial ports to get rid of crap.
        self._serial.flushOutput()
        logger.info("Module rebooted")
        self._reset_after_reboot()

    def _reset_after_reboot(self):
        """
        Reset values after a reboot.
        """
        self.registration_status = 0
        self.connected = False
        self.ip = None
        self.connected = False
        self.sockets = {}
        self.available_messages = list()

    def setup(self):
        """
        Running all commands to get the module up an working
        """
        logger.info(f"Starting initiation process")

        self.enable_signaling_connection_urc()
        self.enable_network_registration()
        self.enable_psm_mode()
        self.enable_radio_functions()
        logger.info(f"Finished initiation process")

    def read_module_status(self):

        self._at_action("AT+CGPADDR")
        self._at_action("AT+CGDCONT?")
        self._at_action("AT+CEREG?")
        self._at_action("AT+CGSN=1")
        if self.registered:
            # The sim needs to initialized.
            self.imsi = self._at_action("AT+CIMI")[0].decode()
            self._at_action("AT+CCID")

    def enable_autoconnect(self):
        """
        Enable Autoconnect.
        """
        self._at_action('AT+NCONFIG="AUTOCONNECT","TRUE"')
        logger.info("Enabled AutoConnect")

    def disable_autoconnect(self):
        """
        Disable autoconnect
        """
        self._at_action('AT+NCONFIG="AUTOCONNECT","FALSE"')
        logger.info("Disabled AutoConnect")

    def enable_psm_mode(self):
        """
        Enable Power Save Mode
        """
        self._at_action(self.AT_ENABLE_POWER_SAVING_MODE)
        self._at_action(self.AT_ENABLE_POWER_SAVING_MODE_URC)
        logger.info("Enabled Power Save Mode")

    def disable_psm_mode(self):
        """
        Enable Power Save Mode
        """
        self._at_action(self.AT_DISABLE_POWER_SAVING_MODE)
        self._at_action(self.AT_DISABLE_POWER_SAVING_MODE_URC)
        logger.info("Disabled Power Save Mode")

    def enable_signaling_connection_urc(self):
        """
        Enable Signaling Connection URC
        """
        self._at_action(self.AT_ENABLE_SIGNALING_CONNECTION_URC)
        logger.info("Signaling Connection URC enabled")

    def enable_network_registration(self):
        """
        Enable Network registration
        """
        self._at_action(self.AT_ENABLE_NETWORK_REGISTRATION)
        logger.info("Network registration enabled")

    def enable_radio_functions(self):
        """
        Enable all radio functions.
        """
        self._at_action(self.AT_ENABLE_ALL_RADIO_FUNCTIONS)
        logger.info("All radio functions enabled")

    def connect(self, operator: int, roaming=False):
        """
        Will initiate commands to connect to operators network and wait until
        connected.
        """
        logger.info(f"Trying to connect to operator {operator} network")
        # TODO: Handle connection independent of home network or roaming.
        if self.registered:
            logger.info(
                f"Already registered to {operator} with registration "
                f"status {self.registration_status}"
            )
        else:

            if operator:
                at_command = f'AT+COPS=1,2,"{operator}"'

            else:
                at_command = f"AT+COPS=0"

            self._at_action(at_command, timeout=300)
            self._await_connection(roaming or self.roaming)
            logger.info(f"Connected to {operator}")
            self.read_module_status()

    @property
    def registered(self):

        if self.roaming:
            register_code = 5

        else:
            register_code = 1

        return self.registration_status == register_code

    def create_socket(self, port: int, socket_type="UDP"):
        """
        Will return a socket-like object that mimics normal python
        sockets. The socket will then translate the commands to correct method
        calls on the module.
        It will also register the socket on the module class so that they can be
        reused in the future if they are not closed.

        :param socket_type:
        :param port:
        :return: UbloxSocket
        """
        logger.info(f"Creating {socket_type} socket")

        if socket_type.upper() not in self.SUPPORTED_SOCKET_TYPES:
            raise ValueError(f"Module does not support {socket_type} sockets")

        sock = None
        if socket_type.upper() == "UDP":
            sock = self._create_upd_socket(port)

        elif socket_type.upper() == "TCP":
            sock = self._create_tcp_socket(port)

        logger.info(f"{socket_type} socket {sock.socket_id} created")

        self.sockets[sock.socket_id] = sock

        return sock

    def _create_upd_socket(self, port):
        """
        Will create a UDP-socket for the N211 module
        """
        at_command = f'AT+NSOCR="DGRAM",17'
        if port:
            at_command = at_command + f",{port}"

        response = self._at_action(at_command)
        socket_id = int(response[0])
        sock = UDPSocket(socket_id, self, port)
        return sock

    def _create_tcp_socket(self, port):
        """
        N211 module only supports UDP.
        """
        raise NotImplementedError("Sara211 does not support TCP")

    def close_socket(self, socket_id):
        """
        Will send the correct AT action to close specified socket and remove
        the reference of it on the module object.
        """
        logger.info(f"Closing socket {socket_id}")
        if socket_id not in self.sockets.keys():
            raise ValueError("Specified socket id does not exist")
        result = self._at_action(f"{self.AT_CLOSE_SOCKET}={socket_id}")
        del self.sockets[socket_id]
        return result

    def send_udp_data(self, socket: int, host: str, port: int, data: bytes):
        """
        Send a UDP message
        """
        logger.info(f"Sending UDP message to {host}:{port}  :  {data!r}")
        _data = binascii.hexlify(data).upper().decode()
        length = len(data)
        atc = f'{self.AT_SEND_TO}={socket},"{host}",{port},{length},"{_data}"'
        result = self._at_action(atc)
        return result

    def receive_udp_data(self):
        """
        Recieve a UDP message
        """
        logger.info(f"Waiting for UDP message")
        self._read_line_until_contains("+NSONMI")
        message_info = self.available_messages.pop(0)
        message = self._at_action(f"AT+NSORF={message_info.decode()}")
        response = self._parse_udp_response(message[0])
        logger.info(f"Recieved UDP message: {response}")
        return response

    def ping(self, ip):

        logger.info(f"Sending ping to {ip}")
        self._at_action(f'AT+NPING="{ip}"')
        result = self._read_line_until_contains("+NPING", timeout=20, capture_urc=True)
        ping_err = self._search_urc_result("+NPINGERR:", result)
        ping_response = self._search_urc_result("+NPING:", result)

        if ping_err:
            err_cause = int(ping_err.rstrip()[-1])
            err_map = {
                1: "No response from remote host",
                2: "Failed to send ping request",
            }
            raise PingError(err_map.get(err_cause, "Error during ping"))

        if ping_response:
            resp = ping_response.split(",")
            return resp[1], resp[2]
        else:
            return None

    def _search_urc_result(self, urc_id, capture_urc_response):
        for item in capture_urc_response:
            if item.decode().startswith(urc_id):
                return item.decode()

        return None

    def _at_action(self, at_command, timeout=10, capture_urc=False):
        """
        Small wrapper to issue a AT command. Will wait for the Module to return
        OK. Some modules return answers to AT actions as URC:s before the OK
        and to handle them as IRCs it is possible to set the capture_urc flag
        and all URCs between the at action and OK will be returned as result.
        """
        logger.debug(f"Applying AT Command: {at_command}")
        self._write(at_command)
        time.sleep(0.02)  # To give the end devices some time to answer.
        irc = self._read_line_until_contains(
            "OK", timeout=timeout, capture_urc=capture_urc
        )
        if irc is not None:
            logger.debug(f"AT Command response = {irc}")
        return irc

    def _write(self, data):
        """
        Writing data to the module is simple. But it needs to end with \r\n
        to accept the command. The module will answer with an empty line as
        acknowledgement. If echo is enabled everything that the is sent to the
        module is returned in the serial line. So we just need to omit it from
        the acknowledge.
        """
        data_to_send = data
        if isinstance(data, str):  # if someone sent in a string make it bytes
            data_to_send = data.encode()

        if not data_to_send.endswith(b"\r\n"):
            # someone didnt add the CR an LN so we need to send it
            data_to_send += b"\r\n"

        # start_time = time.time()

        self._serial.write(data_to_send)
        time.sleep(0.02)  # To give the module time to respond.
        logger.debug(f"Sent: {data_to_send}")

        ack = self._serial.read_until()
        logger.debug(f"Recieved ack: {ack}")

        if self.echo:
            # when echo is on we will have recieved the message we sent and
            # will get it in the ack response read. But it will not send \n.
            # so we can omitt the data we send + i char for the \r
            _echo = ack[:-2]
            wanted_echo = data_to_send[:-2] + b"\r"
            if _echo != wanted_echo:
                raise ValueError(
                    f"Data echoed from module: {_echo} is not the "
                    f"same data as sent to the module"
                )
            ack = ack[len(wanted_echo) :]

        if ack != b"\r\n":
            raise ValueError(f"Ack was not received properly, received {ack}")

    @staticmethod
    def _remove_line_ending(line: bytes):
        """
        To not have to deal with line endings in the data we can use this to
        remove them.
        """
        if line.endswith(b"\r\n"):
            return line[:-2]
        else:
            return line

    def _read_line_until_contains(self, slice, capture_urc=False, timeout=5):
        """
        Similar to read_until, but will read whole lines so we can use proper
        timeout management. Any URC:s that is read will be handled and we will
        return the IRC:s collected. If capture_urc is set we will return all
        data as IRCs.
        """
        _slice = slice
        if isinstance(slice, str):
            _slice = slice.encode()

        data_list = list()
        irc_list = list()
        start_time = time.time()
        while True:
            try:
                data = self._serial.read_until()
            except serial.SerialTimeoutException:
                # continue to read lines until AT Timeout
                duration = time.time() - start_time
                if duration > timeout:
                    raise ATTimeoutError
                continue
            line = self._remove_line_ending(data)

            if line.startswith(b"+"):
                if capture_urc:
                    irc_list.append(line)  # add the urc as an irc

                self._process_urc(line)

            elif line == b"OK":
                pass

            elif line.startswith(b"ERROR"):
                raise ATError(f"Error on AT Command: {line}")

            elif line == b"":
                pass

            else:
                irc_list.append(line)  # the can only be an IRC

            if _slice in line:
                data_list.append(line)
                break
            else:
                data_list.append(line)

            duration = time.time() - start_time
            if duration > timeout:
                raise ATTimeoutError

        clean_list = [response for response in data_list if not response == b""]

        logger.debug(f"Received: {clean_list}")

        return irc_list

    @staticmethod
    def _parse_udp_response(message: bytes):
        _message = message.replace(b'"', b"")
        socket, ip, port, length, _data, remaining_bytes = _message.split(b",")
        data = bytes.fromhex(_data.decode())
        return data

    def _process_urc(self, urc: bytes):
        """
        URC = unsolicited result code
        When waiting on answer from the module it is possible that the module
        sends urcs via +commands. So after the urcs are
        collected we run this method to process them.
        """

        _urc = urc.decode()
        logger.debug(f"Processing URC: {_urc}")
        urc_id = _urc[1 : _urc.find(":")]
        if urc_id == "CSCON":
            self._update_connection_status_callback(urc)
        elif urc_id == "CEREG":
            self._update_eps_reg_status_callback(urc)
        elif urc_id == "CGPADDR":
            self._update_ip_address_callback(urc)
        elif urc_id == "NSONMI":
            self._add_available_message_callback(urc)
        elif urc_id == "CGDCONT":
            self._update_apn_callback(urc)
        elif urc_id == "CGSN":
            self._update_imei_callback(urc)
        elif urc_id == "CCID":
            self._update_iccid_callback(urc)
        elif urc_id == "CME ERROR":
            self._handle_cme_error(urc)
        else:
            logger.debug(f"Unhandled urc: {urc}")

    def _update_iccid_callback(self, urc: bytes):
        urc_string = urc.decode()
        iccid = urc_string.split(":")[1].lstrip()
        self.iccid = iccid

    def _update_imei_callback(self, urc: bytes):
        urc_string = urc.decode()
        imei = urc_string.split(":")[1].lstrip()
        self.imei = imei

    def _update_apn_callback(self, urc: bytes):
        urc_string = urc.decode()
        values = urc_string.split(",")
        apn = values[2].replace('"', "")
        self.apn = apn

    def _handle_cme_error(self, urc: bytes):
        """
        Callback to raise CME Error.
        """
        raise CMEError(urc.decode())

    def _add_available_message_callback(self, urc: bytes):
        """
        Callback to handle recieved messages.
        """
        _urc, data = urc.split(b":")
        result = data.lstrip()
        logger.debug(f"Recieved data: {result}")
        self.available_messages.append(result)

    def update_radio_statistics(self):
        """
        Read radio statistics and update the module object.
        """
        radio_data = self._at_action(self.AT_RADIO_INFORMATION)
        self._parse_radio_stats(radio_data)

    def _update_connection_status_callback(self, urc):
        """
        In the AT urc +CSCON: 1 the last char is indication if the
        connection is idle or connected
        """
        status = bool(int(urc[-1]))
        self.connected = status
        logger.info(f"Changed the connection status to {status}")

    def _update_eps_reg_status_callback(self, urc):
        """
        The command could return more than just the status.
        Maybe a regex would be good
        But for now we just check the last as int
        """
        status = int(chr(urc[-1]))
        self.registration_status = status
        logger.info(f"Updated status EPS Registration = {status}")

    def _update_ip_address_callback(self, urc: bytes):
        """
        Update the IP Address of the module
        """
        # TODO: this is per socket. Need to implement socket handling
        _urc = urc.decode()
        ip_addr = _urc[(_urc.find('"') + 1) : -1]
        self.ip = ip_addr
        logger.info(f"Updated the IP Address of the module to {ip_addr}")

    def _parse_radio_stats(self, irc_buffer):
        """
        Parser for radio statistic result
        """
        stats = [self._parse_radio_stats_string(item) for item in irc_buffer]

        for stat in stats:
            if not stat:
                continue
            if stat.type == "RADIO" and stat.name == "Signal power":
                self.radio_signal_power = stat.value / 10
            elif stat.type == "RADIO" and stat.name == "Total power":
                self.radio_total_power = stat.value / 10
            elif stat.type == "RADIO" and stat.name == "TX power":
                self.radio_tx_power = stat.value / 10
            elif stat.type == "RADIO" and stat.name == "TX time":
                self.radio_tx_time = stat.value
            elif stat.type == "RADIO" and stat.name == "RX time":
                self.radio_rx_time = stat.value
            elif stat.type == "RADIO" and stat.name == "Cell ID":
                self.radio_cell_id = stat.value
            elif stat.type == "RADIO" and stat.name == "ECL":
                self.radio_ecl = stat.value
            elif stat.type == "RADIO" and stat.name == "SNR":
                self.radio_snr = stat.value
            elif stat.type == "RADIO" and stat.name == "EARFCN":
                self.radio_earfcn = stat.value
            elif stat.type == "RADIO" and stat.name == "PCI":
                self.radio_pci = stat.value
            elif stat.type == "RADIO" and stat.name == "RSRQ":
                self.radio_rsrq = stat.value
            else:
                logger.debug(f"Unhandled statistics data: {stat}")

    @staticmethod
    def _parse_radio_stats_string(stats_byte_string: bytes):
        """
        The string is like: b'NUESTATS: "RADIO","Signal power",-682'
        :param stats_byte_string:
        :return: NamedTuple Stats
        """
        parts = stats_byte_string.decode().split(":")

        irc: str = parts[0].strip()
        data: str = parts[1].strip().replace('"', "")

        data_parts = data.split(",")
        if irc == "NUESTATS":
            return Stats(data_parts[0], data_parts[1], int(data_parts[2]))
        else:
            return None

    def __repr__(self):
        return f'NBIoTModule(serial_port="{self._serial_port}")'

    def _await_connection(self, roaming, timeout=180):
        """
        The process to verify that connection has occured is a bit different on
        different devices. On N211 we need to wait intil we get the +CERREG: x
        URC.
        """

        logging.info(f"Awaiting Connection")

        if roaming:
            self._read_line_until_contains("CEREG: 5", timeout=timeout)
        else:
            self._read_line_until_contains("CEREG: 1", timeout=timeout)

    def set_pdp_context(self, apn, pdp_type="IP", cid=1):
        logger.info(f"Setting PDP Context")
        _at_command = f'AT+CGDCONT={cid},"{pdp_type}","{apn}"'
        self._at_action(_at_command)
        logger.info(f"PDP Context: {apn}, {pdp_type}")

