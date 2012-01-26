#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User, Group
from django.template import RequestContext

def index(request):
    
    return render_to_response('ogna/index.html', 
                              locals(), 
                              context_instance=RequestContext(request))