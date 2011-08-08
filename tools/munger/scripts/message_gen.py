#!/usr/bin/env python
#
# This python script generates wrapper functions for OpenFlow messages
#
# See the doc string below for more info
#

# To do:
#    Default type values for messages
#    Generate all message objects
#    Action list objects?
#    Autogen lengths when possible
#    Dictionaries for enum strings
#    Resolve sub struct initializers (see ofp_flow_mod)


"""
Generate wrapper classes for OpenFlow messages

(C) Copyright Stanford University
Date February 2010
Created by dtalayco

Attempting to follow http://www.python.org/dev/peps/pep-0008/
The main exception is that our class names do not use CamelCase
so as to more closely match the original C code names.

This file is meant to generate a file of_wrapper.py which imports
the base classes generated form automatic processing of openflow.h
and produces wrapper classes for each OpenFlow message type.

This file will normally be included in of_message.py which provides
additional hand-generated work.

There are two types of structures/classes here: base components and
message classes.

Base components are the base data classes which are fixed
length structures including:
    ofp_header
    Each ofp_action structure
    ofp_port
    The array elements of all the stats reply messages
The base components are to be imported from a file of_header.py.

Message classes define a complete message on the wire.  These are
comprised of possibly variable length lists of possibly variably
typed objects from the base component list above.

Each OpenFlow message has a header and zero or more fixed length
members (the "core members" of the class) followed by zero or more
variable length lists.

The wrapper classes should live in their own name space, probably
of_message.  Automatically generated base component and skeletons for
the message classes are assumed generated and the wrapper classes
will inherit from those.

Every message class must implement pack and unpack functions to
convert between the class and a string representing what goes on the
wire.

For unpacking, the low level (base-component) classes must implement
their own unpack functions.  A single top level unpack function
will do the parsing and call the lower layer unpack functions as
appropriate.

Every base and message class should implement a show function to
(recursively) display the contents of the object.

Certain OpenFlow message types are further subclassed.  These include
stats_request, stats_reply and error.

"""

# Don't generate header object in messages
# Map each message to a body that doesn't include the header
# The body has does not include variable length info at the end

import re
import string
import sys
sys.path.append("../../src/python/oftest")
from cstruct import *
from class_maps import class_to_members_map

message_top_matter = """
# Python OpenFlow message wrapper classes

from cstruct import *
from action_list import action_list
from instruction_list import instruction_list
from bucket_list import bucket_list
from error import *

# Define templates for documentation
class ofp_template_msg(object):
    \"""
    Sample base class for template_msg; normally auto generated
    This class should live in the of_header name space and provides the
    base class for this type of message.  It will be wrapped for the
    high level API.

    \"""
    def __init__(self):
        \"""
        Constructor for base class

        \"""
        self.header = ofp_header()
        # Additional base data members declared here

    # Normally will define pack, unpack, __len__ functions

class template_msg(ofp_template_msg):
    \"""
    Sample class wrapper for template_msg
    This class should live in the of_message name space and provides the
    high level API for an OpenFlow message object.  These objects must
    implement the functions indicated in this template.

    \"""
    def __init__(self):
        \"""
        Constructor
        Must set the header type value appropriately for the message

        \"""

        ##@var header
        # OpenFlow message header: length, version, xid, type
        ofp_template_msg.__init__(self)
        self.header = ofp_header()
        # For a real message, will be set to an integer
        self.header.type = "TEMPLATE_MSG_VALUE"
    def pack(self):
        \"""
        Pack object into string

        @return The packed string which can go on the wire

        \"""
        pass
    def unpack(self, binary_string):
        \"""
        Unpack object from a binary string

        @param binary_string The wire protocol byte string holding the object
        represented as an array of bytes.

        @return Typically returns the remainder of binary_string that
        was not parsed.  May give a warning if that string is non-empty

        \"""
        pass
    def __len__(self):
        \"""
        Return the length of this object once packed into a string

        @return An integer representing the number bytes in the packed
        string.

        \"""
        pass
    def show(self, prefix=''):
        \"""
        Generate a string (with multiple lines) describing the contents
        of the object in a readable manner

        @param prefix Pre-pended at the beginning of each line.

        \"""
        pass
    def __eq__(self, other):
        \"""
        Return True if self and other hold the same data

        @param other Other object in comparison

        \"""
        pass
    def __ne__(self, other):
        \"""
        Return True if self and other do not hold the same data

        @param other Other object in comparison

        \"""
        pass
"""

