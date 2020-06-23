import logging
import time
import traceback
import urllib.parse
import requests
from bs4 import BeautifulSoup
from prometheus_client import start_http_server, Gauge, Counter

total_scrapes = Counter(
    'netgear_total_scrapes',
    'Total number of times the modem has been scraped'
)
total_failed_scrapes = Counter(
    'netgear_total_failed_scrapes',
    'Total number of times modem scrapes have failed'
)
generic_failures = Counter(
    'netgear_generic_failures',
    'Total number of generic failures'
)
ds_bonded = {
    'locked': {},
    'freq': {},
    'power': {},
    'snrmer': {},
    'uecodewords': {},
    'cocodewords': {},
    'uccodewords': {}
}
us_bonded = {
    'locked': {},
    'freq': {},
    'power': {}
}
ds_ofdm = {
    'locked': {},
    'freq': {},
    'power': {},
    'snrmer': {},
    'uecodewords': {},
    'cocodewords': {},
    'uccodewords': {}
}
us_ofdma = {
    'locked': {},
    'freq': {},
    'power': {}
}
for _key in range(1, 33):
    key = str(_key)
    ds_bonded['locked'][key] = Gauge(f'netgear_bonded_downstream_{key}_locked', f'Downstream bonded channel {key} is locked(1) or not (0)', ['channel'])
    ds_bonded['freq'][key] = Gauge(f'netgear_bonded_downstream_{key}_frequency_hz', f'Downstream bonded frequency for channel {key}', ['channel'])
    ds_bonded['power'][key] = Gauge(f'netgear_bonded_downstream_{key}_power_dbmv', f'Downstream bonded power for channel {key}', ['channel'])
    ds_bonded['snrmer'][key] = Gauge(f'netgear_bonded_downstream_{key}_snr_mer_db', f'Downstream bonded SNR/MER for channel {key}', ['channel'])
    ds_bonded['uecodewords'][key] = Gauge(f'netgear_bonded_downstream_{key}_unerrored_codewords', f'Downstream bonded unerrored codewords for channel {key}', ['channel'])
    ds_bonded['cocodewords'][key] = Gauge(f'netgear_bonded_downstream_{key}_correctable_codewords', f'Downstream bonded correctable codewords for channel {key}', ['channel'])
    ds_bonded['uccodewords'][key] = Gauge(f'netgear_bonded_downstream_{key}_uncorrectable_codewords', f'Downstream bonded uncorrectable codewords for channel {key}', ['channel'])
for _key in range(1, 9):
    key = str(_key)
    us_bonded['locked'][key] = Gauge(f'netgear_bonded_upstream_{key}_locked', f'Upstream bonded channel {key} is locked(1) or not (0)', ['channel'])
    us_bonded['freq'][key] = Gauge(f'netgear_bonded_upstream_{key}_frequency_hz', f'Upstream bonded frequency for channel {key}', ['channel'])
    us_bonded['power'][key] = Gauge(f'netgear_bonded_upstream_{key}_power_dbmv', f'Upstream bonded power for channel {key}', ['channel'])
for _key in range(1, 3):
    key = str(_key)
    ds_ofdm['locked'][key] = Gauge(f'netgear_ofdm_downstream_{key}_locked', f'Downstream ofdm channel {key} is locked(1) or not (0)', ['channel'])
    ds_ofdm['freq'][key] = Gauge(f'netgear_ofdm_downstream_{key}_frequency_hz', f'Downstream ofdm frequency for channel {key}', ['channel'])
    ds_ofdm['power'][key] = Gauge(f'netgear_ofdm_downstream_{key}_power_dbmv', f'Downstream ofdm power for channel {key}', ['channel'])
    ds_ofdm['snrmer'][key] = Gauge(f'netgear_ofdm_downstream_{key}_snr_mer_db', f'Downstream ofdm SNR/MER for channel {key}', ['channel'])
    ds_ofdm['uecodewords'][key] = Gauge(f'netgear_ofdm_downstream_{key}_unerrored_codewords', f'Downstream ofdm unerrored codewords for channel {key}', ['channel'])
    ds_ofdm['cocodewords'][key] = Gauge(f'netgear_ofdm_downstream_{key}_correctable_codewords', f'Downstream ofdm correctable codewords for channel {key}', ['channel'])
    ds_ofdm['uccodewords'][key] = Gauge(f'netgear_ofdm_downstream_{key}_uncorrectable_codewords', f'Downstream ofdm uncorrectable codewords for channel {key}', ['channel'])
for _key in range(1, 3):
    key = str(_key)
    us_ofdma['locked'][key] = Gauge(f'netgear_ofdma_upstream_{key}_locked', f'Upstream OFDMA channel {key} is locked(1) or not (0)', ['channel'])
    us_ofdma['freq'][key] = Gauge(f'netgear_ofdma_upstream_{key}_frequency_hz', f'Upstream OFDMA frequency for channel {key}', ['channel'])
    us_ofdma['power'][key] = Gauge(f'netgear_ofdma_upstream_{key}_power_dbmv', f'Upstream OFDMA power for channel {key}', ['channel'])


