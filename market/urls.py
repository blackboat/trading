from django.urls import path
from . import views


urlpatterns = [
	path('', views.index, name='index'),
	path('realtime', views.realtime, name='realtime'),
	path('get_realtime', views.get_realtime, name='get_realtime'),
	path('s3', views.s3, name='s3'),
	path('store', views.store, name='store'),
	path('ric_codes', views.ric_codes, name='ric_codes'),
	path('update_codes', views.update_codes, name='update_codes'),
]