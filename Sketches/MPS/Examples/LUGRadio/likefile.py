#!/usr/bin/env python
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
# -------------------------------------------------------------------------
"""
=================================================
LikeFile - file-like interaction with components.
=================================================



THE OUTSIDE WORLD
     +----------------------------------+
     |             LikeFile             |
     +----------------------------------+
          |                      / \
          |                       |
      InQueues                 OutQueues
          |                       |
+---------+-----------------------+---------+
|        \ /                      |         |
|    +---------+               +--------+   |
|    |  Input  |   Shutdown    | Output |   |
|    | Wrapper |-------------->|        |   |
|    | (thread)|   Message     |Wrapper |   |
|    +---------+               +--------+   |
|         |                      / \        |
|         |                       |         |
|     Inboxes                 Outboxes      |
|         |                       |         |
|        \ /                      |         |
|    +----------------------------------+   |
|    |      the wrapped component       |   |
|    +----------------------------------+   |
|                                           |
|                                           |
|  AXON SCHEDULED COMPONENTS                |
+-------------------------------------------+



Note 1: Threadsafeness of activate().

when a component is activated, it calls the method inherited from microprocess, which calls _addThread(self)
on an appropriate scheduler. _addThread calls wakeThread, which places the request on a threadsafe queue.

"""

from Axon.Scheduler import scheduler
from Axon.AxonExceptions import noSpaceInBox
from Axon.Ipc import producerFinished, shutdownMicroprocess
import Queue, threading, time, copy, Axon, warnings
queuelengths = 0


def addBox(names, boxMap, addBox):
        """Add an extra wrapped box called name, using the addBox function provided
        (either self.addInbox or self.addOutbox), and adding it to the box mapping
        which is used to coordinate message routing within component wrappers."""
        if type(names) != tuple:
            names = (names,)
        for boxname in names:
            if boxname in boxMap:
                raise ValueError, "%s %s already exists!" % (direction, boxname)
            realboxname = addBox(boxname)
            boxMap[boxname] = realboxname


class dummyComponent(Axon.Component.component):
    """A dummy component. Functionality: None. Prevents the scheduler from dying immediately."""
    def main(self):
        while True:
            self.pause()
            yield 1


class schedulerThread(threading.Thread):
    """A python thread which runs a scheduler."""
    lock = threading.Lock()
    def __init__(self,slowmo=0):
        if not schedulerThread.lock.acquire(False):
            raise "only one scheduler for now can be run!"
        self.slowmo = slowmo
        threading.Thread.__init__(self)
        self.setDaemon(True) # Die when the caller dies
    def run(self):
        dummyComponent().activate() # to keep the scheduler from exiting immediately.
        scheduler.run.runThreads(slowmo = self.slowmo)
        schedulerThread.lock.release()


class componentWrapperInput(Axon.ThreadedComponent.threadedadaptivecommscomponent):
    """A wrapper that takes a child component and waits on an event from the foreground, to signal that there is 
    queued data to be placed on the child's inboxes."""
    def __init__(self, child, extraInboxes = None):
        super(componentWrapperInput, self).__init__()
        self.child = child

        # This is a map from the name of the wrapped inbox on the child, to the
        # Queue used to convey data into it.
        self.inQueues = dict()

        # This queue is used by the foreground to tell us what queue it has sent us
        # data on, so that we do not need to check all our input queues,
        # and also so that we can block on reading it.
        self.whatInbox = Queue.Queue()
        self.isDead = threading.Event()


        # This sets up the linkages between us and our child, avoiding extra
        # box creation by connecting the "basic two" in the same way as, e.g. a pipeline.
        self.childInboxMapping = { "inbox": "outbox", "control": "signal" }
        if extraInboxes:
            addBox(extraInboxes, self.childInboxMapping, self.addOutbox)
        for childSink, parentSource in self.childInboxMapping.iteritems():
            self.inQueues[childSink] = Queue.Queue(self.queuelengths)
            self.link((self, parentSource),(self.child, childSink))

        # This outbox is used to tell the output wrapper when to shut down.
        self.deathbox = self.addOutbox(str(id(self)))

    def main(self):
        while True:
            whatInbox = self.whatInbox.get()
            if not self.pollQueue(whatInbox):
                # a False return indicates that we should shut down.
                self.isDead.set()
                # tells the foreground object that we've successfully processed a shutdown message.
                # unfortunately, whether the child honours it or not is a matter of debate.
                self.send(object, self.deathbox)
                return

    def pollQueue(self, whatInbox):
        """This method checks all the queues from the outside world, and forwards any waiting data
        to the child component. Returns False if we propogated a shutdown signal, true otherwise."""
        parentSource = self.childInboxMapping[whatInbox]
        queue = self.inQueues[whatInbox]
        while not queue.empty():
            if not self.outboxes[parentSource].isFull():
                msg = queue.get_nowait() # won't fail, we're the only one reading from the queue.
                try:
                    self.send(msg, parentSource)
                except noSpaceInBox, e:
                    raise "Box delivery failed despite box (earlier) reporting being not full. Is more than one thread directly accessing boxes?"
                if isinstance(msg, (shutdownMicroprocess, producerFinished)):
                    return False
            else:
                # if the component's inboxes are full, do something here. Preferably not succeed.
                break
        return True

