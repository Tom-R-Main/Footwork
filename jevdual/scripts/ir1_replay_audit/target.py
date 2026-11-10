"""Independent private-bus AT-SPI target. Never imports CUA or Footwork."""
import argparse
import json
import os
import time
from pathlib import Path

from jeepney import DBusAddress, HeaderFields, MessageType, new_method_call
from jeepney.io.blocking import open_dbus_connection
from jeepney.wrappers import new_error, new_method_return


def main():
    p = argparse.ArgumentParser()
    for name in ['address', 'journal', 'ready', 'mode', 'primary', 'invocation']:
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    conn = open_dbus_connection(bus=a.address)
    daemon = DBusAddress('/org/freedesktop/DBus', bus_name='org.freedesktop.DBus', interface='org.freedesktop.DBus')
    for name in ['org.footwork.IR1Target', 'org.a11y.Bus', 'org.a11y.atspi.Registry']:
        conn.send_and_get_reply(new_method_call(daemon, 'RequestName', 'su', (name, 0)), timeout=2)
    with Path(a.journal).open('a', buffering=1) as journal:
        value = ''
        first = True

        def log(kind, **fields):
            journal.write(json.dumps({'invocation':a.invocation, 'monotonic_ns':time.monotonic_ns(),
                                      'kind':kind, **fields})+'\n')
            journal.flush()
            os.fsync(journal.fileno())

        log('target_ready', pid=os.getpid(), unique_name=conn.unique_name)
        Path(a.ready).write_text(json.dumps({'pid':os.getpid(), 'bus':conn.unique_name}))
        while True:
            msg = conn.receive(timeout=120)
            if msg.header.message_type != MessageType.method_call:
                continue
            fields = msg.header.fields
            method = fields.get(HeaderFields.member, '')
            interface = fields.get(HeaderFields.interface, '')
            if method in ['SetTextContents', 'InsertText'] and interface == 'org.a11y.atspi.EditableText':
                log('method_received', method=method, arguments=list(msg.body), serial=msg.header.serial)
                fault = a.mode if first and method == a.primary else 'ack'
                first = False
                if fault != 'false':
                    before = value
                    if method == 'SetTextContents':
                        value = msg.body[0]
                    else:
                        offset, text, length = msg.body
                        value = value[:offset]+text[:length]+value[offset:]
                    log('effect_applied', method=method, before=before, after=value)
                log('reply_behavior', method=method, behavior=fault, value=value)
                if fault == 'withhold':
                    # No held lock or awaited handler: continue servicing the bus.
                    continue
                if fault == 'error':
                    conn.send(new_error(msg, 'org.freedesktop.DBus.Error.Failed', 's', ('IR1 effect already applied',)))
                else:
                    conn.send(new_method_return(msg, 'b', (fault != 'false',)))
            elif method == 'GetInterfaces':
                conn.send(new_method_return(msg, 'as', (['org.a11y.atspi.Accessible', 'org.a11y.atspi.EditableText', 'org.a11y.atspi.Text'],)))
            elif method == 'GetRoleName':
                conn.send(new_method_return(msg, 's', ('entry',)))
            elif method == 'GetAddress':
                conn.send(new_method_return(msg, 's', (a.address,)))
            elif method in ['RegisterEvent', 'DeregisterEvent']:
                conn.send(new_method_return(msg))
            elif method == 'Get' and interface == 'org.freedesktop.DBus.Properties':
                prop = msg.body[1]
                result = ('i', len(value)) if prop == 'CharacterCount' else ('i', 0)
                conn.send(new_method_return(msg, 'v', (result,)))
            elif method == 'GetText':
                conn.send(new_method_return(msg, 's', (value,)))
            else:
                log('unsupported_method', interface=interface, method=method)
                conn.send(new_error(msg, 'org.freedesktop.DBus.Error.UnknownMethod', 's', ('IR1 unsupported method',)))


if __name__ == '__main__':
    main()
