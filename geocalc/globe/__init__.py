#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" 
Berechnungen auf der Kugel 
"""

from math import atan, cos, sin, tan, radians, pi, degrees

def azimuth(pA, lA, pB, lB):
    """
    Aus: Geodäsie I, Geodätische Berechnungen aud Ellipsoid und Kugel
    Kapitel 130
    
    pA, pB, lA und lB in rad
    
    return in degrees:
    - beta
    - alpha
    - alpha_
    - mu
    """
    
    a = 2.0*atan(cos((pA-pB)/2.0)/sin((pA+pB)/2.0)*1.0/tan((lB-lA)/2.0))
    b = 2.0*atan(sin((pA-pB)/2.0)/cos((pA+pB)/2.0)*1.0/tan((lB-lA)/2.0))
    
  
    beta = degrees((a-b)/2.0)
    alpha = degrees(a)-beta
    alpha_ = 180.0-beta
    mu = alpha_ - alpha #Meridiankonvergenz
    
    return locals()

def distance(alpha, beta, pA, pB, R=6378815.904):
    """
    alpha, beta, pA, pB aus azimuth() in radiant
    
    Beispiel: distance(alpha=radians(azi['alpha']),
             beta=radians(azi['beta']),
             pA=azi['pA'], 
             pB=azi['pB'])
    
    """
    c = atan(cos((alpha + beta)/2.0)/cos((alpha-beta)/2.0)*1.0/tan((pA+pB)/2.0))*2.0
    s = c*R*pi/radians(180)
    
    return locals()
