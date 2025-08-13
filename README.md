# dbus-huaweisun2000-pvinverter

Modified version of dbus driver for Huawei Sun2000 of kcbam https://github.com/kcbam/dbus-huaweisun2000-pvinverter.
All credits goes to him and to Olivergregorius https://github.com/olivergregorius/sun2000_modbus.


## Purpose

This script is intended to help integrate a Huawei Sun 2000 inverter into the Venus OS and thus also into the VRM
portal.

I use a Cerbo GX, which I have integrated via Ethernet in the house network. I used the WiFi of the device to connect to
the internal WiFi of the Huawei Sun 2000. Attention: No extra dongle is necessary! You can use the integrated Wifi,
which is actually intended for configuration with the Huawei app (Fusion App or Sun2000 App). The advantage is that no
additional hardware needs to be purchased and the inverter does not need to be connected to the Internet.

To further use the data, the mqtt broker from Venus OS can be used.

## Installation

1. Copy the full project directory to the /data/etc folder on your venus:

    - /data/dbus-huaweisun2000-pvinverter/

   Info: The /data directory persists data on venus os devices while updating the firmware

   Easy way:
   ```
   wget https://github.com/kcbam/dbus-huaweisun2000-pvinverter/archive/refs/heads/main.zip
   unzip main.zip -d /data
   mv /data/dbus-huaweisun2000-pvinverter-main /data/dbus-huaweisun2000-pvinverter
   chmod a+x /data/dbus-huaweisun2000-pvinverter/install.sh
   rm main.zip
   ```


3. Edit the config.py file (not longer needed. Watch for Settings in the Remote Console.)

   `nano /data/dbus-huaweisun2000-pvinverter/config.py`

5. Check Modbus TCP Connection to gridinverter

   `python /data/dbus-huaweisun2000-pvinverter/connector_modbus.py`

6. Run install.sh

   `sh /data/dbus-huaweisun2000-pvinverter/install.sh`

### Debugging

You can check the status of the service with svstat:

`svstat /service/dbus-huaweisun2000-pvinverter`

It will show something like this:

`/service/dbus-huaweisun2000-pvinverter: up (pid 10078) 325 seconds`

If the number of seconds is always 0 or 1 or any other small number, it means that the service crashes and gets
restarted all the time.

When you think that the script crashes, start it directly from the command line:

`python /data/dbus-huaweisun2000-pvinverter/dbus-huaweisun2000-pvinverter.py`

Also useful:

`tail -f /var/log/dbus-huaweisun2000/current | tai64nlocal`

### Stop the script

`svc -d /service/dbus-huaweisun2000-pvinverter`

### Start the script

`svc -u /service/dbus-huaweisun2000-pvinverter`


### Restart the script

If you want to restart the script, for example after changing it, just run the following command:

`sh /data/dbus-huaweisun2000-pvinverter/restart.sh`

## Uninstall the script

Run

   ```
sh /data/dbus-huaweisun2000-pvinverter/uninstall.sh
rm -r /data/dbus-huaweisun2000-pvinverter/
   ```

## CREDITS

kcbam 			https://github.com/kcbam/dbus-huaweisun2000-pvinverter
Olivergregorius	https://github.com/olivergregorius/sun2000_modbus

Thanks to kcbam for developing dbus driver for Huawei Sun2000.
Thanks to Olivergregorius for developing the python modbus library for Huawei Sun2000.
Thanks to both for share code with the comunity!


## this project is inspired by

https://github.com/RalfZim/venus.dbus-fronius-smartmeter

https://github.com/fabian-lauer/dbus-shelly-3em-smartmeter.git

https://github.com/victronenergy/velib_python.git