# Dictionary mapping wrapped classes to the auto-generated structure
# underlieing the class (body only, not header or var-length data)
message_class_map = {
    "hello"                         : "ofp_header",
    "error"                         : "ofp_error_msg",
    "echo_request"                  : "ofp_header",
    "echo_reply"                    : "ofp_header",
    "experimenter"                  : "ofp_experimenter_header",
    "features_request"              : "ofp_header",
    "features_reply"                : "ofp_switch_features",
    "get_config_request"            : "ofp_header",
    "get_config_reply"              : "ofp_switch_config",
    "set_config"                    : "ofp_switch_config",
    "packet_in"                     : "ofp_packet_in",
    "flow_removed"                  : "ofp_flow_removed",
    "port_status"                   : "ofp_port_status",
    "packet_out"                    : "ofp_packet_out",
    "flow_mod"                      : "ofp_flow_mod",
    "group_mod"                     : "ofp_group_mod",
    "port_mod"                      : "ofp_port_mod",
    "table_mod"                     : "ofp_table_mod",
    "stats_request"                 : "ofp_stats_request",
    "stats_reply"                   : "ofp_stats_reply",
    "barrier_request"               : "ofp_header",
    "barrier_reply"                 : "ofp_header",
    "queue_get_config_request"      : "ofp_queue_get_config_request",
    "queue_get_config_reply"        : "ofp_queue_get_config_reply"
}

# These messages have a string member at the end of the data
string_members = [
    "hello",
    "error",
    "echo_request",
    "echo_reply",
    "experimenter",
    "packet_in",
    "packet_out"
]

# These messages have a list (with the given name) in the data,
# after the core members; the type is given for validation
list_members = {
    "features_reply"                : ('ports', None),
    "packet_out"                    : ('actions', 'action_list'),
    "flow_mod"                      : ('instructions', 'instruction_list'),
    "group_mod"                     : ('buckets', 'bucket_list'),
    "queue_get_config_reply"        : ('queues', None)
}

_ind = "    "

def _p1(s): print _ind + s
def _p2(s): print _ind * 2 + s
def _p3(s): print _ind * 3 + s
def _p4(s): print _ind * 4 + s

# Okay, this gets kind of ugly:
# There are three variables:  
# has_core_members:  If parent class is not ofp_header, has inheritance
# has_list: Whether class has trailing array or class
# has_string: Whether class has trailing string

