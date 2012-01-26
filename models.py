#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.urlresolvers import reverse
from django.db import models as django_models
from django.db import IntegrityError



from decimal import Decimal

TYP_CHOICES = (
               (u'levelling', u'Nivellement'),
               (u'distance', u'Distanzmessung'),
               (u'h_angle', u'Horizontalwinkelmessung'),
               (u'v_angle', u'Vertikalwinkelmessung'),
               (u'z_angle',u'Zenitwinkelmessung'),
               (u'azimuth', u'Azimutmessung'),
               (u'gps_rtk', u'GPS-RTK-Messung'),
               (u'gps_rs', u'GPS-Rapid-Static-Messung')
              )

DIRECTION_CHOICES = (
                     (+1, u'Hinmessung'),
                     (-1, u'Rueckmessung'),
                     ( 0, u'Hin und Rueckmessung'),
                    )
UNITS_CHOICES = (
                 (u'km', u'km'),
                 (u'm', u'm'),
                 (u'mm', u'mm'),
                 (u'gon', u'gon'),
                 (u'mgon', u'mgon'),
                 (u'ppm', u'ppm')
                )

COND_CHOICES = (
                (u'triangle', u'Dreiecks-Bedinung'),
                (u'anglesum', u'Winkelsummen-Bedingung'),
                (u'distance', u'Stecken-Bedingung'),
                (u'lotfuss', u'Lotfußpunkt-Bedingung'),
               )

POINT_CLASS_CHOICES = (
                 (1,u'Kontroll'),
                 (2,u'Referenz'),
                 (3,u'Ausgeglichen'),
                 (4,u'Gemittelt'),
                 (5,u'Gemessen'),
                 (6,u'SPSS'),
                 (7,u'Navigiert'),
                 (8,u'Geschätzt'),
                )

OBS_CLASS_CHOICES = (
                  (1,u'Referenzmessung'),
                  (2,u'Bedingt Ausgeglichen'),
                  (3,u'Vermittelnd Ausgeglichen'),
                  (4,u'Gemessen und Korrigiert'),
                  (5,u'arithmetisch gemittelt'),
                  (6,u'Gemessen'),
                  (7,u'Aus Punktkoordinaten'),
                  (8,u'A priori / Geschätzt')
                 )

STATUS_CHOICES = (
                    (u'planning',u'Planung'),
                    (u'accomplishment',u'Ausführung'),
                    (u'analysis',u'Auswertung'),
                 )


class Project(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    zoom = models.IntegerField(blank=True, default='16')
    center = models.PointField(blank=True)
    user = models.ForeignKey(User)
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    objects = models.GeoManager()
    
    class Meta:
        verbose_name = u"Projekt"
        verbose_name_plural = u"Project"
        ordering = ['-id', 'status']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('ogna_project_details', kwargs={'slug':self.slug})

    def get_map_url(self):
        return reverse('ogna_project_map', kwargs={'slug':self.slug})

    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)


class Order(models.Model):
    project =  models.ForeignKey(Project)
    name = models.CharField(max_length=100)
    objects = models.GeoManager()
    
    class Meta:
        verbose_name = u"Auftrag"
        verbose_name_plural = u"Aufträge"
        ordering = ['name',]

    def __unicode__(self):
        return self.name
    
    def get_absolute_url(self):
        return "%s#order%s" %(self.project.get_absolute_url(), self.pk)

    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)
    
