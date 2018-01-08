from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
import csv
import boto.s3
import sys
from boto.s3.key import Key
import datetime
import urllib.parse
from .models import RICCode, Daily, Realtime


def index(request):
	if request.method == "POST":
		start_date = request.POST.get('start_date')
		end_date = request.POST.get('end_date')
		interval = request.POST.get('interval')
		if datetime.datetime.strptime(start_date, '%Y-%m-%d') >= datetime.datetime.strptime(end_date, '%Y-%m-%d'):
			context = {
				'error': 'End Date must be later than Start Date.',
				'start_date': start_date,
				'end_date': end_date,
				'interval': interval,
			}
			return render(request, 'market/index.html', context)

		currency = ['EUR=', 'JPY=', 'GBP=', 'CHF=', 'CAD=', 'AUD=', 'NZD=',	'SEK=', 'NOK=',	'CZK=', 'HUF=',	'PLN=']
		code_list = [row.code for row in RICCode.objects.all()]
		data = get_data(code_list, start_date, end_date, interval)
		if data:
			tmp = get_formatted_data(data, code_list)
			with open('media/data.csv', 'w') as csv_file:
				writer = csv.writer(csv_file)
				writer.writerow(['TimeStamp'] + code_list)
				for row in tmp[1:]:
					writer.writerow(row)
			context = {
				'data': tmp,
				'codes': code_list,
				'start_date': start_date,
				'end_date': end_date,
				'interval': interval,
			}
		else:
			context = {
				'error': 'Eikon API Proxy is shutdown on server!',
			}
		return render(request, 'market/index.html', context)

	return render(request, 'market/index.html')


def realtime(request):
	if request.method == "POST":
		codes = request.POST.get('codes', None)
		if codes:
			codes = codes.split(',')
			for code in codes:
				RICCode.objects.get_or_create(code=code.strip())

	code_list = [row.code for row in RICCode.objects.all()]
	realtime_vals = get_realtime_data(code_list)
	if realtime_vals:
		context = {
			'data': [realtime_vals[code] for code in code_list],
			'codes': code_list,
		}
	else:
		context = {
			'error': 'Eikon API Proxy is shutdown on server!',
		}
	return render(request, 'market/realtime.html', context)


def get_realtime(request):
	code_list = [row.code for row in RICCode.objects.all()]
	realtime_vals = get_realtime_data(code_list)
	data = {'data': [realtime_vals[code] for code in code_list]}
	return JsonResponse(data)


def get_realtime_data(code_list):
	interval = 'minute'
	current_date = datetime.datetime.utcnow()
	end_date = current_date.strftime("%Y-%m-%d %H:%M:%S")
	start_date = (current_date-datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
	data = get_data(code_list, start_date, end_date, interval)
	realtime_vals = {}

	if not data:
		return False
	
	nan_codes = []

	def last_val(vals, dates):
		for val,date in zip(reversed(vals), reversed(dates)):
			if isinstance(val, float) and str(val) != 'nan':
				return val, date
		return None, None

	for code in code_list:
		ric_code, created = RICCode.objects.get_or_create(code=code)
		if code not in data:
			nan_codes.append(code)
			continue
		val, date = last_val(data[code], data['dates'])
		if val:
			realtime_vals[code] = val
			realtime, created = Realtime.objects.get_or_create(ric_code=ric_code)
			realtime.value = val
			realtime.date = date
			realtime.save()
		else:
			nan_codes.append(code)

	if nan_codes:
		while (nan_codes):
			end_date = start_date
			start_date = (datetime.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")-datetime.timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
			data = get_data(nan_codes, start_date, end_date, 'hour')
			if not data:
				return False
			codes = nan_codes[:]
			for code in codes:
				val, date = last_val(data[code], data['dates'])
				if val:
					ric_code = RICCode.objects.get(code=code)
					realtime_vals[code] = val
					realtime, created = Realtime.objects.get_or_create(ric_code=ric_code)
					realtime.value = val
					realtime.date = date
					realtime.save()
					nan_codes.remove(code)
	return realtime_vals


def get_data(code_list, start_date, end_date, interval, n=10):
	codes = code_list[:n]
	url = 'http://54.152.240.172/market/?codes=%s&start_date=%s&end_date=%s&interval=%s' % (urllib.parse.quote(','.join(codes)), start_date, end_date, interval)
	req = requests.get(url)
	if req.status_code == 200:
		data = json.loads(req.text)
		for i in range(n, len(code_list), n):
			sub_codes = code_list[i:i+n]
			url = 'http://54.152.240.172/market/?codes=%s&start_date=%s&end_date=%s&interval=%s' % (urllib.parse.quote(','.join(sub_codes)), start_date, end_date, interval)
			req = requests.get(url)
			if req.status_code != 200:
				return False
			data.update(json.loads(req.text))
		
		# in case of code_list have one element
		if 'CLOSE' in data:
			return {code_list[0]: data['CLOSE'], 'dates': data['dates']}

		return data
	return False


def get_formatted_data(data, codes):
	tmp = []
	for i in range(len(data['dates'])):
		vals = []
		for c in codes:
			if str(data[c][i]) == 'nan' and i > 0:
				vals.append(data[c][i-1])
			else:
				vals.append(data[c][i])
		tmp.append(['W', data['dates'][i]] + vals)
	return tmp


def s3(request):
	AWS_ACCESS_KEY_ID = 'AKIAJX4LF2MP4X2XUANQ'
	AWS_SECRET_ACCESS_KEY = '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'

	bucket_name = AWS_ACCESS_KEY_ID.lower() + '-dump'
	conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

	try:
		bucket = conn.get_bucket(bucket_name)
	except:
		bucket = conn.create_bucket(bucket_name, location=boto.s3.connection.Location.DEFAULT)

	testfile = "media/data.csv"

	def percent_cb(complete, total):
		sys.stdout.write('.')
		sys.stdout.flush()

	k = Key(bucket)
	k.key = 'my test file'
	k.set_contents_from_filename(testfile, cb=percent_cb, num_cb=10)
	return HttpResponse('Success')


@csrf_exempt
def store(request):
	start_date = request.POST.get('start_date')
	end_date = request.POST.get('end_date')
	interval = request.POST.get('interval')
	if interval != 'daily':
		return HttpResponse('Success')
	codes = [row.code for row in RICCode.objects.all()]
	url = 'http://54.152.240.172/market/?codes=%s&start_date=%s&end_date=%s&interval=%s' % (urllib.parse.quote(','.join(codes)), start_date, end_date, interval)
	req = requests.get(url)
	if req.status_code == 200:
		data = json.loads(req.text)
		tmp = get_formatted_data(data, codes)
		dailys = []
		for i, dt in enumerate(data['dates']):
			for code in codes:
				dailys.append(Daily(ric_code=RICCode.objects.get(code=code), datetime=dt, value=data[code][i]))
		Daily.objects.bulk_create(dailys)
		return HttpResponse('Success')
	return HttpResponse('Eikon API Proxy is shutdown on server!')