class componentWrapperOutput(Axon.AdaptiveCommsComponent.AdaptiveCommsComponent):
    """A component which takes a child component and connects its outboxes to queues, which communicate
    with the LikeFile component."""
    def __init__(self, child, inputHandler, extraOutboxes = None):
        super(componentWrapperOutput, self).__init__()
        self.queuelengths = queuelengths
        self.child = child
        self.addChildren(self.child)

        # This queue maps from the name of the outbox on the child which is to be wrapped,
        # to the Queue which conveys that data to the foreground thread.
        self.outQueues = dict()

        # set up notification from the input handler to kill us when appropriate.
        # we cannot rely on shutdown messages being propogated through the child.
        self.isDead = inputHandler.isDead
        self.deathbox = self.addInbox(str(id(self)))
        self.link((inputHandler, inputHandler.deathbox), (self, self.deathbox))

        # This sets up the linkages between us and our child, avoiding extra
        # box creation by connecting the "basic two" in the same way as, e.g. a pipeline.
        self.childOutboxMapping = { "outbox": "inbox", "signal": "control" }
        if extraOutboxes:
            addBox(extraOutboxes, self.childOutboxMapping, self.addInbox)

        for childSource, parentSink in self.childOutboxMapping.iteritems():
            self.outQueues[childSource] = Queue.Queue(self.queuelengths)
            self.link((self.child, childSource),(self, parentSink))

    def main(self):
        self.child.activate()
        while True:
            self.pause()
            yield 1
            self.sendPendingOutput()
            if self.dataReady(self.deathbox):
                return


    def sendPendingOutput(self):
        """This method will take any outgoing data sent to us from a child component and stick it on a queue 
        to the outside world."""
        for childSource, parentSink in self.childOutboxMapping.iteritems():
            queue = self.outQueues[childSource]
            while self.dataReady(parentSink):
                if not queue.full():
                    msg = self.recv(parentSink)
                    # TODO - what happens when the wrapped component terminates itself? We keep on going. Not optimal.
                    queue.put_nowait(msg)
                else:
                    break
                    # permit a horrible backlog to build up inside our boxes. What could go wrong?

class LikeFile(object):
    alive = False
    """An interface to the message queues from a wrapped component, which is activated on a backgrounded scheduler."""
    def __init__(self, componenttowrap, extrainboxes = None, extraoutboxes = None):
        if schedulerThread.lock.acquire(False): 
            schedulerThread.lock.release()
            raise AttributeError, "no running scheduler found."
        try: inputComponent = componentWrapperInput(componenttowrap, extrainboxes)
        except KeyError, e:
            raise KeyError, 'component to wrap has no such inbox: %s' % e
        try: outputComponent = componentWrapperOutput(componenttowrap, inputComponent, extraoutboxes)
        except KeyError, e:
            del inputComponent
            raise KeyError, 'component to wrap has no such outbox: %s' % e
        self.inQueues = copy.copy(inputComponent.inQueues)
        self.outQueues = copy.copy(outputComponent.outQueues)
        # reaching into the component and its child like this is threadsafe since it has not been activated yet.
        self.inputComponent = inputComponent
        self.outputComponent = outputComponent


    def activate(self):
        """Activates the component on the backgrounded scheduler and permits IO."""
        if self.alive:
            return
        self.inputComponent.activate() # threadsafe, see note 1
        self.outputComponent.activate()
        self.alive = True

    def recv(self, boxname = "outbox"):
        """Performs a blocking read on the queue corresponding to the named outbox on the wrapped component.
        raises AttributeError if the LikeFile is not alive."""
        if self.alive:
            return self.outQueues[boxname].get()
        else: raise AttributeError, "shutdown was previously called, or we were never activated."
    get = recv # alias for backwards compatibility.

    def send(self, msg, boxname = "inbox"):
        """Places an object on a queue which will be directed to a named inbox on the wrapped component."""
        if self.alive:
            queue = self.inQueues[boxname]
            queue.put_nowait(msg)
            self.inputComponent.whatInbox.put_nowait(boxname)
        else: raise AttributeError, "shutdown was previously called, or we were never activated."
    put = send # alias for backwards compatibility

    def shutdown(self):
        """Sends terminatory signals to the wrapped component, and shut down the componentWrapper.
        will warn if the shutdown took too long to confirm in action."""
        if self.alive: 
            self.send(Axon.Ipc.shutdown(),               "control") # legacy support.
            self.send(Axon.Ipc.producerFinished(),       "control") # some components only honour this one
            self.send(Axon.Ipc.shutdownMicroprocess(),   "control") # should be last, this is what we honour
        else:
            raise AttributeError, "shutdown was previously called, or we were never activated."
        self.inputComponent.isDead.wait(1)
        if not self.inputComponent.isDead.isSet(): # we timed out instead of someone else setting the flag
            warnings.warn("Timed out waiting on shutdown confirmation, may not be dead.")
        self.alive = False

    def __del__(self):
        if self.alive:
            self.shutdown()


if __name__ == "__main__":
    background = schedulerThread(slowmo=0.01).start()
    time.sleep(0.1)
    from Kamaelia.Protocol.HTTP.HTTPClient import SimpleHTTPClient
    import time
    p = LikeFile(SimpleHTTPClient())
    p.activate()
    p.send("http://google.com")
    p.send("http://slashdot.org")
    p.send("http://whatismyip.org")
    google = p.recv()
    slashdot = p.recv()
    whatismyip = p.recv()
    print "google is", len(google), "bytes long, and slashdot is", len(slashdot), "bytes long. Also, our IP address is:", whatismyip