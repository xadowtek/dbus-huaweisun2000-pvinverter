#!/usr/bin/env python3

"""
A class to put a simple service on the dbus, according to victron standards, with constantly updating
paths. See example usage below. It is used to generate dummy data for other processes that rely on the
dbus. See files in dbus_vebus_to_pvinverter/test and dbus_vrm/test for other usage examples.

To change a value while testing, without stopping your dummy script and changing its initial value, write
to the dummy data via the dbus. See example.

https://github.com/victronenergy/dbus_vebus_to_pvinverter/tree/master/test
"""
from gi.repository import GLib
import platform
import logging
import sys
import time
import os
import config
from dbus.mainloop.glib import DBusGMainLoop
from connector_modbus import ModbusDataCollector2000Delux
from settings import HuaweiSUN2000Settings

# our own packages from victron
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService


class DbusSun2000Service:
    def __init__(self, servicename, settings, paths, data_connector, serialnumber='X',
                 productname='Huawei Sun2000 PV-Inverter'):
        self._dbusservice = VeDbusService(servicename)
        # self._paths = paths
        self._data_connector = data_connector

        logging.debug("%s /DeviceInstance = %d" % (servicename, settings.get_vrm_instance()))

        # productname="Huawei Sun2000" #tmp please del

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion',
                                   'Unkown version, and running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', 'Internal Wifi Modbus TCP')

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', settings.get_vrm_instance())
        self._dbusservice.add_path('/ProductId', 0)  # Huawei does not have a product id
        self._dbusservice.add_path('/ProductName', productname)
        self._dbusservice.add_path('/CustomName', settings.get("custom_name"))
        self._dbusservice.add_path('/FirmwareVersion', 1.0)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 1, writeable=True)

        # Create the mandatory objects
        self._dbusservice.add_path('/Latency', None)
        self._dbusservice.add_path('/Role', "pvinverter")
        self._dbusservice.add_path('/Position', settings.get("position"))  # 0 = AC Input, 1 = AC-Out 1, AC-Out 2
        self._dbusservice.add_path('/Serial', serialnumber)
        self._dbusservice.add_path('/ErrorCode', 0)
        self._dbusservice.add_path('/UpdateIndex', 0)
        self._dbusservice.add_path('/StatusCode', 7)

        for _path, _settings in paths.items():
            self._dbusservice.add_path(
                _path, _settings['initial'], gettextcallback=_settings.get('textformat', lambda p,v:v), writeable=True,
                onchangecallback=self._handlechangedvalue)

        GLib.timeout_add(settings.get('update_time_ms'), self._update)  # pause in ms before the next request

    def _update(self):
        with self._dbusservice as s:

            try:
                meter_data = self._data_connector.getData()

                for k, v in meter_data.items():
                    logging.info(f"set {k} to {v}")
                    s[k] = v

                # increment UpdateIndex - to show that new data is available (and wrap)
                s['/UpdateIndex'] = (s['/UpdateIndex'] + 1) % 256

                # update lastupdate vars
                self._lastUpdate = time.time()

            except Exception as e:
                logging.critical('Error at %s', '_update', exc_info=e)

        return True

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change

def exit_mainloop(mainloop):
    mainloop.quit()