def gen_message_wrapper(msg):
    """
    Generate a wrapper for the given message based on above info
    @param msg String identifying the message name for the class
    """

    msg_name = "OFPT_" + msg.upper()
    parent = message_class_map[msg]

    has_list = False    # Has trailing list
    has_core_members = False
    has_string = False  # Has trailing string
    if parent != 'ofp_header':
        has_core_members = True
    if msg in list_members.keys():
        (list_var, list_type) = list_members[msg]
        has_list = True
    if msg in string_members:
        has_string = True

    if has_core_members:
        print "class " + msg + "(" + parent + "):"
    else:
        print "class " + msg + "(object):"
    _p1('"""')
    _p1("Wrapper class for " + msg)
    print
    _p1("OpenFlow message header: length, version, xid, type")
    _p1("@arg length: The total length of the message")
    _p1("@arg version: The OpenFlow version (" + str(OFP_VERSION) + ")")
    _p1("@arg xid: The transaction ID")
    _p1("@arg type: The message type (" + msg_name + "=" + 
        str(eval(msg_name)) + ")")
    print
    if has_core_members and parent in class_to_members_map.keys():
        _p1("Data members inherited from " + parent + ":")
        for var in class_to_members_map[parent]:
            _p1("@arg " + var)
    if has_list:
        if list_type == None:
            _p1("@arg " + list_var + ": Variable length array of TBD")
        else:
            _p1("@arg " + list_var + ": Object of type " + list_type);
    if has_string:
        _p1("@arg data: Binary string following message members")
    print
    _p1('"""')

    print
    _p1("def __init__(self):")
    if has_core_members:
        _p2(parent + ".__init__(self)")
    _p2("self.header = ofp_header()")
    _p2("self.header.type = " + msg_name)
    if has_list:
        if list_type == None:
            _p2('self.' + list_var + ' = []')
        else:
            _p2('self.' + list_var + ' = ' + list_type + '()')
    if has_string:
        _p2('self.data = ""')

    print """

    def pack(self):
        \"""
        Pack object into string

        @return The packed string which can go on the wire

        \"""
        self.header.length = len(self)
        packed = self.header.pack()
"""

    # Have to special case the action length calculation for pkt out
    if msg == 'packet_out':
        _p2('self.actions_len = len(self.actions)')
    if has_core_members:
        _p2("packed += " + parent + ".pack(self)")
    if has_list:
        if list_type == None:
            _p2('for obj in self.' + list_var + ':')
            _p3('packed += obj.pack()')
        else:
            _p2('packed += self.' + list_var + '.pack()')
    if has_string:
        _p2('packed += self.data')
    _p2("return packed")

    print """
    def unpack(self, binary_string):
        \"""
        Unpack object from a binary string

        @param binary_string The wire protocol byte string holding the object
        represented as an array of bytes.
        @return The remainder of binary_string that was not parsed.

        \"""
        binary_string = self.header.unpack(binary_string)
"""
    if has_core_members:
        _p2("binary_string = " + parent + ".unpack(self, binary_string)")
    if has_list:
        if msg == "features_reply":  # Special case port parsing
            # For now, cheat and assume the rest of the message is port list
            _p2("while len(binary_string) >= OFP_PORT_BYTES:")
            _p3("new_port = ofp_port()")
            _p3("binary_string = new_port.unpack(binary_string)")
            _p3("self.ports.append(new_port)")
        elif list_type == None:
            _p2("for obj in self." + list_var + ":")
            _p3("binary_string = obj.unpack(binary_string)")
        elif msg == "packet_out":  # Special case this
            _p2('binary_string = self.actions.unpack(' + 
                'binary_string, bytes=self.actions_len)')
        elif msg == "flow_mod":  # Special case this
            _p2("ai_len = self.header.length - (OFP_FLOW_MOD_BYTES + " + 
                "OFP_HEADER_BYTES)")
            _p2("binary_string = self.instructions.unpack(binary_string, " +
                "bytes=ai_len)")
        else:
            _p2("binary_string = self." + list_var + ".unpack(binary_string)")
    if has_string:
        _p2("self.data = binary_string")
        _p2("binary_string = ''")
    else:
        _p2("# Fixme: If no self.data, add check for data remaining")
    _p2("return binary_string")

    print """
    def __len__(self):
        \"""
        Return the length of this object once packed into a string

        @return An integer representing the number bytes in the packed
        string.

        \"""
        length = OFP_HEADER_BYTES
"""
    if has_core_members:
        _p2("length += " + parent + ".__len__(self)")
    if has_list:
        if list_type == None:
            _p2("for obj in self." + list_var + ":")
            _p3("length += len(obj)")
        else:
            _p2("length += len(self." + list_var + ")")
    if has_string:
        _p2("length += len(self.data)")
    _p2("return length")

    print """
    def show(self, prefix=''):
        \"""
        Generate a string (with multiple lines) describing the contents
        of the object in a readable manner

        @param prefix Pre-pended at the beginning of each line.

        \"""
"""
    _p2("outstr = prefix + '" + msg + " (" + msg_name + ")\\n'")
    _p2("prefix += '  '")
    _p2("outstr += prefix + 'ofp header\\n'")
    _p2("outstr += self.header.show(prefix + '  ')")
    if has_core_members:
        _p2("outstr += " + parent + ".show(self, prefix)")
    if has_list:
        if list_type == None:
            _p2('outstr += prefix + "Array ' + list_var + '\\n"')
            _p2('for obj in self.' + list_var +':')
            _p3("outstr += obj.show(prefix + '  ')")
        else:
            _p2('outstr += prefix + "List ' + list_var + '\\n"')
            _p2('outstr += self.' + list_var + ".show(prefix + '  ')")
    if has_string:
        _p2("outstr += prefix + 'data is of length ' + str(len(self.data)) + '\\n'")
        _p2("##@todo Fix this circular reference")
        _p2("# if len(self.data) > 0:")
        _p3("# obj = of_message_parse(self.data)")
        _p3("# if obj != None:")
        _p4("# outstr += obj.show(prefix)")
        _p3("# else:")
        _p4('# outstr += prefix + "Unable to parse data\\n"')
    _p2('return outstr')

    print """
    def __eq__(self, other):
        \"""
        Return True if self and other hold the same data

        @param other Other object in comparison

        \"""
        if type(self) != type(other): return False
        if not self.header.__eq__(other.header): return False
"""
    if has_core_members:
        _p2("if not " + parent + ".__eq__(self, other): return False")
    if has_string:
        _p2("if self.data != other.data: return False")
    if has_list:
        _p2("if self." + list_var + " != other." + list_var + ": return False")
    _p2("return True")

    print """
    def __ne__(self, other):
        \"""
        Return True if self and other do not hold the same data

        @param other Other object in comparison

        \"""
        return not self.__eq__(other)
    """


