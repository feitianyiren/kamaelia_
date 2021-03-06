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

import nxt.locator
import axon
from nxt.sensor import *

class KamaeliaNXT(Axon.Component.component):
   Inboxes = {"rmotor" : "control signals for the right motor",
              "lmotor" : "control signals for the left motor",
              }
   Outboxes = {"outbox" : "data collected from sensors",
              }
   def __init__(self, sock):
      self.rmotor = Motor(sock, PORT_B)
      self.lmotor = Motor(sock, PORT_C)
      self.light = LightSensor(b, PORT_3)
      self.sock = sock
      
   def stop(self):
      self.send(0, "rmotor")
      self.send(0, "lmotor")
      
   def main(self):
      while 1:
         self.send(light.get_sample()), "outbox")
         if self.dataReady("rmotor"):
            rmotor.power = self.recv("rmotor") # Right motor control
            rmotor.mode = MODE_MOTOR_ON
            rmotor.run_state = RUN_STATE_RUNNING
         if self.dataReady("lmotor"):
            lmotor.power = self.recv("lmotor") # Left motor control
            lmotor.mode = MODE_MOTOR_ON
            lmotor.run_state = RUN_STATE_RUNNING
         if TouchSensor(b, PORT_1).get_sample(): 
             self.stop()
             break
         yield 1
