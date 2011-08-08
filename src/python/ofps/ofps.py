#!/usr/bin/env python
######################################################################
#
# All files associated with the OpenFlow Python Switch (ofps) are
# made available for public use and benefit with the expectation
# that others will use, modify and enhance the Software and contribute
# those enhancements back to the community. However, since we would
# like to make the Software available for broadest use, with as few
# restrictions as possible permission is hereby granted, free of
# charge, to any person obtaining a copy of this Software to deal in
# the Software under the copyrights without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject
# to the following conditions:
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# 
######################################################################

"""
OFPS:  OpenFlow Python Switch

This is a very simple implementation of an OpenFlow switch based on 
the structures generated for OpenFlow test.

To a large extent, we try to follow the openflow.h conventions;
one point of departure is an attempt to better isolate matching
structures, flow table entries with status and actions resulting
from a match.
"""

import sys
import logging
import signal
import copy
import struct
from threading import Thread
from optparse import OptionParser
import pdb

import oftest.cstruct as ofp
import oftest.dataplane as dataplane
import oftest.message as message
import oftest.action as action
from ctrl_if import ControllerInterface
from oftest.packet import Packet
from pipeline import FlowPipeline
import oftest.netutils as netutils
import ctrl_msg

DEFAULT_TABLE_COUNT = 4

class OFSwitchConfig(object):
    """
    Class to hold normal configuration parameters
    
       extended to do arg parsing
    """
    def __init__(self):         
        self.controller_ip = None
        self.controller_port = None
        self.n_tables = None
        self.passive_listen_port = None 
        self.port_map = {}
        self.env = {}  # Extensible array

        parser = OptionParser(version="%prog 0.1")
        parser.set_defaults(controller_ip="127.0.0.1")
        parser.set_defaults(controller_port=6633)
        parser.set_defaults(passive_connect=False)
        parser.set_defaults(n_tables=DEFAULT_TABLE_COUNT)
        parser.set_defaults(interfaces="veth0,veth2,veth4,veth6")
        parser.set_defaults(datapath_id=self.devine_datapath_id())
        parser.set_defaults(validate_flow_mods=True)
        
        parser.add_option('-i', '--interfaces', type='string',
                          help="Comma separated list of interfaces: e.g., \"veth0,veth2,veth4,veth6\"")
        parser.add_option('-c', '--controller', type="string", dest="controller_ip",
                           help="OpenFlow Controller Hostname or IP")
        parser.add_option('-p', '--port', type='int', dest="controller_port",
                           help="OpenFlow Controller Port")
        parser.add_option("-P", "--passive-connect", 
                          help="Listen on port; don't connect",
                          action="store_true")
        parser.add_option('-t', '--tables', type='int', dest="n_tables",
                          help="Number of tables to create in the pipeline")
        parser.add_option('-d', '--datapath-id', dest='datapath_id', type='long'
                          ,help="DatapathID for switch")
        self.parser = parser
    
    def devine_datapath_id(self):
        """
        Come up with a unique dpid from our environment
        """
        #@todo Query one of our interfaces to find a good dpid
        return 0xcafebabedeadbeef
    def datapath_id2str(self, dpid):
        '''
        Convert 8 byte long to "xx:xx:xx:..." string
        @TODO Move this else where
        '''
        return "0x%lx" % (dpid) 
        
        
    def parse_args(self):
        (self.options, self.args) = self.parser.parse_args()
        ### Should be a better way to do this
        self.controller_ip = self.options.controller_ip
        self.controller_port = self.options.controller_port
        self.passive_connect = self.options.passive_connect
        self.n_tables = self.options.n_tables
        for intr in self.options.interfaces.split(','):
            self.addInterface(intr)
 
    def getConfig(self, config):
        return getattr(self.options, config)

    def addInterface(self, intr):
        self.port_map[len(self.port_map) + 1] = intr
 