################################################################
#
# Stats request subclasses
# description_request, flow, aggregate, table, port, experimenter
#
################################################################

# table and desc stats requests are special with empty body
extra_ofp_stats_req_defs = """
# Stats request bodies for desc and table stats are not defined in the
# OpenFlow header;  We define them here.  They are empty classes, really

class ofp_desc_stats_request(object):
    \"""
    Forced definition of ofp_desc_stats_request (empty class)
    \"""
    def __init__(self):
        pass
    def pack(self, assertstruct=True):
        return ""
    def unpack(self, binary_string):
        return binary_string
    def __len__(self):
        return 0
    def show(self, prefix=''):
        return prefix + "ofp_desc_stats_request (empty)\\n"
    def __eq__(self, other):
        return type(self) == type(other)
    def __ne__(self, other):
        return type(self) != type(other)

OFP_DESC_STATS_REQUEST_BYTES = 0

class ofp_table_stats_request(object):
    \"""
    Forced definition of ofp_table_stats_request (empty class)
    \"""
    def __init__(self):
        pass
    def pack(self, assertstruct=True):
        return ""
    def unpack(self, binary_string):
        return binary_string
    def __len__(self):
        return 0
    def show(self, prefix=''):
        return prefix + "ofp_table_stats_request (empty)\\n"
    def __eq__(self, other):
        return type(self) == type(other)
    def __ne__(self, other):
        return type(self) != type(other)

OFP_TABLE_STATS_REQUEST_BYTES = 0

class ofp_group_desc_stats_request(object):
    \"""
    Forced definition of ofp_group_desc_stats_request (empty class)
    \"""
    def __init__(self):
        pass
    def pack(self, assertstruct=True):
        return ""
    def unpack(self, binary_string):
        return binary_string
    def __len__(self):
        return 0
    def show(self, prefix=''):
        return prefix + "ofp_group_desc_stats_request (empty)\\n"
    def __eq__(self, other):
        return type(self) == type(other)
    def __ne__(self, other):
        return type(self) != type(other)

OFP_GROUP_DESC_STATS_REQUEST_BYTES = 0

"""