def scrape_modem(modem_ip, username, password):
    # Authenticate and get the status page
    with requests.Session() as s:
        data = {}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        r = requests.get(f'http://{modem_ip}/GenieLogin.asp')
        soup = BeautifulSoup(r.content, features='html.parser')
        data['loginUsername'] = username
        data['loginPassword'] = password
        data['login'] = '1'
        token = soup.select_one('input[name="webToken"]')['value']
        data['webToken'] = token
        payload = urllib.parse.urlencode(data, quote_via=urllib.parse.quote_plus)
        s.post(f'http://{modem_ip}/goform/GenieLogin', headers=headers, data=payload)
        status_page = s.get(f'http://{modem_ip}/DocsisStatus.asp')
    if status_page.status_code == 200:
        total_scrapes.inc()
        # Scrape data from the status page
        soup = BeautifulSoup(status_page.content, features='html.parser')
        ds_table = soup.find('table', id='dsTable').find_all('tr')[1:]
        us_table = soup.find('table', id='usTable').find_all('tr')[1:]
        ds_ofdm_table = soup.find('table', id='d31dsTable').find_all('tr')[1:]
        us_ofdma_table = soup.find('table', id='d31usTable').find_all('tr')[1:]
        ds_hash = {}
        us_hash = {}
        ds_ofdm_hash = {}
        us_ofdma_hash = {}
        for each in ds_table:
            ds_hash[each.contents[0].get_text()] = {
                'lock_status': each.contents[1].get_text(),
                'modulation': each.contents[2].get_text(),
                'channel_id': each.contents[3].get_text(),
                'frequency': each.contents[4].get_text(),
                'power': each.contents[5].get_text(),
                'snr_mer': each.contents[6].get_text(),
                'unerrored_codewords': each.contents[7].get_text(),
                'correctable_codewords': each.contents[8].get_text(),
                'uncorrectable_codewords': each.contents[9].get_text()
            }
        for each in us_table:
            us_hash[each.contents[0].get_text()] = {
                'lock_status': each.contents[1].get_text(),
                'modulation': each.contents[2].get_text(),
                'channel_id': each.contents[3].get_text(),
                'frequency': each.contents[4].get_text(),
                'power': each.contents[5].get_text(),
            }
        for each in ds_ofdm_table:
            ds_ofdm_hash[each.contents[0].get_text()] = {
                'lock_status': each.contents[1].get_text(),
                'modulation': each.contents[2].get_text(),
                'channel_id': each.contents[3].get_text(),
                'frequency': each.contents[4].get_text(),
                'power': each.contents[5].get_text(),
                'snr_mer': each.contents[6].get_text(),
                'active_subcarrier_number_range': each.contents[7].get_text(),
                'unerrored_codewords': each.contents[8].get_text(),
                'correctable_codewords': each.contents[9].get_text(),
                'uncorrectable_codewords': each.contents[10].get_text()
            }
        for each in us_ofdma_table:
            us_ofdma_hash[each.contents[0].get_text()] = {
                'lock_status': each.contents[1].get_text(),
                'modulation': each.contents[2].get_text(),
                'channel_id': each.contents[3].get_text(),
                'frequency': each.contents[4].get_text(),
                'power': each.contents[5].get_text()
            }
        return {
            'ds_bonded': ds_hash,
            'us_bonded': us_hash,
            'ds_ofdm': ds_ofdm_hash,
            'us_ofdma': us_ofdma_hash
        }
    else:
        total_failed_scrapes.inc()


def set_locked(lockstatus: str, gauge: Gauge, channel: str):
    if lockstatus == 'Locked':
        gauge.labels(channel=channel).set(1)
    else:
        gauge.labels(channel=channel).set(0)


def set_ds_metrics(metrics: dict, instruments: dict):
    for key, val in metrics.items():
        set_locked(val['lock_status'], instruments['locked'][key])
        instruments['freq'][key].labels(channel=key).set(float(val['frequency'].replace('Hz', '').strip()))
        instruments['power'][key].labels(channel=key).set(float(val['power'].replace('dBmV', '').strip()))
        instruments['snrmer'][key].labels(channel=key).set(float(val['snr_mer'].replace('dB', '').strip()))
        instruments['uecodewords'][key].labels(channel=key).set(float(val['unerrored_codewords']))
        instruments['cocodewords'][key].labels(channel=key).set(float(val['correctable_codewords']))
        instruments['uccodewords'][key].labels(channel=key).set(float(val['correctable_codewords']))


def set_us_metrics(metrics: dict, instruments: dict):
    for key, val in metrics.items():
        set_locked(val['lock_status'], instruments['locked'][key], key)
        instruments['freq'][key].labels(channel=key).set(float(val['frequency'].replace('Hz', '').strip()))
        instruments['power'][key].labels(channel=key).set(float(val['power'].replace('dBmV', '').strip()))


def export_metrics(modem_ip, username, password, interval):
    metrics = scrape_modem(modem_ip, username, password)
    set_ds_metrics(metrics['ds_bonded'], ds_bonded)
    set_ds_metrics(metrics['ds_ofdm'], ds_ofdm)
    set_us_metrics(metrics['us_bonded'], us_bonded)
    set_us_metrics(metrics['us_ofdma'], us_ofdma)
    time.sleep(interval)


if __name__ == '__main__':
    from yaml import Loader

    try:
        import os
        conf = {
            'modem_ip': os.getenv('PCM_MODEM_IP', '192.168.100.1'),
            'username': os.getenv('PCM_USERNAME', 'admin'),
            'password': os.environ['PCM_PASSWORD'],
            'export_port': os.getenv('PCM_EXPORT_PORT', 9527),
            'interval': os.getenv('PCM_INTERVAL', 10)
        }
    except KeyError:
        logging.warning('Environment variables not found, using config file...')
        with open('/usr/local/prom_cm1000.yaml') as f:
            conf = yaml.load(f.read())

    start_http_server(int(conf.get('export_port', 9527)))
    while True:
        try:
            export_metrics(conf.get('modem_ip', '192.168.100.1'),
                           conf.get('username', 'admin'),
                           conf['password'],
                           conf.get('interval', 10))
        except Exception as exc:
            logging.error(traceback.print_tb(exc.__traceback__))
            generic_failures.inc()
