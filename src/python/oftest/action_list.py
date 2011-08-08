"""
OpenFlow action, instruction and bucket list classes
"""

from action import *
from cstruct import ofp_header
from base_list import ofp_base_list
import copy

action_object_map = {
    OFPAT_OUTPUT                        : action_output,
    OFPAT_SET_VLAN_VID                  : action_set_vlan_vid,
    OFPAT_SET_VLAN_PCP                  : action_set_vlan_pcp,
    OFPAT_SET_DL_SRC                    : action_set_dl_src,
    OFPAT_SET_DL_DST                    : action_set_dl_dst,
    OFPAT_SET_NW_SRC                    : action_set_nw_src,
    OFPAT_SET_NW_DST                    : action_set_nw_dst,
    OFPAT_SET_NW_TOS                    : action_set_nw_tos,
    OFPAT_SET_NW_ECN                    : action_set_nw_ecn,
    OFPAT_SET_TP_SRC                    : action_set_tp_src,
    OFPAT_SET_TP_DST                    : action_set_tp_dst,
    OFPAT_COPY_TTL_OUT                  : action_copy_ttl_out,
    OFPAT_COPY_TTL_IN                   : action_copy_ttl_in,
    OFPAT_SET_MPLS_LABEL                : action_set_mpls_label,
    OFPAT_SET_MPLS_TC                   : action_set_mpls_tc,
    OFPAT_SET_MPLS_TTL                  : action_set_mpls_ttl,
    OFPAT_DEC_MPLS_TTL                  : action_dec_mpls_ttl,
    OFPAT_PUSH_VLAN                     : action_push_vlan,
    OFPAT_POP_VLAN                      : action_pop_vlan,
    OFPAT_PUSH_MPLS                     : action_push_mpls,
    OFPAT_POP_MPLS                      : action_pop_mpls,
    OFPAT_SET_QUEUE                     : action_set_queue,
    OFPAT_GROUP                         : action_group,
    OFPAT_SET_NW_TTL                    : action_set_nw_ttl,
    OFPAT_DEC_NW_TTL                    : action_dec_nw_ttl,
    OFPAT_EXPERIMENTER                  : action_experimenter
}

class action_list(ofp_base_list):
    """
    Maintain a list of actions

    Data members:
    @arg actions: An array of action objects such as action_output, etc.

    Methods:
    @arg pack: Pack the structure into a string
    @arg unpack: Unpack a string to objects, with proper typing
    @arg add: Add an action to the list; you can directly access
    the action member, but add will validate that the added object 
    is an action.

    """

    def __init__(self):
        ofp_base_list.__init__(self)
        self.actions = self.items
        self.name = "action"
        self.class_list = action_class_list

    def unpack(self, binary_string, bytes=None):
        """
        Unpack a list of actions
        
        Unpack actions from a binary string, creating an array
        of objects of the appropriate type

        @param binary_string The string to be unpacked

        @param bytes The total length of the action list in bytes.  
        Ignored if decode is True.  If None and decode is false, the
        list is assumed to extend through the entire string.

        @return The remainder of binary_string that was not parsed

        """
        if bytes == None:
            bytes = len(binary_string)
        bytes_done = 0
        count = 0
        cur_string = binary_string
        while bytes_done < bytes:
            hdr = ofp_action_header()
            hdr.unpack(cur_string)
            if hdr.len < OFP_ACTION_HEADER_BYTES:
                print "ERROR: Action too short"
                break
            if not hdr.type in action_object_map.keys():
                print "WARNING: Skipping unknown action ", hdr.type, hdr.len
            else:
                self.actions.append(action_object_map[hdr.type]())
                self.actions[count].unpack(cur_string)
                count += 1
            cur_string = cur_string[hdr.len:]
            bytes_done += hdr.len
        return cur_string

