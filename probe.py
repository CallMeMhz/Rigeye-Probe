#!/usr/bin/env python3
import sys
import os
import socket
import platform
import requests
import time
import multiprocessing
import json

INSTANCE_ID = ''
# HOST = 'www.rigeye.top:3000'
HOST = 'localhost:8000'
JSON_HEADER = {'content-type': 'application/json'}


def message(text):
	print('[', time.ctime(), '] %s' % text)

def load_stat():
	loadavg = {}
	f = open("/proc/loadavg")
	con = f.read().split()
	f.close()
	loadavg['lavg_1']=con[0]
	loadavg['lavg_5']=con[1]
	loadavg['lavg_15']=con[2]
	loadavg['nr']=con[3]
	loadavg['last_pid']=con[4]
	return loadavg

def get_network_interface_card_names():
	return os.listdir('/sys/class/net/')

def get_bytes(t, iface=''):
	data = 0
	if iface:
		with open('/sys/class/net/' + iface + '/statistics/' + t + '_bytes', 'r') as f:
			data = int(f.read())
		return data
	else:
		for i in get_network_interface_card_names():
			with open('/sys/class/net/' + i + '/statistics/' + t + '_bytes', 'r') as f:
				data += int(f.read())
		return data


def monitor():
	global INSTANCE_ID
	global HOST
	global tx_prev, rx_prev

	while True:
		#
		# TODO: 增加对 MacOS 的支持
		#
		tx_speed, rx_speed = (0, 0)
		tx = get_bytes('tx')
		rx = get_bytes('rx')

		if tx_prev > 0:
			tx_speed = tx - tx_prev

		if rx_prev > 0:
			rx_speed = rx - rx_prev

		jiffy = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
		num_cpu = multiprocessing.cpu_count()

		stat_fd = open('/proc/stat')
		stat_buf = stat_fd.readlines()[0].split()
		user, nice, sys, idle, iowait, irq, sirq = ( float(stat_buf[1]), float(stat_buf[2]),
												float(stat_buf[3]), float(stat_buf[4]),
												float(stat_buf[5]), float(stat_buf[6]),
												float(stat_buf[7]) )

		stat_fd.close()

		time.sleep(1)

		stat_fd = open('/proc/stat')
		stat_buf = stat_fd.readlines()[0].split()
		user_n, nice_n, sys_n, idle_n, iowait_n, irq_n, sirq_n = ( float(stat_buf[1]), float(stat_buf[2]),
																float(stat_buf[3]), float(stat_buf[4]),
																float(stat_buf[5]), float(stat_buf[6]),
																float(stat_buf[7]) )

		stat_fd.close()

		payload = {
			'instance_id': INSTANCE_ID,
			'cpu_percent': ((user_n - user) * 100 / jiffy) / num_cpu,
			'iowait': ((iowait_n - iowait) * 100 / jiffy) / num_cpu,
			'lavg1': load_stat()['lavg_1'],
			'lavg15': load_stat()['lavg_5'],
			'lavg15': load_stat()['lavg_15'],
			'ip': socket.gethostbyname(socket.gethostname()),
			'net_speed_r': rx_speed,
			'net_speed_t': tx_speed,
			'time': time.time()
		}

		requests.post('http://' + HOST + '/rest/add_data', headers=JSON_HEADER, data=json.dumps(payload))

		tx_prev = tx
		rx_prev = rx

def init():
	global INSTANCE_ID
	global HOST
	token_local = ''
	try:
		fp = open('.instance_id', 'r')
		token_local = fp.readline()
		fp.close()

		message('Read token successfully')

		payload = {
			'instance_id': token_local,
			'node': platform.node(),
			'os': platform.system(),
			'status': 'MONITORING'
		}
	except:
		payload = {
			'node': platform.node(),
			'os': platform.system(),
			'status': 'MONITORING'
		}

	print(token_local)

	res = requests.post('http://' + HOST + '/rest/add_info', headers=JSON_HEADER, data=json.dumps(payload))
	INSTANCE_ID = res.text
	
	with open('.instance_id', 'w') as fp:
		fp.write(INSTANCE_ID)

	if INSTANCE_ID != token_local:
		message('Register new token')

	message('TOKEN: ' + INSTANCE_ID)

if __name__ == '__main__':
	init()
	(tx_prev, rx_prev) = (0, 0)
	monitor()
