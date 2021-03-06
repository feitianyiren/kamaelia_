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
import pygame

class Drawing:
    """
    Code adapted slightly from MagnaDoodle.py and moved into separate module
    Methods added back to ShardMagnaDoodle using shard wrapper function at runtime
    """
    
    def displaySetup(self, bgcolour, fgcolour, margin, size, transparent, position):
        self.backgroundColour = bgcolour
        self.foregroundColour = fgcolour
        self.margin = margin
        self.oldpos = None
        self.drawing = False
        
        self.size = size
        self.innerRect = pygame.Rect(10, 10, self.size[0]-20, self.size[1]-20)
        
        if transparent:
            transparency = bgcolour
        else:
            transparency = None
        
        self.disprequest = {"DISPLAYREQUEST" : True,
                                        "callback" : (self,"callback"),
                                        "events" : (self, "inbox"),
                                        "size": self.size,
                                        "transparency" : transparency}
        if not position is None:
            self.disprequest["position"] = position
            
    def drawBG(self):
        self.display.fill( (255,0,0) )
        self.display.fill( self.backgroundColour, self.innerRect )
      
    def blitToSurface(self):
        self.send({"REDRAW":True, "surface":self.display}, "display_signal")