def main():

    # FIXME: This should be a proper private logger, instead of trying to configure the root logger,
    # which doesn't work unless force=True is specified and then leads to all sorts of libraries
    # logging lots of debug data
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=config.LOGGING,
                        handlers=[
                            logging.StreamHandler()
                        ])

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    settings = HuaweiSUN2000Settings()
    logging.info(f"VRM pvinverter instance: {settings.get_vrm_instance()}")
    logging.info(f"Settings: ModbusHost '{settings.get('modbus_host')}', ModbusPort '{settings.get('modbus_port')}', ModbusUnit '{settings.get('modbus_unit')}'")
    logging.info(f"Settings: CustomName '{settings.get('custom_name')}', Position '{settings.get('position')}', UpdateTimeMS '{settings.get('update_time_ms')}'")
    logging.info(f"Settings: PowerCorrectionFactor '{settings.get('power_correction_factor')}'")

    while "255" in settings.get("modbus_host"):
        # This catches the initial setting and allows the service to be installed without configuring it first
        logging.warning(f"Please configure the modbus host and other settings in the VenusOS GUI (current setting: {settings.get('modbus_host')})")
        # Running a mainloop means we'll be notified about config changes and exit in that case (which restarts the service)
        mainloop = GLib.MainLoop()
        mainloop.run()

    modbus = ModbusDataCollector2000Delux(host = settings.get("modbus_host"),
                                          port=settings.get("modbus_port"),
                                          modbus_unit=settings.get("modbus_unit"),
                                          power_correction_factor=settings.get("power_correction_factor"))

    while True:
        staticdata = modbus.getStaticData()
        if staticdata is None:
            logging.error(f"Didn't receive static data from modbus, error is above. Sleeping 10 seconds before retrying.")
            # Again we sleep in the mainloop in order to pick up config changes
            mainloop = GLib.MainLoop()
            GLib.timeout_add(10000, exit_mainloop, mainloop)
            mainloop.run()
            continue
        else:
            break

    try:
        logging.info("Starting up");

        # formatting
        _kwh = lambda p, v: (str(round(v, 2)) + ' kWh')
        _a = lambda p, v: (str(round(v, 1)) + ' A')
        _w = lambda p, v: (str(round(v, 1)) + ' W')
        _v = lambda p, v: (str(round(v, 1)) + ' V')
        _hz = lambda p, v: f"{v:.4f}Hz"
        _n = lambda p, v: f"{v:i}"


        dbuspath = {
            '/Ac/Power': {'initial': 0, 'textformat': _w},
            '/Ac/Current': {'initial': 0, 'textformat': _a},
            '/Ac/Voltage': {'initial': 0, 'textformat': _v},
            '/Ac/Energy/Forward': {'initial': None, 'textformat': _kwh},
            #
            '/Ac/L1/Power': {'initial': 0, 'textformat': _w},
            '/Ac/L1/Current': {'initial': 0, 'textformat': _a},
            '/Ac/L1/Voltage': {'initial': 0, 'textformat': _v},
            '/Ac/L1/Frequency': {'initial': None, 'textformat': _hz},
            '/Ac/L1/Energy/Forward': {'initial': None, 'textformat': _kwh},
            #
            '/Ac/MaxPower': {'initial': 20000, 'textformat': _w},
            '/Ac/StatusCode': {'initial': 0, 'textformat': _n},
            '/Ac/L2/Power': {'initial': 0, 'textformat': _w},
            '/Ac/L2/Current': {'initial': 0, 'textformat': _a},
            '/Ac/L2/Voltage': {'initial': 0, 'textformat': _v},
            '/Ac/L2/Frequency': {'initial': None, 'textformat': _hz},
            '/Ac/L2/Energy/Forward': {'initial': None, 'textformat': _kwh},
            '/Ac/L3/Power': {'initial': 0, 'textformat': _w},
            '/Ac/L3/Current': {'initial': 0, 'textformat': _a},
            '/Ac/L3/Voltage': {'initial': 0, 'textformat': _v},
            '/Ac/L3/Frequency': {'initial': None, 'textformat': _hz},
            '/Ac/L3/Energy/Forward': {'initial': None, 'textformat': _kwh},
            '/Dc/Power': {'initial': 0, 'textformat': _w},
            '/Status': {'initial': ""},
        }

        pvac_output = DbusSun2000Service(
            servicename='com.victronenergy.pvinverter.sun2000',
            settings=settings,
            paths=dbuspath,
            productname=staticdata['Model'],
            serialnumber=staticdata['SN'],
            data_connector=modbus
        )

        logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
        mainloop = GLib.MainLoop()
        mainloop.run()
    except Exception as e:
        logging.critical('Error at %s', 'main', exc_info=e)


if __name__ == "__main__":
    main()
