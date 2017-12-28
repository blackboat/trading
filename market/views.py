from django.shortcuts import render
from django.http import HttpResponse
import requests
import json
import csv
import boto.s3
import sys
from boto.s3.key import Key
import datetime


def index(request):
	if request.method == "POST":
		start_date = request.POST.get('start_date')
		end_date = request.POST.get('end_date')
		interval = request.POST.get('interval')
		currency = ['EUR=', 'JPY=', 'GBP=', 'CHF=', 'CAD=', 'AUD=', 'NZD=',	'SEK=', 'NOK=',	'CZK=', 'HUF=',	'PLN=']
		url = 'http://54.152.240.172/market/?currency=%s&start_date=%s&end_date=%s&interval=%s' % (','.join([c.rstrip('=') for c in currency]), start_date, end_date, interval)
		req = requests.get(url)
		if req.status_code == 200:
			data = json.loads(req.text)
			tmp = []
			for i in range(len(data['dates'])):
				tmp.append([data['dates'][i]] + [data[c][i] for c in currency])
				if i != len(data['dates']) - 1:
					cur = data['dates'][i].split(' ')[0]
					cur = datetime.datetime.strptime(cur, '%Y-%m-%d')
					next = data['dates'][i+1].split(' ')[0]
					next = datetime.datetime.strptime(next, '%Y-%m-%d')
					diff = next - cur
					if diff.days > 1:
						for j in range(diff.days-1):
							next = cur + datetime.timedelta(j+1)
							tmp.append([next.strftime('%Y-%m-%d %H:%M:%S')] + [data[c][i] for c in currency])

			with open('media/data.csv', 'w') as csv_file:
				writer = csv.writer(csv_file)
				writer.writerow(['TimeStamp'] + currency)
				for row in tmp:
					writer.writerow(row)
			context = {
				'data': tmp,
				'currency': currency,
				'start_date': start_date,
				'end_date': end_date,
				'interval': interval,
			}
		else:
			context = {
				'error': req.text,
			}
		return render(request, 'market/index.html', context)

	return render(request, 'market/index.html')


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