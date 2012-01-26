#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
#from ogna import views as ogna_views

urlpatterns = patterns('karrie.django.ogna.views',
    url(r'^$', 
        'index', 
        name='ogna_index'),

)