class SinglePoint(models.Model):
    attributes = models.TextField(blank=True)
    name = models.CharField(max_length=30)
    geom = models.PointField(dim=2) #Kartenposition
    objects = models.GeoManager()
    
    class Meta:
        ordering = ['name',]
        verbose_name = u"Einzelpunkt"
        verbose_name_plural = u"Einzelpunkte"
    
    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('ogna_show', kwargs={'pk':self.pk, 
                                              'model':self._meta.object_name})

    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)
    
    def latest_point_by_class(self):
        if self.pointclass_set.all().count() != 0:
            lowest = self.pointclass_set.aggregate(django_models.Min('pclass'))
            minvalue = lowest['pclass__min']
            return self.pointclass_set.get(pclass = minvalue)
        else:
            self.save()
                
    def update_fixed_observations(self):
        import karrie_info.ogna.utils as ogna_utils
        for conn in self.connection_set.all():
            for obs in conn.observation_set.filter(obstype__in = ['distance', 'azimuth']):
                dist_unit = 'm'
                azi_unit = 'gon'
                dist = ogna_utils.distance_ellipsoid([conn.p1, conn.p2], unit=dist_unit)
                azi = ogna_utils.azimuth([conn.p1, conn.p2])
                azi_gon = Decimal(str(azi*10.0/9.0))
                oclass = obs.observationclass_set.get(oclass=7)
                if obs.obstype == 'distance':
                    oclass.measvalue = Decimal(str(dist))
                    oclass.measunit = dist_unit
                elif obs.obstype == 'azimuth':
                    oclass.measvalue = azi_gon
                    oclass.measunit = azi_unit
                print oclass.save()
                #print obs.fixed().update()
                
    def save(self):
        super(SinglePoint, self).save()
        if self.pointclass_set.all().count() == 0:
            #new_pc = PointClass(point=self, pclass=8, x=Decimal(str(self.geom.x)), y=Decimal(str(self.geom.y)), fixpoint=False)
            new_pc = PointClass(point=self, pclass=8, xyz=self.geom, fixpoint=False)
            new_pc.save()
        else:
            #update latest_point_by_class
            pass
        
        if self.connection_set.count():
            self.update_fixed_observations()
    
class UnconnectedPointsManager(models.Manager):
    def get_query_set(self):
        #return super(UnconnectedPointsManager, self).get_query_set().filter(display=True)
        return SinglePoint.objects.filter(connection__isnull = True)
    
class Vektordata(models.Model):
    order = models.ForeignKey(Order)
    display = models.BooleanField(u"Anzeigen", default=True)
    name = models.CharField(max_length=100)
    objects = models.GeoManager()
    #unconnected_points = UnconnectedPointsManager()
    is_valid = models.BooleanField(editable=False, default=False)
    
    class Meta:
        verbose_name = u"Vektordaten/Layer"
        verbose_name_plural = u"Vektordaten/Layer"
        order_with_respect_to = 'order'
        ordering = ['name',]

    
    def __unicode__(self):
        return u'%s, Validiert: %s' %(self.name, self.is_valid)
    
    def unconnected_points(self):
        return SinglePoint.objects.filter(connection__isnull = True)


    def get_absolute_url(self):
        return "%s#layer%s" %(self.order.project.get_absolute_url(), self.pk)

    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)
        
    def has_connections(self):
        if self.connection_set.count() > 0:
            return True
        else:
            return False
    
    def unknown_points(self):
        up = []
        for point in self.connected_points():
            if not point.latest_point_by_class().fixpoint and point not in up:
                up.append(point)
        return up

    def unknown_points_count(self):
        return len(self.unknown_points())
    
    
    def unknown_parameters(self):
        
        azi = self.unknown_points()
        
        
        
        parameters = {u'levelling' : self.unknown_points(),
                      u'distance' : self.unknown_points(),
                      u'azimuth' : azi,
                      }
        
        """
        Bei Distanzmessung: Additionskonst. und Massstab (ppm),
        Bei Winkelmessung: Orientierungsunbekannte
        
        Weitere mit einer neuen Tabelle
        """
        
        return parameters
        
    
    def fixpoints(self):
        return SinglePoint.objects.filter(connection__vektordata = self).filter(pointclass__pclass = 1).distinct()
    
    
    def connected_points(self):
        return SinglePoint.objects.filter(connection__vektordata = self)
    
    def validate(self):
        obs_without_obsclass = self.connection_set.filter(observation__observationclass__isnull=True)
        if self.has_connections():
            if self.connection_set.filter(observation__isnull=True).count() > 0:
                self.is_valid = False
                ret_text = u'Verbindungen haben teilweise keine Beobachtungen und, müssen dies aber haben'
            elif obs_without_obsclass.count() > 0:
                self.is_valid = False
                text_list = ""
                for obs in obs_without_obsclass:
                    text_list += " " + obs.name
                ret_text = u"Folgende Verbindungen haben keine Beobachtungsklassen: %s" %(text_list)
            else:
                count_points_in_vd = SinglePoint.objects.filter(connection__vektordata = self).distinct().count() - 1
                count_connections = self.connection_set.count()
                if count_points_in_vd <= count_connections:
                    if self.fixpoints().count() == 0:
                        self.is_valid = False
                        ret_text = u"Keine Lagerung (kein Festpunkt gewählt)"
                    else:
                        self.is_valid = True
                        ret_text = u'Ist validiert mit %i Punkten in %i Verbindungen' %(count_points_in_vd + 1, count_connections)
                else:
                    self.is_valid = False
                    ret_text = u'Mind. 1 Objektgruppe bzw. Objekt ist nicht Verbunden: %i Punkte in %i Verbindungen' %(count_points_in_vd + 1, count_connections)
        else:
            self.is_valid = False
            ret_text = u'Vektordata hat keine Verbindungen'
        
        self.save()
        return ret_text
    
    def save(self):
        super(Vektordata, self).save()
        
    has_connections.short_description = u"Hat Verbindungen?"
    fixpoints.short_description = u"Festpunkte"
    unknown_points.short_description = u"Neupunkte (X_i)"
        
