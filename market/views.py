from django.shortcuts import render
import requests
import json


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
			context = {
				'data': tmp,
				'currency': currency,
			}
		else:
			context = {
				'error': req.text,
			}
		return render(request, 'market/index.html', context)

	return render(request, 'market/index.html')
