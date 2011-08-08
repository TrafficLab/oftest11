"""
OpenFlow instruction list class
"""

import oftest.action as action
import oftest.instruction as instruction
from action_list import action_list
from base_list import ofp_base_list
from cstruct import ofp_header
import unittest

# Instruction list

instruction_object_map = {
    action.OFPIT_GOTO_TABLE          : instruction.instruction_goto_table,
    action.OFPIT_WRITE_METADATA      : instruction.instruction_write_metadata,      
    action.OFPIT_WRITE_ACTIONS       : instruction.instruction_write_actions,       
    action.OFPIT_APPLY_ACTIONS       : instruction.instruction_apply_actions,       
    action.OFPIT_CLEAR_ACTIONS       : instruction.instruction_clear_actions,       
    action.OFPIT_EXPERIMENTER        : instruction.instruction_experimenter        
}

class instruction_list(ofp_base_list):
    """
    Maintain a list of instructions

    Data members:
    @arg instructions An array of instructions such as write_actions

    Methods:
    @arg pack: Pack the structure into a string
    @arg unpack: Unpack a string to objects, with proper typing
    @arg add: Add an action to the list; you can directly access
    the action member, but add will validate that the added object 
    is an action.

    """

    def __init__(self):
        ofp_base_list.__init__(self)
        self.instructions = self.items
        self.name = "instruction"
        self.class_list = instruction.instruction_class_list

    def unpack(self, binary_string, bytes=None):
        """
        Unpack a list of instructions
        
        Unpack instructions from a binary string, creating an array
        of objects of the appropriate type

        @param binary_string The string to be unpacked

        @param bytes The total length of the instruction list in bytes.  
        Ignored if decode is True.  If bytes is None and decode is false, the
        list is assumed to extend through the entire string.

        @return The remainder of binary_string that was not parsed

        """
        if bytes == None:
            bytes = len(binary_string)
        bytes_done = 0
        count = 0
        cur_string = binary_string
        while bytes_done < bytes:
            hdr = instruction.ofp_instruction()
            hdr.unpack(cur_string)
            if hdr.len < action.OFP_ACTION_HEADER_BYTES:
                print "ERROR: Action too short"
                break
            if not hdr.type in instruction_object_map.keys():
                print "WARNING: Skipping unknown action ", hdr.type, hdr.len
            else:
                self.instructions.append(instruction_object_map[hdr.type]())
                self.instructions[count].unpack(cur_string)
                count += 1
            cur_string = cur_string[hdr.len:]
            bytes_done += hdr.len
        return cur_string

class Instruction_List_Test(unittest.TestCase):
    def runTest(self):
        # instructions header is 8 bytes
        l = instruction_list()
        act = action.action_output()
        act.port = 7
        inst = instruction.instruction_apply_actions()
        self.assertTrue(inst.actions.add(act)) 
        self.assertTrue(l.add(inst))
        pkt = l.pack()
        # 24 == 8 (list header) + (apply header) 8 + (output action) 8 
        self.assertEqual(len(pkt),24)
       
        l = instruction_list()
        self.assertTrue(l.add(instruction.instruction_goto_table()))
        