###############################################################################
#   ilastik: interactive learning and segmentation toolkit
#
#       Copyright (C) 2011-2014, the ilastik developers
#                                <team@ilastik.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition, as a special exception, the copyright holders of
# ilastik give you permission to combine ilastik with applets,
# workflows and plugins which are not covered under the GNU
# General Public License.
#
# See the LICENSE file for details. License information is also available
# on the ilastik web site at:
#           http://ilastik.org/license.html
###############################################################################


def handshake(facade, _, protocol, name, **address):

    if "host" in address and "port" in address:
        address = (address["host"], address["port"])
    facade.handshake(protocol, name, address)


def goodbye(facade, _, protocol, name, **address):
    from ilastik.shell.gui.ipcManager import IPCFacade
    if "host" in address and "port" in address:
        address = (address["host"], address["port"])
    facade.goodbye(protocol, name, address)


def clear_peers(facade, _, protocol):
    from ilastik.shell.gui.ipcManager import IPCFacade
    facade.clear_peers(protocol)


def set_position(facade, shell, t=0, x=0, y=0, z=0, c=0, **_):
    try:
        shell.setAllViewersPosition([t, x, y, z, c])
    except IndexError:
        pass  # No project loaded


commands = {
    "clear peers": clear_peers,
    "handshake": handshake,
    "setviewerposition": set_position,
    "goodbye": goodbye,
}


class CommandProcessor(object):
    def __init__(self):

        self.shell = None
        self.facade = None

    def set_shell(self, shell):
        from ilastik.shell.gui.ipcManager import IPCFacade
        self.shell = shell
        self.facade = IPCFacade()

    def connect_receiver(self, receiver):
        receiver.signal.connect(self.execute)

    def disconnect_receiver(self, receiver):
        receiver.signal.disconnect(self.execute)

    def execute(self, command, data):
        command = str(command)
        handler = commands.get(command)
        if handler is None:
            raise RuntimeError("Command '{}' is not available".format(command))
        success = True
        try:
            handler(self.facade, self.shell, **data)
        except Exception as e:
            print e
            success = False
        if command not in ("handshake", "goodbye", "clear peers"):
            data.update({"command": command})
            self.facade.handled_command(data["protocol"], data, success)





