#!/usr/bin/env python
# -*- coding: utf-8 -*-

from models import SinglePoint, Vektordata, Connection, Device, Observation, ObservationClass
from decimal import Decimal
import math
import numpy
from geocalc import globe
from geopy import distance as g_distance
import geopy

def azimuth_and_distance(points, azi_unit = 'grad', dist_unit = 'm'):
    if len(points) == 2:
        pA = math.radians(points[0].geom.x)
        lA = math.radians(points[0].geom.y)
        pB = math.radians(points[1].geom.x)
        lB = math.radians(points[1].geom.y)
        
        azi = globe.azimuth(pA, lA, pB, lB)
        dist = globe.distance(alpha=math.radians(azi['alpha']),
             beta=math.radians(azi['beta']),
             pA=azi['pA'], 
             pB=azi['pB'])
        
        azimuth = 90.0-azi['alpha']
        distance = dist['s']
             
        return azimuth, distance
        
def azimuth(points, azi_unit = 'grad'):
    if len(points) == 2:
        pA = math.radians(points[0].geom.x)
        lA = math.radians(points[0].geom.y)
        pB = math.radians(points[1].geom.x)
        lB = math.radians(points[1].geom.y)
        
        azi = globe.azimuth(pA, lA, pB, lB)
        azimuth = 90.0-azi['alpha']
             
        return azimuth
        
def distance_ellipsoid(points, unit='m'):
    if len(points) == 2:
        pA = points[0].geom.x
        lA = points[0].geom.y
        pB = points[1].geom.x
        lB = points[1].geom.y
        
        a = geopy.Point(pA, lA)
        b = geopy.Point(pB, lB)
        
        
        g_distance.distance = g_distance.VincentyDistance
        dist = getattr(g_distance.distance(a, b), unit)
        return dist

def distance_great_circle(points):
    if len(points) == 2:
        pA = points[0].geom.x
        lA = points[0].geom.y
        pB = points[1].geom.x
        lB = points[1].geom.y
        
        a = geopy.Point(pA, lA)
        b = geopy.Point(pB, lB)
        
        g_distance.distance = g_distance.GreatCircleDistance
        return g_distance.distance(a, b).m

    
def global_unused_points():
    return SinglePoint.objects.filter(connection__p2=None).distinct()

def validate_connection(vd, p1, p2, connection=False):
    valid = True
    
    if connection:
        current_conn = Connection.objects.get(pk=connection)
    
    for conn in vd.connection_set.all():
        
        both = conn.get_points().filter(pk__in = [p1.pk, p2.pk]).distinct()
        if both.count() > 1:
            if connection:
                if conn.name != current_conn.name:
                    #print conn.name, current_conn.name
                    valid = False
            else:
                valid = False
            break
        
    return valid

def generate_observations_from_connection(conn):
    azi= azimuth([conn.p1, conn.p2])
    d = distance_ellipsoid([conn.p1, conn.p2], unit='m')
    dist = Decimal(str(d))
    azi_gon = Decimal(str(azi*10.0/9.0))
    
    #print dist, azi_gon
    
    map_device = Device.objects.get(name__exact = '_Map')
    
    map_distance_obs = Observation(connection=conn, use=True, obstype='distance', direction=1)
    map_distance_obs.save()
    
    map_distance_obsclass = ObservationClass(observation = map_distance_obs, use = True, oclass = 7, measvalue = dist, measunit = 'm', from_device = True, device = map_device)
    map_distance_obsclass.save()
    
    map_azi_obs = Observation(connection=conn, use=True, obstype='azimuth', direction=1)
    map_azi_obs.save()
    
    map_azi_obsclass = ObservationClass(observation=map_azi_obs, use = True, oclass = 7, measvalue = azi_gon, measunit = 'gon', from_device = True, device = map_device)
    map_azi_obsclass.save()
    
    return True



