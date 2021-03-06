#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2010 British Broadcasting Corporation and Kamaelia Contributors(1)
#
# (1) Kamaelia Contributors are listed in the AUTHORS file and at
#     http://www.kamaelia.org/AUTHORS - please extend this file,
#     not this notice.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# -------------------------------------------------------------------------

# physics code for forces between particles
#
# unbonded force acts between all non bonded particles
# bonded force acts between bonded particles

from SpatialIndexer import SpatialIndexer

from operator import sub as _sub
from operator import add as _add
from operator import mul as _mul

class SimpleLaws(object):
    """Implements a simple set of physics laws for the particle system.
       repulsion force : force proportional to 1/distance_squared 
       bonds : force proportional to extension (Hook's law)
       
       All force strengths etc. are set up to vaguely sensible values on the basis of
       the specified bond length
    """
    def __init__(self, bondLength        = 100,
                       maxRepelRadius    = None,
                       repulsionStrength = None,
                       maxBondForce      = None,
                       damp              = None,
                       dampcutoff        = None,
                       maxVelocity       = None
                 ):
        """bondlength argument is the 'master control'
              maxInteractRadius is the maximum distance repulsions are considered over
              repulsionStrength = strength of repulsion (when at bondLength distance)
              maxBondForce      = force at distance 0 or 2*bondLength (ie. bond spring constant)
              damp              = dampening (drag) 0.0 = none, 1.0 = no movement at all!
              dampcutoff        = minimum velocity below which friction stops movement all together
              maxVelocity       = maximum velocity limit
              
           maxVelocity is a fiddle factor to help you stop the system spiralling out of control
           
           damp and dampcutoff are effectively wind resistance and friction
           
           bondLengthsInteractRadius gives the physics system a way to reduce the amount of
           
           computation needed because particles are greater distances are deemed to not interact
        """
        self.bondLength = bondLength

        scale = 100.0 / self.bondLength
        
        def defaultIfNone(value, default):
            if value == None:
                return default
            else:
                return value
        
        self.maxInteractRadius          = defaultIfNone(maxRepelRadius,    200  / scale)
        self.repulsionForceAtBondLength = defaultIfNone(repulsionStrength, 3.2  / scale)
        self.maxBondForce               = defaultIfNone(maxBondForce,      20.0 / scale)
        self.damp                       = 1.0 - defaultIfNone(damp, 0.2)
        self.dampcutoff                 = defaultIfNone(dampcutoff,        0.4  / scale)
        self.maxVelocity                = defaultIfNone(maxVelocity,       32   / scale)
        
        self.bondForce         = self.maxBondForce / self.bondLength
        self.maxRepulsionForce = self.repulsionForceAtBondLength * self.bondLength**2
        
    def particleMaxInteractRadius(self, ptype):
        return self.maxInteractRadius
        
    def unbonded(self, ptype1, ptype2, dist, distSquared):
        """1/distance_squared unbonded repulsion force"""
        if distSquared < 1.0:
            return -self.maxRepulsionForce
        else:
            return -self.maxRepulsionForce / distSquared #* (self.particleRadius*self.particleRadius)

    
    def bonded(self, ptype1, ptype2, dist, distSquared):
        """proportional to extension bond force"""
        # note, its import that this retains its sign, so the direction of the force is determined
        f = self.bondForce * (dist - self.bondLength)
        if f < -self.maxBondForce:
            return -self.maxBondForce
        elif f > self.maxBondForce:
            return self.maxBondForce
        else:
            return f
    
    
    def dampening(self, ptype, velocity):
        """velocity dampening and minimal velocity (friction-like) cutoff"""
        vmag = reduce(lambda a,b:abs(a)+abs(b), velocity)
        if vmag < self.dampcutoff:
            return [0] * len(velocity) #[0 for a in velocity]
        else:
            damp = self.damp
            if damp * vmag > self.maxVelocity:
                damp = self.maxVelocity / vmag
                
            return map(_mul, velocity, [damp] * len(velocity) )
#            return [ damp * v for v in velocity ]

