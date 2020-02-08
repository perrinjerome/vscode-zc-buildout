import argparse
import io
import ipaddress
import logging
import sys
import urllib.parse

from .server import server


def main() -> None:

  parser = argparse.ArgumentParser(
      'buildoutls',
      description='zc.buildout language server',
  )

  parser.add_argument(
      '--check-install',
      help='Utility flag to check if language server is installed on this python',
      action='store_true',
  )
  parser.add_argument(
      '--logfile',
      help='Use a debug log file',
      type=str,
  )
  parser.add_argument(
      '--tcp',
      help='listen on tcp port or hostname:port on IPv4.',
      type=str,
  )

  options = parser.parse_args()
  if options.check_install:
    print("Installation looks OK")
    sys.exit(0)

  if options.logfile:
    logging.basicConfig(
        filename=options.logfile,
        format='%(asctime)s %(name)s %(levelname)-8s %(message)s',
        filemode='w',
        level=logging.DEBUG,
    )
    logging.getLogger().propagate = False

  if options.tcp:
    host = 'localhost'
    port = options.tcp
    if ':' in options.tcp:
      host, port = options.tcp.split(':')
    print('Listening on {}:{}'.format(host, port))
    server.start_tcp(host, int(port))  # type: ignore
  else:
    server.start_io()  # type: ignore
