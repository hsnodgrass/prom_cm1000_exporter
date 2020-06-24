import logging
import time
import traceback
import urllib.parse
import requests
from bs4 import BeautifulSoup
from prometheus_client import start_http_server, Gauge, Counter

logging.basicConfig(level=logging.INFO)

total_scrapes = Counter(
    'netgear_total_scrapes',
    'Total number of times the modem has been scraped'
)
total_failed_scrapes = Counter(
    'netgear_total_failed_scrapes',
    'Total number of times modem scrapes have failed',
    ['http_response_code']
)
generic_failures = Counter(
    'netgear_generic_failures',
    'Total number of generic failures'
)
i_locked = Gauge(
    'netgear_locked',
    'Channel is locked(1) or not (0)',
    ['channel', 'channel_type', 'direction']
)
i_freq = Gauge(
    'netgear_frequency_hz',
    'Channel frequency',
    ['channel', 'channel_type', 'direction']
)
i_power = Gauge(
    'netgear_power_dbmv',
    'Channel power',
    ['channel', 'channel_type', 'direction']
)
i_snrmer = Gauge(
    'netgear_snr_mer_db',
    'Channel SNR/MER',
    ['channel', 'channel_type', 'direction']
)
i_ue_codewords = Gauge(
    'netgear_unerrored_codewords',
    'Channel unerrored codewords',
    ['channel', 'channel_type', 'direction']
)
i_co_codewords = Gauge(
    'netgear_correctable_codewords',
    'Channel correctable codewords',
    ['channel', 'channel_type', 'direction']
)
i_uc_codewords = Gauge(
    'netgear_uncorrectable_codewords',
    'Channel uncorrectable codewords',
    ['channel', 'channel_type', 'direction']
)


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
        ds_hash['channel_type'] = 'bonded'
        ds_hash['direction'] = 'downstream'
        us_hash = {}
        us_hash['channel_type'] = 'bonded'
        us_hash['direction'] = 'upstream'
        ds_ofdm_hash = {}
        ds_ofdm_hash['channel_type'] = 'ofdm'
        ds_ofdm_hash['direction'] = 'downstream'
        us_ofdma_hash = {}
        us_ofdma_hash['channel_type'] = 'ofdma'
        us_ofdma_hash['direction'] = 'upstream'
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
        logging.info('Successfully scraped metrics...')
        return {
            'ds_bonded': ds_hash,
            'us_bonded': us_hash,
            'ds_ofdm': ds_ofdm_hash,
            'us_ofdma': us_ofdma_hash
        }
    else:
        logging.error('HTTP Error: Failed to scrape metrics, check total_failed_scrapes metric...')
        total_failed_scrapes.labels(
            http_response_code=status_page.status_code
        ).inc()
        raise Exception('HTTP Error: Failed to scrape metrics')


def set_locked(channel: str, channel_type: str, direction: str, metrics: dict):
    if metrics['lock_status'] == 'Locked':
        i_locked.labels(channel=channel, channel_type=channel_type, direction=direction).set(1)
    else:
        i_locked.labels(channel=channel, channel_type=channel_type, direction=direction).set(0)


def set_ds_metrics(metrics: dict):
    channel_type = metrics['channel_type']
    direction = metrics['direction']
    for key, val in metrics.items():
        if key != 'channel_type' and key != 'direction':
            set_locked(key, channel_type, direction, val)
            i_freq.labels(channel=key, channel_type=channel_type, direction=direction).set(float(val['frequency'].replace('Hz', '').strip()))
            i_power.labels(channel=key, channel_type=channel_type, direction=direction).set(float(val['power'].replace('dBmV', '').strip()))
            i_snrmer.labels(channel=key, channel_type=channel_type, direction=direction).set(float(val['snr_mer'].replace('dB', '').strip()))
            i_ue_codewords.labels(channel=key, channel_type=channel_type, direction=direction).set(float(val['unerrored_codewords']))
            i_co_codewords.labels(channel=key, channel_type=channel_type, direction=direction).set(float(val['correctable_codewords']))
            i_uc_codewords.labels(channel=key, channel_type=channel_type, direction=direction).set(float(val['correctable_codewords']))


def set_us_metrics(metrics: dict):
    channel_type = metrics['channel_type']
    direction = metrics['direction']
    for key, val in metrics.items():
        if key != 'channel_type' and key != 'direction':
            set_locked(key, channel_type, direction, val)
            i_freq.labels(channel=key, channel_type=channel_type, direction=direction).set(float(val['frequency'].replace('Hz', '').strip()))
            i_power.labels(channel=key, channel_type=channel_type, direction=direction).set(float(val['power'].replace('dBmV', '').strip()))


def export_metrics(modem_ip, username, password, interval):
    metrics = scrape_modem(modem_ip, username, password)
    set_ds_metrics(metrics['ds_bonded'])
    set_ds_metrics(metrics['ds_ofdm'])
    set_us_metrics(metrics['us_bonded'])
    set_us_metrics(metrics['us_ofdma'])
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
                           int(conf.get('interval', 10)))
        except Exception as exc:
            logging.error(exc)
            logging.error(traceback.print_tb(exc.__traceback__))
            generic_failures.inc()
