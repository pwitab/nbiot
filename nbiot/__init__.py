import logging
from logging.config import DictConfigurator

import click
from .scan import connect, ping, stats, reboot
import serial
from .module import SaraN211Module

logger = logging.getLogger(__name__)


class AppContext:
    def __init__(self, module, mno, psm=False, apn=None):
        self.module = module
        self.mno = mno
        self.psm = psm
        self.apn = apn


@click.group()
@click.option("--port", "-p", help="Serial port to use")
@click.option(
    "--roaming/--home-network",
    default=True,
    help="Indicate if the SIM is using home network or roaming status",
)
@click.option(
    "--mno",
    default=None,
    help="ID of MNO (Mobile Network Operator) ex. Telia Sweden = 24001",
)
@click.option(
    "--loglevel",
    "-l",
    default="WARNING",
    help="Choose loglevel",
    type=click.Choice(["DEBUG", "INFO", "WARNING"]),
)
@click.option("--psm", is_flag=True, help="If Power Save Mode should be used.")
@click.option("--apn", default=None, help="choose apn")
@click.pass_context
def cli(ctx, port, roaming, mno, loglevel, psm, apn):
    """
    This is a NB-IoT scanner tool made for finding problems and evaluating network
    coverage in smart meter rollouts.

    Built by Palmlund Wahlgren Innovative Technology AB in Sweden. We offer it as a part
    of our free tooling for customers of our AMR solution, Utilitarian. https://www.utilitarian.io

    But it can of course be used by anyone wanting to analyse coverage and finding
    problems in IoT solutions based on NB-IoT.

    You will need a Ublox SARA N211 NB-IoT module connected via a serial interface,
    like USB.
    """
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {},
            "formatters": {
                "main_formatter": {
                    "format": "[{asctime}] :: [{levelname}] :: {name} :: {message}",
                    "style": "{",
                }
            },
            "handlers": {
                "console": {
                    "level": "DEBUG",
                    "filters": [],
                    "class": "logging.StreamHandler",
                    "formatter": "main_formatter",
                }
            },
            "loggers": {"": {"handlers": ["console"], "level": loglevel}},
        }
    )

    try:
        nbiot_module = SaraN211Module(serial_port=port, roaming=roaming, echo=False)
    except serial.serialutil.SerialException as e:
        serial_error_nr_map = {
            16: (
                f"Resource busy. Are you sure no other process is using port {port}"
            )
        }

        reason = serial_error_nr_map.get(e.errno, None)

        if reason:
            raise click.ClickException(reason)
        else:
            raise click.ClickException(e)

    ctx.obj = AppContext(module=nbiot_module, mno=mno, psm=psm, apn=apn)


def main():
    cli()


cli.add_command(connect)
cli.add_command(ping)
cli.add_command(stats)
cli.add_command(reboot)