class Condition(models.Model):
    condtyp = models.CharField(max_length=100, choices=COND_CHOICES)
    objects = models.GeoManager()

    class Meta:
        verbose_name = u"Bedingung"
        verbose_name_plural = u"Bedingungen"

    def __unicode__(self):
        return dict(COND_CHOICES)[self.condtyp]

    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)

class Connection(models.Model):
    """
    - evtl mal unter http://docs.djangoproject.com/en/dev/topics/db/models/#intermediary-manytomany schauen
    - 
    """
    vektordata = models.ForeignKey(Vektordata)
    name = models.CharField(max_length=100, help_text="Name der Verbindung")
    points = models.ManyToManyField(SinglePoint, editable=False, blank=True)
    p1 = models.ForeignKey(SinglePoint, related_name='p1_set', help_text="Punkt 1", verbose_name="Standpunkt")
    p2 = models.ForeignKey(SinglePoint, related_name='p2_set', help_text="Punkt 2", verbose_name="Zielpunkt")
    conds = models.ManyToManyField(Condition, blank=True)
    objects = models.GeoManager()
    
    class Meta:
        #order_with_respect_to = 'p1'
        unique_together = (('vektordata', 'p1', 'p2'),('vektordata', 'p2','p1'))
        ordering = ['name','p1', 'p2',]
        verbose_name = u"Verbindung"
        verbose_name_plural = u"Verbindungen"
    
    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('ogna_details', kwargs={
            'pk':self.pk,
            'model':self.model_name()})


    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)

    def get_points(self):
        return SinglePoint.objects.filter(pk__in=[self.p1_id,self.p2_id])
    
    def validate(self, vektordata, p1, p2):
        print "Validate: "
        print vektordata
        print p1
        print p2
    
    def save(self):
        #TODO: Funktion zur Sicherstellung, dass P1 != P2
        has_generated_obs = False
        for obs in self.observation_set.all():
            has_generated_obs += obs.observationclass_set.filter(oclass=7).count()
        print has_generated_obs
        if self.p1 == self.p2:
            raise IntegrityError, "P1 darf nicht gleich P2 sein"
        
        else:
            super(Connection, self).save()
            self.points.clear()
            self.points.add(self.p1)
            self.points.add(self.p2)
            if not has_generated_obs:
                import karrie_info.ogna.utils as ogna_utils
                ogna_utils.generate_observations_from_connection(conn=self)
            
        
