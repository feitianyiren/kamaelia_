#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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
#
# In order to work, this example requires IPython, and has been tested with
# IPython 0.6.13
#
# This in all likelihood may form the basis of an "Introspecting Scheduler"
# It's already clear that a number of knock on changes in the scheduler are
# necessary for this system to have the maximum benefit.
#
#
"""
The script following shows the basics of how to run IPython as a foreground
thread and Axon as a background thread - allowing live introspection of the
running system.

Example interaction:
michaelsparks:~> ./axonshell.py
In [1]: Axon
Out[1]: <module 'Axon' from
'/usr/lib/python2.3/site-packages/Axon/__init__.pyc'>

In [2]: Axon.Scheduler.scheduler.run
Out[2]: <Axon.Scheduler.scheduler object at 0x403e3eac>

In [3]: Axon.Scheduler.scheduler.run.threads
Out[3]: 
[<Axon.Postman.postman object at 0x40447ccc>,
 <__main__.Echo object at 0x40441a2c>]

In [4]: Axon.Scheduler.scheduler.run.threads
Out[4]: [<Axon.Postman.postman object at 0x40447ccc>]

(Note that these two show the run queue updating in the background)

In [5]: echo._deliver("Hello World")

In [6]: Echo received:  Hello World

In [6]: 
"""

import threading
import time
import Axon
from Axon.Scheduler import scheduler
from Axon.Component import component

class Echo(component):
   def main(self):
      tlast = time.time()
      while 1:
         if self.dataReady("inbox"):
             data = self.recv("inbox")
             print "Echo received: ", data
         self.pause()
         yield 1
   def _activityCreator(self):
      return True

class schedulerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True) # Die when the interactive shell dies
    def run(self):
       a=Echo()
       a.activate()
       scheduler.run.runThreads()


if __name__ == "__main__":
   import Axon
   foo = schedulerThread()
   foo.start()
   try:
       __IPYTHON__
   except NameError:
       nested = 0
       args = ['']
   else:
       print "Running nested copies of IPython."
       print "The prompts for the nested copy have been modified"
       nested = 1
       # what the embedded instance will see as sys.argv:
       args = ['-pi1','In <\\#>:','-pi2', '   .\\D.:','-po','Out<\\#>:','-nosep']
   from IPython.Shell import IPShellEmbed

   ipshell = IPShellEmbed(args,
                          banner = 'Starting Axon Interactive Shell',
                          exit_msg = '')

   ipshell('***Called from top level. '
           'Hit Ctrl-D to exit interpreter and continue program.')

