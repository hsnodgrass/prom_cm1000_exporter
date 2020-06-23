# prom_cm1000_exporter

A metric exporter for the Netgear CM1000 modem.

# Usage

There are two ways to configure the exporter: environment variables or a `yaml` file. YOU CANNOT MIX THE TWO. If you use envvars, you have to use all envvars and the same with a `yaml` file.

## Environment variables

* `PCM_MODEM_IP` - This envvar should be set to the IP of your modem. Default: `192.168.100.1`.
* `PCM_USERNAME` - The username to login to your modem. Default: `admin`.
* `PCM_PASSWORD` - The password to log into your modem. REQUIRED.
* `PCM_EXPORT_PORT` - The TCP port the exporter runs on. Default: `9527`.
* `PCM_INTERVAL` - The interval, in seconds, between scrapes. Default: `10`.

## Running the container with envvars

`docker run -p 9527:9527 -e PCM_MODEM_IP='192.168.100.1' -e PCM_USERNAME='admin' -e PCM_PASSWORD='hunter2' -e PCM_EXPORT_PORT=9527 -e PCM_INTERVAL=10 hsnodgrass3/prom_cm1000_exporter`

## YAML

If you would like to use a YAML file for config, it should be mounted to the container at `/usr/local/prom_cm1000.yaml`.

Below is a sample config file:

```yaml
modem_ip: 192.168.100.1
username: admin
password: hunter2
export_port: 9527
interval: 10
```

## Running the container with a config file

`docker run -p 9257:9257 -v /path/to/local.yaml:/usr/local/prom_cm1000.yaml hsnodgrass3/prom_cm1000_exporter`