stats_request_template = """
class --TYPE--_stats_request(ofp_stats_request, ofp_--TYPE--_stats_request):
    \"""
    Wrapper class for --TYPE-- stats request message
    \"""
    def __init__(self):
        self.header = ofp_header()
        ofp_stats_request.__init__(self)
        ofp_--TYPE--_stats_request.__init__(self)
        self.header.type = OFPT_STATS_REQUEST
        self.type = --STATS_NAME--

    def pack(self, assertstruct=True):
        self.header.length = len(self)
        packed = self.header.pack()
        packed += ofp_stats_request.pack(self)
        packed += ofp_--TYPE--_stats_request.pack(self)
        return packed

    def unpack(self, binary_string):
        binary_string = self.header.unpack(binary_string)
        binary_string = ofp_stats_request.unpack(self, binary_string)
        binary_string = ofp_--TYPE--_stats_request.unpack(self, binary_string)
        if len(binary_string) != 0:
            print "ERROR unpacking --TYPE--: extra data"
        return binary_string

    def __len__(self):
        return len(self.header) + OFP_STATS_REQUEST_BYTES + \\
               OFP_--TYPE_UPPER--_STATS_REQUEST_BYTES

    def show(self, prefix=''):
        outstr = prefix + "--TYPE--_stats_request\\n"
        outstr += prefix + "ofp header:\\n"
        outstr += self.header.show(prefix + '  ')
        outstr += ofp_stats_request.show(self)
        outstr += ofp_--TYPE--_stats_request.show(self)
        return outstr

    def __eq__(self, other):
        if type(self) != type(other): return False
        return (self.header == other.header and
                ofp_stats_request.__eq__(self, other) and
                ofp_--TYPE--_stats_request.__eq__(self, other))

    def __ne__(self, other): return not self.__eq__(other)
"""

################################################################
#
# Stats replies always have an array at the end.
# For aggregate and desc, these arrays are always of length 1
# This array is always called stats
#
################################################################


# Template for objects stats reply messages
stats_reply_template = """
class --TYPE--_stats_reply(ofp_stats_reply):
    \"""
    Wrapper class for --TYPE-- stats reply
    \"""
    def __init__(self):
        self.header = ofp_header()
        ofp_stats_reply.__init__(self)
        self.header.type = OFPT_STATS_REPLY
        self.type = --STATS_NAME--
        # stats: Array of type --TYPE--_stats_entry
        self.stats = []

    def pack(self, assertstruct=True):
        self.header.length = len(self)
        packed = self.header.pack()
        packed += ofp_stats_reply.pack(self)
        for obj in self.stats:
            packed += obj.pack()
        return packed

    def unpack(self, binary_string):
        binary_string = self.header.unpack(binary_string)
        binary_string = ofp_stats_reply.unpack(self, binary_string)
        dummy = --TYPE--_stats_entry()
        while len(binary_string) >= len(dummy):
            obj = --TYPE--_stats_entry()
            binary_string = obj.unpack(binary_string)
            self.stats.append(obj)
        if len(binary_string) != 0:
            print "ERROR unpacking --TYPE-- stats string: extra bytes"
        return binary_string

    def __len__(self):
        length = len(self.header) + OFP_STATS_REPLY_BYTES
        for obj in self.stats:
            length += len(obj)
        return length

    def show(self, prefix=''):
        outstr = prefix + "--TYPE--_stats_reply\\n"
        outstr += prefix + "ofp header:\\n"
        outstr += self.header.show(prefix + '  ')
        outstr += ofp_stats_reply.show(self)
        outstr += prefix + "Stats array of length " + str(len(self.stats)) + '\\n'
        for obj in self.stats:
            outstr += obj.show()
        return outstr

    def __eq__(self, other):
        if type(self) != type(other): return False
        return (self.header == other.header and
                ofp_stats_reply.__eq__(self, other) and
                self.stats == other.stats)

    def __ne__(self, other): return not self.__eq__(other)
"""

#
# To address variations in stats reply bodies, the following
# "_entry" classes are defined for each element in the reply
#

extra_stats_entry_defs = """
# Stats entries define the content of one element in a stats
# reply for the indicated type; define _entry for consistency

aggregate_stats_entry = ofp_aggregate_stats_reply
desc_stats_entry = ofp_desc_stats
port_stats_entry = ofp_port_stats
queue_stats_entry = ofp_queue_stats
table_stats_entry = ofp_table_stats
group_stats_entry = ofp_group_stats
group_desc_stats_entry = ofp_group_desc_stats
"""

# Special case flow_stats to handle actions_list

