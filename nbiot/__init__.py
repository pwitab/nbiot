import logging
from logging.config import DictConfigurator

import click
from .scan import connect, ping, stats, reboot, send
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
@click.option("--port", "-p", help="Register the serial port to use")
@click.option(
    "--roaming/--home-network",
    default=True,
    help="Indicate if the MNO is using home network or roaming status",
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
    This is a NB IoT Scanner software built by Palmlund Wahlgren Innovative
    Technology AB in Sweden for use in finding problems and evaluating network
    coverage in smart meter rollouts.

    You will need a Ublox NB-IoT module (SARA N211 for
    example) connected via a serial interface, like USB.
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
                f"Resource busy. Are you sure no " f"other process is using port {port}"
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
cli.add_command(send)