class Observation(models.Model):
    connection = models.ForeignKey(Connection) #NEXT
    use = models.BooleanField(u"Aktiv", default=True)
    obstype = models.CharField(u"Typ", max_length=50, choices=TYP_CHOICES)
    direction = models.IntegerField(u"Richtung", max_length=1, choices=DIRECTION_CHOICES)
    objects = models.GeoManager()

    class Meta:
        ordering = ['connection__name',]
        verbose_name = u"Beobachtung"
        verbose_name_plural = u"Beobachtungen"

    def __unicode__(self):
        return "Beob. '%s' in Verbindung '%s'" %(self.get_obstype_display(), self.connection)
    
    def is_apriori(self):
        """
        Sollte sich in Zukunft auf die Projekteinstellung "status" beziehen
        """
        if self.latest_class():
            return self.latest_class().oclass in [7,8] # Punktkoorinaten + Apriori
        else:
            return False


    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)
    
    def latest_class(self):
        if self.observationclass_set.all().count() != 0:
            lowest = self.observationclass_set.aggregate(django_models.Min('oclass'))
            minvalue = lowest['oclass__min']
            return self.observationclass_set.get(oclass = minvalue)
        else:
            #raise ValueError, "No Observationclass set for %s (id=%d)" %(self, self.pk)
            return False
        
    def latest_measured(self):
        if self.latest_class():
            lowest = self.observationclass_set.filter(use=True).filter(oclass__in = [4,5,6]).aggregate(django_models.Min('oclass'))
            minvalue = lowest['oclass__min']
            if minvalue:
                return self.observationclass_set.get(oclass = minvalue)   
            else:
                return False
            
    def latest_calculated(self):
        if self.latest_class():
            lowest = self.observationclass_set.filter(use=True).filter(oclass__in = [7,8]).aggregate(django_models.Min('oclass'))
            minvalue = lowest['oclass__min']
            if minvalue:
                return self.observationclass_set.get(oclass = minvalue)   
            else:
                return False
            
    def fixed(self):
        if self.latest_class():
            return self.observationclass_set.get(oclass = 7)
            
        
    def unknown_parameters(self):
        if self.obstype == 'levelling':
            up = self.connection.get_points().filter(pointclass__pclass = 8)
        else:
            up = "NotSupportedNow"
        return up
    
    def possible_devices(self):
        devices = Device.objects.filter(devicesensor__sensor_type = self.obstype)
        return devices
    possible_devices.short_description = "Passende Instrumente"

class DeviceVendor(models.Model):
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name = u'Instrumentenhersteller'
        verbose_name_plural = u'Instrumentenhersteller'
        
    def __unicode__(self):
        return self.name
    
class Device(models.Model):
    name = models.CharField(max_length=100)
    vendor = models.ForeignKey(DeviceVendor)

    def __unicode__(self):
        return self.name   
 
    class Meta:
        verbose_name = u"Instrument"
        verbose_name_plural = u"Instrumente"
        unique_together = (('name', 'vendor'),)

    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)
    
class ObservationClass(models.Model):
    observation = models.ForeignKey(Observation)
    use = models.BooleanField(u"Aktiv", default=True)
    oclass = models.SmallIntegerField("Beobachtunsklasse", choices=OBS_CLASS_CHOICES, help_text="")
    measvalue = models.DecimalField("Messwert", max_digits=12, decimal_places=5)
    measunit = models.CharField("Einheit", max_length=4, choices=UNITS_CHOICES)
    theorstddev = models.DecimalField("StdAbw", max_digits=12, decimal_places=5, null = True, blank = True)
    theorstddevunit = models.CharField("Einheit", max_length=4, choices=UNITS_CHOICES, null = True, blank = True)
    from_device = models.BooleanField(default = True)
    device = models.ForeignKey(Device)
    correctionparams = models.TextField("Korrekturparameter", max_length=50, blank=True)
    
    class Meta:
        verbose_name = u"Beobachtungsklasse"
        verbose_name_plural = u"Beobachtungsklassen"
        # Jeder Beobachtung hat nur (max) 8 Klassen
        unique_together = (("observation", "oclass"),)
        
    
    def __unicode__(self):
        return "%s in %s" %(self.get_oclass_display(), unicode(self.observation))
    
    def save(self):
        if self.from_device:
            sensor = self.device.devicesensor_set.get(sensor_type=self.observation.obstype)
            self.theorstddev = sensor.sigma0
            self.theorstddevunit = sensor.sigma0_unit
        else:
            #self.theorstddev = None
            print "Passende Instrumente: ", self.observation.possible_devices()
        
        super(ObservationClass, self).save()
    
