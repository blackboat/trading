from django.urls import path
from . import views


urlpatterns = [
	path('', views.index, name='index'),
	path('realtime', views.realtime, name='realtime'),
	path('s3', views.s3, name='s3'),
	path('store', views.store, name='store'),
]