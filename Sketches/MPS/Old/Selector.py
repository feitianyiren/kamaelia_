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


import Axon
from Axon.Ipc import shutdown
import select
from Kamaelia.KamaeliaIPC import newReader, removeReader, newWriter, removeWriter, newExceptional, removeExceptional
import Axon.CoordinatingAssistantTracker as cat

READERS,WRITERS, EXCEPTIONALS = 0, 1, 2
FAILHARD = False
class Selector(Axon.AdaptiveCommsComponent.AdaptiveCommsComponent): # SmokeTests_Selector.test_SmokeTest
    Inboxes = {
         "control" : "Recieving a Axon.Ipc.shutdown() message here causes shutdown",
         "inbox" : "Not used at present",
         "notify" : "Used to be notified about things to select"
    }
    def removeLinks(self, selectable, meta, selectables):
        replyService, outbox, Linkage = meta[selectable]
        self.postoffice.deregisterlinkage(thelinkage=Linkage)
        selectables.remove(selectable)
        self.deleteOutbox(outbox)
        del meta[selectable]
        Linkage = None

    def addLinks(self, replyService, selectable, meta, selectables, boxBase):
        outbox = self.addOutbox(boxBase)
        L = self.link((self, outbox), replyService)
        meta[selectable] = replyService, outbox, L
        selectables.append(selectable)
        return L

    def handleNotify(self, meta, readers,writers, exceptionals):
        if self.dataReady("notify"):
            message = self.recv("notify")
            if isinstance(message, newReader):
                replyService, selectable = message.object
                L = self.addLinks(replyService, selectable, meta[READERS], readers, "readerNotify")
                L.showtransit = 0

            if isinstance(message, newWriter):
                replyService, selectable = message.object
                L = self.addLinks(replyService, selectable, meta[WRITERS], writers, "writerNotify")
                L.showtransit = 0

            if isinstance(message, newExceptional):
                replyService, selectable = message.object
                self.addLinks(replyService, selectable, meta[EXCEPTIONALS], exceptionals, "exceptionalNotify")

            if isinstance(message, removeReader):
                selectable = message.object
                self.removeLinks(selectable, meta[READERS], readers)

            if isinstance(message, removeWriter):
                selectable = message.object
                self.removeLinks(selectable, meta[WRITERS], writers)

            if isinstance(message, removeExceptional):
                selectable = message.object
                self.removeLinks(selectable, meta[EXCEPTIONALS], exceptionals)

    def main(self):
        readers,writers, exceptionals = [],[], []
        meta = [ {}, {}, {} ]
        self.pause()
        while 1: # SmokeTests_Selector.test_RunsForever
            if self.dataReady("control"):
                message = self.recv("control")
                if isinstance(message,shutdown):
                   return

            self.handleNotify(meta, readers,writers, exceptionals)
            if len(readers) + len(writers) + len(exceptionals) > 0:
                try:
#                    if len(writers)>0:
#                        print;print;print;print;print ",,,,",writers[0].getsockname(),",,,,"
#                        print;print;print;print;
#                    else:
#                        print "Bugger"
                    read_write_except = select.select(readers, writers, exceptionals,0)
                except ValueError, e:
                    print dir(e), e.args
                    if FAILHARD:
                        raise e

                for i in xrange(3):
                    for selectable in read_write_except[i]:
                        try:
                            replyService, outbox, linkage = meta[i][selectable]
                            self.send(selectable, outbox)
                            replyService, outbox, linkage = None, None, None
                        except KeyError:
                            print "Error!"
                            pass
            elif not self.anyReady():
                self.pause()
            yield 1

    def setSelectorServices(selector, tracker = None):
        """\
        Sets the given selector as the service for the selected tracker or the
        default one.

        (static method)
        """
        if not tracker:
            tracker = cat.coordinatingassistanttracker.getcat()
        tracker.registerService("selector", selector, "notify")
        tracker.registerService("selectorshutdown", selector, "control")
    setSelectorServices = staticmethod(setSelectorServices)

    def getSelectorServices(tracker=None): # STATIC METHOD
      """\
      Returns any live selector registered with the specified (or default) tracker,
      or creates one for the system to use.

      (static method)
      """
      if tracker is None:
         tracker = cat.coordinatingassistanttracker.getcat()
      try:
         service = tracker.retrieveService("selector")
         shutdownservice = tracker.retrieveService("selectorshutdown")
         return service, shutdownservice, None
      except KeyError:
         selector = Selector()
         Selector.setSelectorServices(selector, tracker)
         service=(selector,"notify")
         shutdownservice=(selector,"control")
         return service, shutdownservice, selector
    getSelectorServices = staticmethod(getSelectorServices)


__kamaelia_components__  = ( Selector, )
