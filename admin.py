#!/usr/bin/env python
# -*- coding: utf-8 -*-

from models import *

from django.contrib.gis import admin
from django.core import serializers
from django.http import HttpResponse

def make_fixpoint(modeladmin, request, queryset):
    queryset.update(pclass = 1)
make_fixpoint.short_description = "Kontroll"

def make_undefpoint(modeladmin, request, queryset):
    queryset.update(pclass = 8)
make_undefpoint.short_description = "Neupunkt"

def validate_vd(modeladmin, request, queryset):
    for q in queryset.all():
        message = u"%s: %s" %(q.name, q.validate())
        request.user.message_set.create(message=message)
validate_vd.short_description = "Validate for Agl"

def force_save(modeladmin, request, queryset):
    for q in queryset.all():
        q.save()
    message = u"%d %s wurden gespeichert" %(queryset.count(), modeladmin.model._meta.verbose_name_plural)
    modeladmin.message_user(request, message=message)
force_save.short_description = "Force Save"

class OrderInline(admin.TabularInline): #oder StackedInline
    model = Order
    extra = 4

class ProjectAdmin(admin.GeoModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OrderInline]
    
class PointClassAdmin(admin.ModelAdmin):
    #exclude = ['srid',]
    list_display = ('point','fixpoint','get_srid','pclass',)
    actions = [make_fixpoint, make_undefpoint]
    
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('condtyp',)
    
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'p1', 'p2', 'get_points')
    
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('connection', 'obstype', 'direction','unknown_parameters', 'possible_devices')
    
class ObservationClassAdmin(admin.ModelAdmin):
    list_display = ('observation', 'oclass')
    
class VektordataAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'is_valid', 'has_connections', 'unknown_points', 'fixpoints')
    actions = [validate_vd]

admin.site.register(Order)
admin.site.register(Device)
admin.site.register(DeviceVendor)
admin.site.register(DeviceSensor)
admin.site.register(Project, ProjectAdmin)
admin.site.register(SinglePoint)
admin.site.register(Connection, ConnectionAdmin)
admin.site.register(Vektordata, VektordataAdmin)
admin.site.register(Rasterdata)
admin.site.register(Observation, ObservationAdmin)
admin.site.register(ObservationClass, ObservationClassAdmin)
admin.site.register(Condition, ConditionAdmin)
admin.site.register(PointClass, PointClassAdmin)

admin.site.add_action(force_save)