flow_stats_entry_def = """
#
# Flow stats entry contains an action list of variable length, so
# it is done by hand
#

class flow_stats_entry(ofp_flow_stats):
    \"""
    Special case flow stats entry to handle action list object
    \"""
    def __init__(self):
        ofp_flow_stats.__init__(self)
        self.instructions = instruction_list()

    def pack(self, assertstruct=True):
        self.length = len(self)
        packed = ofp_flow_stats.pack(self, assertstruct)
        packed += self.instructions.pack()
        if len(packed) != self.length:
            print("ERROR: flow_stats_entry pack length not equal",
                  self.length, len(packed))
        return packed

    def unpack(self, binary_string):
        binary_string = ofp_flow_stats.unpack(self, binary_string)
        ai_len = self.length - OFP_FLOW_STATS_BYTES
        if ai_len < 0:
            print("ERROR: flow_stats_entry unpack length too small",
                  self.length)
        binary_string = self.instructions.unpack(binary_string, bytes=ai_len)
        return binary_string

    def __len__(self):
        return OFP_FLOW_STATS_BYTES + len(self.instructions)

    def show(self, prefix=''):
        outstr = prefix + "flow_stats_entry\\n"
        outstr += ofp_flow_stats.show(self, prefix + '  ')
        outstr += self.instructions.show(prefix + '  ')
        return outstr

    def __eq__(self, other):
        if type(self) != type(other): return False
        return (ofp_flow_stats.__eq__(self, other) and 
                self.instructions == other.instructions)

    def __ne__(self, other): return not self.__eq__(other)
"""

stats_types = [
    'aggregate',
    'desc',
    'flow',
    'port',
    'queue',
    'group',
    'group_desc',
    'table']

if __name__ == '__main__':

    print message_top_matter

    print """
################################################################
#
# OpenFlow Message Definitions
#
################################################################
"""

    msg_types = message_class_map.keys()
    msg_types.sort()

    for t in msg_types:
        gen_message_wrapper(t)
        print

    print """
################################################################
#
# Stats request and reply subclass definitions
#
################################################################
"""

    print extra_ofp_stats_req_defs
    print extra_stats_entry_defs
    print flow_stats_entry_def

    # Generate stats request and reply subclasses
    for t in stats_types:
        stats_name = "OFPST_" + t.upper()
        to_print = re.sub('--TYPE--', t, stats_request_template)
        to_print = re.sub('--TYPE_UPPER--', t.upper(), to_print)
        to_print = re.sub('--STATS_NAME--', stats_name, to_print)
        print to_print
        to_print = re.sub('--TYPE--', t, stats_reply_template)
        to_print = re.sub('--STATS_NAME--', stats_name, to_print)
        print to_print

    # Lastly, generate a tuple containing all the message classes
    print """
# @todo Add buckets to group and group_desc stats obejcts"
message_type_list = (
    aggregate_stats_reply,
    aggregate_stats_request,
    bad_action_error_msg,
    bad_request_error_msg,
    barrier_reply,
    barrier_request,
    desc_stats_reply,
    desc_stats_request,
    echo_reply,
    echo_request,
    error,
    experimenter,
    features_reply,
    features_request,
    flow_mod,
    flow_mod_failed_error_msg,
    flow_removed,
    flow_stats_reply,
    flow_stats_request,
    get_config_reply,
    get_config_request,
    group_desc_stats_request,
    group_desc_stats_reply,
    group_stats_request,
    group_stats_reply,
    group_mod,
    group_mod_failed_error_msg,
    hello,
    hello_failed_error_msg,
    packet_in,
    packet_out,
    port_mod,
    port_mod_failed_error_msg,
    port_stats_reply,
    port_stats_request,
    port_status,
    queue_get_config_reply,
    queue_get_config_request,
    queue_op_failed_error_msg,
    queue_stats_reply,
    queue_stats_request,
    set_config,
    switch_config_failed_error_msg,
    table_mod,
    table_mod_failed_error_msg,
    table_stats_reply,
    table_stats_request,
    )
"""

#
# OFP match variants
#  ICMP 0x801 (?) ==> icmp_type/code replace tp_src/dst
#


