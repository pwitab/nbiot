# NB-IoT Scanner Tool

This is a NB-IoT scanner tool made for finding problems and evaluating
network coverage in smart meter rollouts.

Built by Palmlund Wahlgren Innovative Technology AB in Sweden. We offer it
as a part of our free tooling for customers of our AMR solution,
Utilitarian. https://www.utilitarian.io

But it can of course be used by anyone wanting to analyse coverage and
finding problems in IoT solutions based on NB-IoT.

You will need a Ublox SARA N211 NB-IoT module connected via a serial
interface, like USB.

# Use Cases

## Network Statistics

Use the `nbiot stats` command to get a table of the current network statistics. 
Run a couple of commands after the initial connect. The device can start en ECL 2 and 
move up after a while.

It is usually only necessary to look at the ECL (Extended Coverage Level) metric. 
ECL 0 is good, ECL 1 is worse and ECL 2 the worst. In the higher ECL the repetitions 
of the messages (radio level) are increased and it will take longer to send data and 
it will use more battery.

It is also easy to see if there is a problem with your device or with the network by 
using this tool to try and connect to the network in close proximity to the 
malfunctioning device. We try to and use a similar antenna type as the device we are 
investigating so that we get reasonable result. Checking for connection problems on a 
device with a built in PCB antenna  using a large external antenna is not comparable.

But it can be good to check both because if you can get a connection using a larger 
antenna your MNO might be able to do some optimizations.  

# IoT Solution Networking and Firewall checks

It is useful to use the `nbiot ping` command to make sure your devices and SIM are set 
up correctly at the MNO with for example a VPN to your datacenter.

We are currently working on making the UDP send functionality available over the CLI.
This can be used on conjunction with our simple UDP logger 
[protolog](https://github.com/pwitab/protolog) to set up a listening server on the 
receiving end and make sure all firewall rules are applied correctly.

# Installation

Requires python>=3.6

```bash
pip install nbiot
```

# Usage

Use the `--help` to get the CLI documentation

```bash
>> nbiot --help
Usage: nbiot [OPTIONS] COMMAND [ARGS]...

  This is a NB-IoT Scanner software built by Palmlund Wahlgren Innovative
  Technology AB in Sweden for use in finding problems and evaluating network
  coverage in smart meter rollouts.

  You will need a Ublox NB-IoT module (SARA N211 for example) connected via
  a serial interface, like USB.

Options:
  -p, --port TEXT                 Register the serial port to use
  --roaming / --home-network      Indicate if the MNO is using home network or
                                  roaming status
  --mno TEXT                      ID of MNO (Mobile Network Operator) ex.
                                  Telia Sweden = 24001
  -l, --loglevel [DEBUG|INFO|WARNING]
                                  Choose loglevel
  --psm                           If Power Save Mode should be used.
  --apn TEXT                      choose apn
  --help                          Show this message and exit.

Commands:
  connect  Connect to the network and get general info on module and network
  ping     Ping an IP address
  reboot   Reboot the module
  stats    Print statistics from the module.


```

Using the `--help` on a command gives more information about a command. Ex:

```bash
>> nbiot ping --help
Usage: nbiot ping [OPTIONS] IP

  Ping an IP address

Options:
  -r, --runs INTEGER  How many times should we ping
  --help              Show this message and exit.
```

# Hardware

You will need a Ublox SARA N211 NB-IoT module connected via a serial interface, like USB.
Either you make your own board or you buy a development board for quick setup.
We use this one with a passthrough program loaded on the Arduino: https://shop.sodaq.com/sodaq-sara-aff-n211.html

We have chosen to only support the SARA N211 because it gives the most statistics about 
the network of the Ublox modules we have tried out. 


# Notes

## Home network vs roaming
Your SIM might be for home network or roaming. Make sure you know which you need to 
use. If it doesn't work and you can't connect try switching. Default is roaming.
