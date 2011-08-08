#!/usr/bin/env python
#
# This python script generates error subclasses
#

import re
import sys
sys.path.append("../../src/python/oftest")
from cstruct import *
from class_maps import class_to_members_map

print """
# Python OpenFlow error wrapper classes

from cstruct import *

"""

################################################################
#
# Error message subclasses
#
################################################################

# Template for error subclasses

template = """
class --TYPE--_error_msg(ofp_error_msg):
    \"""
    Wrapper class for --TYPE-- error message class

    Data members inherited from ofp_error_msg:
    @arg type
    @arg code
    @arg data: Binary string following message members
    
    \"""
    def __init__(self):
        ofp_error_msg.__init__(self)
        self.header = ofp_header()
        self.header.type = OFPT_ERROR
        self.type = --ERROR_NAME--
        self.data = ""

    def pack(self, assertstruct=True):
        self.header.length = self.__len__()
        packed = self.header.pack()
        packed += ofp_error_msg.pack(self)
        packed += self.data
        return packed

    def unpack(self, binary_string):
        binary_string = self.header.unpack(binary_string)
        binary_string = ofp_error_msg.unpack(self, binary_string)
        self.data = binary_string
        return ""

    def __len__(self):
        return OFP_HEADER_BYTES + OFP_ERROR_MSG_BYTES + len(self.data)

    def show(self, prefix=''):
        outstr = prefix + "--TYPE--_error_msg\\m"
        outstr += self.header.show(prefix + '  ')
        outstr += ofp_error_msg.show(self, prefix + '  ')
        outstr += prefix + "data is of length " + str(len(self.data)) + '\\n'
        ##@todo Consider trying to parse the string
        return outstr

    def __eq__(self, other):
        if type(self) != type(other): return False
        return (self.header == other.header and
                ofp_error_msg.__eq__(self, other) and
                self.data == other.data)

    def __ne__(self, other): return not self.__eq__(other)
"""

error_types = [
    'hello_failed',
    'bad_request',
    'bad_action',
    'bad_instruction',
    'bad_match',
    'flow_mod_failed',
    'group_mod_failed',
    'port_mod_failed',
    'table_mod_failed',
    'queue_op_failed',
    'switch_config_failed']

for t in error_types:
    error_name = "OFPET_" + t.upper()
    to_print = re.sub('--TYPE--', t, template)
    to_print = re.sub('--ERROR_NAME--', error_name, to_print)
    print to_print
