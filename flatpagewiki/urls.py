""" urls.py for flatpagewiki app

"""

from django.conf.urls.defaults import *


urlpatterns = patterns('flatpagewiki.views',
    (r'^(?P<slug>[^/]+)/$', 'showpage'),
    
)