class PointClass(models.Model):
    """
    Weiter mal hier: http://iowa.hobu.biz/branches/original/references/models.py sehr interessant!!!
    """
    
    point = models.ForeignKey(SinglePoint)
    pclass = models.PositiveSmallIntegerField(choices=POINT_CLASS_CHOICES, default=8)
    xyz = models.PointField(default="SRID=4326;POINT(8.2122802734375 50.0042724609375)", blank=True)
    x = models.DecimalField(max_digits=12, decimal_places=5, blank=True, null=True)
    y = models.DecimalField(max_digits=12, decimal_places=5, blank=True, null=True)
    z = models.DecimalField(max_digits=12, decimal_places=5, blank=True, null=True, default='0')
    objects = models.GeoManager()

    def __unicode__(self):
        if self.point:
            return u"%s: %s" %(self.point, self.get_pclass_display())
        else:
            return self.pclass
        
    def get_srid(self):
        return "%s (%s)" %(self.xyz.srid, self.xyz.srs.name[0:20])
    get_srid.short_description = "SRID"
    
    #1 = Festpunkt
    #8 = Neupunkt
    
    def _get_as_fixpoint(self):
        return self.pclass == 1
    
    def _set_as_fixpoint(self, yes):
        if yes: self.pclass = 1
        else: self.pclass = 8
        self.save()
    
    fixpoint = property(_get_as_fixpoint, _set_as_fixpoint)

    def save(self):
        super(PointClass, self).save()
        
        
    class Meta:
        verbose_name = u"Punktklasse"
        verbose_name_plural = u"Punktklassen"
        # Jeder Punkt hat nur (max) 8 Punktklassen
        unique_together = (("point", "pclass"),)

    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)
        


class Rasterdata(models.Model):
    auftrag = models.ForeignKey(Order)
    name = models.CharField(max_length=100)
    typ = models.CharField(max_length=10)
    url = models.CharField(max_length=1000)
    objects = models.GeoManager()
    
    
    class Meta:
        verbose_name = u"Rasterdaten"
        verbose_name_plural = u"Rasterdaten"

    
    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return u"/rasterdata/%s/" % self.id

    def model_name(self):
        return "%s.%s" %(self._meta.app_label, self._meta.object_name)
        
class DeviceSensor(models.Model):
    device = models.ForeignKey(Device)
    sensor_type = models.CharField("Sensortyp", max_length=100, choices=TYP_CHOICES)
    sigma0 = models.DecimalField("StdAbw 1 Sigma", max_digits=12, decimal_places=5)
    sigma0_unit = models.CharField("Einheit", max_length=100, choices=UNITS_CHOICES)
    sigma1 = models.DecimalField("StdAbw 2 Sigma", null = True, blank = True, max_digits=12, decimal_places=5)
    sigma1_unit = models.CharField("Einheit", max_length=100, choices=UNITS_CHOICES, null = True, blank = True)
    min_measvalue = models.DecimalField("Min. Messwert", null = True, blank = True, max_digits=12, decimal_places=5)
    max_measvalue = models.DecimalField("Max. Messwert", null = True, blank = True, max_digits=12, decimal_places=5)
    scale = models.DecimalField("Massstab", null = True, blank = True, max_digits=12, decimal_places=5)
    scale_unit = models.CharField("Einheit", max_length=100, choices=UNITS_CHOICES, null = True, blank = True)
    
    def __unicode__(self):
        return "%s: %s" %(self.device.name, self.get_sensor_type_display())
    
    class Meta:
        verbose_name = u'Instrumentensensor'
        verbose_name_plural = u'Instrumentensensoren'
        unique_together = (("device", "sensor_type"),)