class OFSwitch(Thread):
    """
    Top level class for the ofps implementation
    Components:
       A set of dataplane ports in a DataPlane object
       A controller connection and ofp stack
       A flow table object
    The switch is responsible for:
       Plumbing the packets from the dataplane to the flow table
       Executing actions as specified by the output from the flow table
       Processing the controller messages
    The main thread processes dataplane packets and control packets
    """

    VERSION = "OFPS version 0.1"

    # @todo Support fail open/closed
    def __init__(self):
        """
        Constructor for base class
        """
        super(OFSwitch, self).__init__()
        self.setDaemon(True)
        self.config = OFSwitchConfig()
        self.logger = logging.getLogger("switch")
        self.groups = GroupTable()
        self.ports = {}         # hash of ports[index]=ofp.ofp_port
    def config_set(self, config):
        """
        Set the configuration for the switch.
        Contents:
            Controller IP address and port
            Fail open/closed
            Passive listener port
            Number of tables to support
        """
        self.config = config
        
    def ctrl_pkt_handler(self, cookie, msg, rawmsg):
        """
        Handle a message from the controller
        @todo Use a queue so messages can be processed in the main thread
        """
        try:
            callable = getattr(ctrl_msg, msg.__class__.__name__)
            self.logger.debug("Calling ctrl_msg.%s" % msg.__class__.__name__)
            callable(self, msg, rawmsg)
        except KeyError:
            self.logger.error("Could not execute controller fn (%s)" %
                                str(msg.__class__.__name__))
            sys.exit(1)

        return True
    
    def getConfig(self,element):
        """ 
        Return the element from the config 
        @param  element:  a string
        """
        return self.config.getConfig(element)

    def run(self):
        """
        Main execute function for running the switch
        """

        logging.basicConfig(filename="", level=logging.DEBUG)
        self.logger.info("Switch thread running")
        host = self.config.controller_ip
        if self.config.passive_connect:
            host = None
        self.controller = ControllerInterface(host=host,
                                              port=self.config.controller_port)
        self.dataplane = dataplane.DataPlane()
        self.logger.info("Dataplane started")
        self.pipeline = FlowPipeline(self, self.config.n_tables)
        self.pipeline.controller_set(self.controller)
        self.pipeline.start()
        self.logger.info("Pipeline started")
        link_status = ofp.OFPPF_1GB_FD  #@todo dynamically infer this from the interface status
        for of_port, ifname in self.config.port_map.items():          
            self.dataplane.port_add(ifname, of_port)
            port = ofp.ofp_port()
            port.port_no = of_port
            port.name = ifname
            port.max_speed = 9999999
            port.curr_speed = 9999999
            mac = netutils.get_if_hwaddr(port.name)
            self.logger.info("Added port %s (ind=%d) with mac %x:%x:%x:%x:%x:%x" % ((ifname, of_port) + mac))
            port.hw_addr = list(mac)    # stupid frickin' python; need to convert a tuple to a list
            port.config = 0
            port.state = 0 #@todo infer if link is up/down and set OFPPS_LINK_DOWN
            port.advertised = link_status
            port.supported = link_status
            port.curr = link_status
            port.peer = link_status
            self.ports[of_port]=port
        # Register to receive all controller packets
        self.controller.register("all", self.ctrl_pkt_handler, calling_obj=self)
        self.controller.start()
        self.logger.info("Controller started")

        # Process packets when they arrive
        self.logger.info("Entering packet processing loop")
        while True:
            (of_port, data, recv_time) = self.dataplane.poll(timeout=5)
            if not self.controller.isAlive():
                # @todo Implement fail open/closed
                self.logger.error("Controller dead\n")
                break
            if not self.pipeline.isAlive():
                # @todo Implement fail open/closed
                self.logger.error("Pipeline dead\n")
                break
            if data is None:
                self.logger.debug("No packet for 5 seconds\n")
                continue
            self.logger.debug("Packet len " + str(len(data)) +
                              " in on port " + str(of_port))
            packet = Packet(in_port=of_port, data=data)
            self.pipeline.apply_pipeline(self, packet)

        self.logger.error("Exiting OFSwitch thread")
        self.pipeline.kill()
        self.dataplane.kill()
        self.pipeline.join()
        self.controller.join()
    
    def __str__(self):
        str  = "OFPS:: OpenFlow Python Switch\n"
        str += "    datapath_id = %s\n" % (self.config.datapath_id2str(
                self.config.getConfig('datapath_id')))
        for key, val in self.config.port_map.iteritems():
            str += "    interface %d = %s\n" % (key, val)
        return str 
    
    def version(self):
        return OFSwitch.VERSION

class GroupTable(object):
    """
    Class to implement a group table object
    """
    def __init__(self):
        """
        Constructor for base class
        Groups is a dict indexed by group_id with values group_mod messages
        """
        self.groups = {}

    def update(self, group_mod):
        """
        Execute the group_mod operation on the table
        """
        # @todo Error checking, etc; should this be copy?
        self.groups[group_mod.group_id] = group_mod

    def group_get(self, group_id):
        if group_id in self.groups.keys():
            return self.groups[group_id]
        else:
            return None

    def group_stats_get(self, group_id):
        """
        Return an ofp_group_stats object for the group_id
        """
        return None

def sigint_handler(signum, frame):
    sys.exit()

#####
# If we're actually executing this file, then run this
if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)

    #pdb.set_trace()
    config = OFSwitchConfig()
    config.parse_args()
    threads = []

    ofps = OFSwitch()
    threads.append(ofps)

    ofps.config_set(config)
    print 'OFPS Starting...'
    ofps.run()
    print 'OFPS Exiting'
