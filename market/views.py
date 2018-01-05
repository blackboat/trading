from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
import csv
import boto.s3
import sys
from boto.s3.key import Key
import datetime
import urllib.parse
from .models import RICCode, Daily


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
		n = 10
		codes = code_list[:n]
		url = 'http://54.152.240.172/market/?codes=%s&start_date=%s&end_date=%s&interval=%s' % (urllib.parse.quote(','.join(codes)), start_date, end_date, interval)
		req = requests.get(url)
		if req.status_code == 200:
			data = json.loads(req.text)
			for i in range(n, len(code_list), n):
				codes = code_list[i:i+n]
				url = 'http://54.152.240.172/market/?codes=%s&start_date=%s&end_date=%s&interval=%s' % (urllib.parse.quote(','.join(codes)), start_date, end_date, interval)
				req = requests.get(url)
				if req.status_code != 200:
					context = {
						'error': 'Eikon API Proxy is shutdown on server!',
					}
					return render(request, 'market/index.html', context)
				data.update(json.loads(req.text))
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