class Ausgleichung(object):
    
    # Zur Zeit nur Nivellements bis
    # http://groups.google.com/group/geodjango/browse_thread/thread/2f50f336dec00286
    # und
    # http://code.djangoproject.com/ticket/11854
    # gefixed wird
    
    def __init__(self, network):
        
        self.supported_obstypes = [
                         'levelling',
                         #'distance',
                         #'azimuth',
                         ]
        self.s0 = 1
        
        self._network = network
        self.detected_groups = self._detect_observationgroups()
        self.observationgroups = self._get_observationgroups()
        self.unknown_parameters = self._get_unknown_parameters()
        
        self._A, self._p, self._l = self._generate_Apl()
        self._results = self._calculate()
        self.results_for_table = self.as_table()
    
    def _get_observations(self, group, use=True):
        """
        group = ('levelling', 'azimuth', 'distance')
        return: Beobachtungen in Messgruppen in 
                einer liste. [Beob1, Beob2]
         }
        """
        return Observation.objects.filter(use=use, obstype=group).filter(connection__vektordata = self._network)
    
    def _get_observationgroups(self):
        """
        Gibt ein Dict mit den Gruppierten Beobachtungen wieder:
            {
             'distance':
                [obs1, obs2, obs3],
             'levelling':
                 [obs4, obs5, obs6]
             }
        """
        groups_with_observations = {}
        
        #print self.detected_groups
        
        for group in self.detected_groups:
            if group in self.supported_obstypes:
                groups_with_observations[group] = self._get_observations(group)
            
        return groups_with_observations
    
    def _detect_observationgroups(self, use=True):
        """
        Erkennt aus dem Beobachtungen die Beobachtungsklasse
        return: detected_groups = ['levelling', 'distance']
        """
        
        detected_groups = []
        
        print "Beonachtungen: ", self._network.connection_set.all()
        
        for conn in self._network.connection_set.all():
            for obs in conn.observation_set.filter(use=use):
                if obs.obstype not in detected_groups:
                    detected_groups.append(obs.obstype)
        return detected_groups
    
    def _get_unused_observations_in_group(self, group):
        return self._get_observations(group, use=False)
    
    def _get_unknown_parameters(self):
        """
        Gibt eine Liste von unbekannten Parametern wieder:
            {
             '...':
                [..., ...],
             '...':
                [..., ...],
             }
        """
        
        supported = {}
        
        for obstype, para in self._network.unknown_parameters().items():
            if obstype in self.supported_obstypes:
                supported[obstype] = para
        
        #return self._network.unknown_parameters()
        return supported
    
    def _generate_Apl(self):
        """
        Generiert die A-Matrix
        """
        
        A = []
        l = []
        p = []
        
        #print self.observationgroups
        
        for group, observations in self.observationgroups.items():
            for obs in observations:
                if obs.obstype in self.supported_obstypes:
                    a_obs = []
                    l.append([self._get_abspart(obs)])
                    p.append(self._get_loading(obs))
                    for para, unknown_para in self.unknown_parameters.items():
                        
                        for up in unknown_para:
                        
                            if up in obs.connection.points.all() and group == para:
                                #a_obs.append('%s -> %s' %(obs.connection.p1, obs.connection.p2))
                                a_obs.append(self._get_koeff(up, para, obs))
                            else:
                                #print '%s no in %s' %(up, obs.connection.points.all())
                                a_obs.append(0)
                    #print a_obs
                    A.append(a_obs)

        return A, p, l
    
    def _gererate_B_matrix(self):
        """
        Generiert die B-Matrix (Bedinungsmatrix)
        """
        pass
    
    def _save_new_pointclasses(self):
        """
        Speichert die ausgeglichenen Beobachtungen in einer neuen PunktKlasse
        """
        pass

    def _get_koeff(self, up, group, obs):
        if group in self.supported_obstypes:
            #print "_get_koeff: Group %(group)s supported" %{'group':group}
            return getattr(self, '_get_%(group)s_koeff' %{'group':group})(up, obs)
        else:
            return 0

    def _get_levelling_koeff(self, up, obs):
        pc1 = obs.connection.p1.latest_point_by_class()
        pc2 = obs.connection.p2.latest_point_by_class()
        
        # Swap
        if obs.direction == -1:
            pc1, pc2 = pc2, pc1

        current = up.latest_point_by_class()
        
        if (pc1 != current) and (pc2 != current): return 0
        elif pc1 == current: return -1
        elif pc2 == current: return 1

    def _get_distance_koeff(self, up, obs):
        """
        Bisher nicht unterstützt, deshalb das geliche wie beim Niv
        """
        pc1 = obs.connection.p1.latest_point_by_class()
        pc2 = obs.connection.p2.latest_point_by_class()
        
        # Swap
        if obs.direction == -1:
            pc1, pc2 = pc2, pc1

        current = up.latest_point_by_class()        
        alpha = math.radians(float(obs.latest_class().measvalue)*9/10)
        
        if (pc1 != current) and (pc2 != current): return 0
        elif pc1 == current: return math.cos(alpha)
        elif pc2 == current: return -math.cos(alpha)
    
    def _get_azimuth_koeff(self, up, obs):
        """
        Bisher nicht unterstützt, deshalb das geliche wie beim Niv
        """
        pc1 = obs.connection.p1.latest_point_by_class()
        pc2 = obs.connection.p2.latest_point_by_class()
        
        # Swap
        if obs.direction == -1:
            pc1, pc2 = pc2, pc1

        current = up.latest_point_by_class()
        
        alpha, dist = azimuth_and_distance([obs.connection.p1,obs.connection.p2], azi_unit='grad', dist_unit='m')
        
        if (pc1 != current) and (pc2 != current): return 0
        elif pc1 == current: return -(math.sin(alpha)/dist)
        elif pc2 == current: return +(math.sin(alpha)/dist)
    
    def _get_abspart(self, obs):
        if obs.is_apriori():
            return 0
        else:
            #Gemessen - Gerechnet
            lm = obs.latest_measured()
            lc = obs.latest_calculated()
            
            if lm and lc:
                """
                TODO: Umrechnungen hier (firkin?)
                """
                return lm.measvalue - lc.measvalue
            else:
                return 1234567
            
    def _get_loading(self, obs):
        if obs.obstype == 'levelling':
            dist = distance_ellipsoid([obs.connection.p1, obs.connection.p2], unit = 'km')
            pi = 1/math.sqrt(dist)
        else:
            pi = self.s0 / float(obs.latest_class().theorstddev**2)
        return pi
    
    def _calculate(self):
        A = numpy.matrix(self._A)
        A_height, A_width = A.shape
        l = numpy.matrix(self._l)
        P = numpy.matrix(numpy.diag(self._p))
        s0 = self.s0
        error_msg = []
        
        try:
            N = A.T*P*A
            Na, Nb = N.shape
        except ValueError, e:
            Na = 0
            Nb = 1
            error_msg.append(e)
        
        
        
        if Na == Nb:
            error_msg.append(["Kapitel GSA: Mathematische Modelle der Netzberechnung, Netzlagerung",
                         "#4: Lösung ist ein freies Netz"])
        
        try:
            n = A.T*P*l
            #print "n", n.shape
            x = N.I*n
            #print "x", x.shape
            Qxx = N.I
            Q = P.I
            Qquer = A*Qxx*A.T
            Qvv = Q-Qquer
            v = A*x-l
            f = len(A)-A.ndim
            m0 = numpy.sqrt((v.T*P*v)/f)
            q = m0**2/s0**2
            mX = m0*numpy.sqrt(numpy.diag(Qxx))
            sX = s0*numpy.sqrt(numpy.diag(Qxx))
            FFrei = P*Qvv
            zi = numpy.diag(FFrei)
            sv = s0*numpy.sqrt(numpy.diag(Qvv))
            nl = 4.1*(sv/zi)
            nx = (N.I*A.T*P*numpy.diag(nl)).T
            success = True
            error_msg = None
        except (numpy.linalg.LinAlgError, ValueError), e:
            success = False
            error_msg.append(e)

        #parse_time = time.time() - cur
        if success:
            results = {
                       'A':A.tolist(),
                       'l':l.tolist(),
                       'p':P.tolist(),
                       'N':N.tolist(),
                       'v':v.tolist(),
                       'm0':m0.tolist(),
                       'q':q.tolist(),
                       'mX':mX.tolist(),
                       'sX':sX.tolist(),
                       'zi':zi.tolist(),
                       'sv':sv.tolist(),
                       'nx':nx.tolist(),
                       'nl':nl.tolist(),
                       'error_msg':error_msg,
                       'success':success,
                       #'parse_time':parse_time,
                       #'unit':unit,
                       }
        else:
            results = {'error_msg':error_msg,
                       'success':success}
        return results
    
    def as_table(self):
        result_matrix = []
        res = self._results
        if res['success']:
            A = res['A']
            p = self._p
            l = res['l']
            v = res['v']
            sv = res['sv']
            zi = res['zi']
            i = 0
            for group, observations in self.observationgroups.items():
                for obs in observations:
                    result_matrix.append([group, obs, A[i], p[i], l[i][0], v[i][0], sv[i], zi[i]*100])
                    i += 1
        else:
            result_matrix = [[self._results['error_msg']]]
        
        return result_matrix


def syncTwitter():
    from karrie_info.settings import TWITTER_USER, TWITTER_PASS
    from syncr.app.tweet import TwitterSyncr
    t = TwitterSyncr(TWITTER_USER, TWITTER_PASS)
    t.syncTwitterUserTweets(TWITTER_USER)
    t.syncFriends(TWITTER_USER)
    t.syncTwitterUserTweets(TWITTER_USER)
    
    
    
