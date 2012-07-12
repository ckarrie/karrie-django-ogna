#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django import forms
from django.forms.models import inlineformset_factory
from django.forms.util import ErrorList
import models as ogna_models
import utils
from decimal import Decimal

IPLF_trenn_Choices = (
                ('tab', 'Tabulator'),
                ('space', 'Leerzeichen'),
                ('comma', 'Komma'),
                )

IPLF_EOL_Choices = (
                ('win', 'Windows'),
                ('unix', 'Unix/Linux'),
                ('mac', 'Mac'),
                )

IPLF_srid_Choices = (
                 (2056, 'CH1903+ / LV95'),
                 (21781, 'CH1903 / LV03'),
                 (4326, 'WGS 84'),
                 (4327, 'WGS 84 (geographic 3D)'),
                 (4329, 'WGS 84 (3D)'),
                 )
    
class ImportPointListForm(forms.ModelForm):
    lines = forms.CharField(widget=forms.Textarea(attrs={'cols':'100'}), help_text="Format: Punktname  X  Y  Z")
    trenn = forms.ChoiceField(choices=IPLF_trenn_Choices)
    srid = forms.ChoiceField(choices=IPLF_srid_Choices, help_text="See <a href='http://spatialreferences.org/'>http://spatialreferences.org/</a>")
    start = forms.IntegerField(initial=1, help_text="Nummer der Linie, in der mit dem Import begonnen wird")
    EOL = forms.ChoiceField(choices=IPLF_EOL_Choices, help_text="Aufpassen")
    class Meta:
        fields = ('lines', 'trenn', 'start', 'srid')
        model = ogna_models.SinglePoint
        
        def clean(self):
            cleaned_data = self.cleaned_data
            obj = self.instance
            
            
            
            return super(ImportPointListForm, self).clean()

class ConnectionsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ConnectionsForm, self).__init__(*args, **kwargs)
        self.fields['vektordata'].widget = forms.HiddenInput()
    
    def clean(self):
        if self.cleaned_data['p1'] == self.cleaned_data['p2']:
            self._errors["p1"] = ErrorList(['P1 darf nicht gleich P2 sein'])
            del self.cleaned_data['p1']
            del self.cleaned_data['p2']
                
        else:
            if utils.validate_connection(self.cleaned_data['vektordata'], self.cleaned_data['p1'], self.cleaned_data['p2']):
                pass
            else:
                self._errors["p1"] = ErrorList(['Verbindung in dieser Form schon vorhanden'])
                del self.cleaned_data['p1']
        
        return super(ConnectionsForm, self).clean()
        
    class Meta:
        fields = ('name', 'p1','p2', 'vektordata')
        model = ogna_models.Connection
        
class ConnectionNameForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ConnectionNameForm, self).__init__(*args, **kwargs)
        self.fields['vektordata'].widget = forms.HiddenInput()
        self.fields['p1'].widget = forms.HiddenInput()
        self.fields['p2'].widget = forms.HiddenInput()
        
    class Meta:
        fields = ('name', 'vektordata', 'p1', 'p2')
        model = ogna_models.Connection
        
class ProjectForm(forms.ModelForm):
    class Meta:
        model = ogna_models.Project
        fields = ('name', 'status')
        
class OrderForm(forms.ModelForm):
    class Meta:
        model = ogna_models.Order
        fields = ('name', 'project')
        
class VektordataForm(forms.ModelForm):
    class Meta:
        model = ogna_models.Vektordata
        fields = ('name',)

class SinglePointForm(forms.ModelForm):

    fixpoint = forms.BooleanField(required=False)
    
    def clean(self):
                        
        return super(SinglePointForm, self).clean()
        
    
    class Meta:
        model = ogna_models.SinglePoint
        fields = ('name','fixpoint')
        
class ObservationForm(forms.ModelForm):
   
    def __init__(self, *args, **kwargs):
        super(ObservationForm, self).__init__(*args, **kwargs)
        self.fields['connection'].widget = forms.HiddenInput()

    
    def clean(self):
        if self.cleaned_data.has_key('obstype'):
            if self.cleaned_data['obstype'] != 'levelling':
                if self.cleaned_data['obstype'] != 'distance':
                    #self._errors["obstype"] = ErrorList(['Leider bisher nur Nivellements und Distanzmessung, Sorry'])
                    #del self.cleaned_data['obstype']
                    pass
                

        return super(ObservationForm, self).clean()

    class Meta:
        model = ogna_models.Observation
        fields = ('use', 'obstype','direction','connection')

class ObservationClassForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(ObservationClassForm, self).__init__(*args, **kwargs)
      
        try:
            if self.instance:
                self.fields['device'].queryset = self.instance.observation.possible_devices()
        except ogna_models.Observation.DoesNotExist:
            pass
    
    def clean(self):
        if self.cleaned_data.has_key('device'):
            try:
                if self.cleaned_data['device'] in self.instance.observation.possible_devices():
                    print "ok"
                else:
                    print "nich ok"
            except ogna_models.Observation.DoesNotExist:
                pass
            
            if self.cleaned_data.has_key('oclass'):
                if self.cleaned_data['oclass'] == 8:
                    self.cleaned_data['measvalue'] = 0
                    self.cleaned_data['measunit'] = 'm'
                    
        return super(ObservationClassForm, self).clean()

    class Meta:
        model = ogna_models.ObservationClass
        fields = ('oclass','device', 'measvalue', 'measunit', 'use', 'from_device')
        
ObservationClassFormSet = inlineformset_factory(ogna_models.Observation, 
                                                ogna_models.ObservationClass,
                                                extra=3,
                                                fk_name = 'observation',
                                                exclude = 'correctionparams',
                                                form = ObservationClassForm)



