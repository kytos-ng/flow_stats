"""Main module of amlight/flow_stats Kytos Network Application.

This NApp does operations with flows not covered by Kytos itself.
"""
# pylint: disable=too-many-return-statements,too-many-instance-attributes
# pylint: disable=too-many-arguments,too-many-branches,too-many-statements

import hashlib
import ipaddress
import json
from threading import Lock

import pyof.v0x01.controller2switch.common as common01
import pyof.v0x04.controller2switch.common as common04
from flask import jsonify, request
from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import listen_to
from napps.amlight.flow_stats.utils import format_request
from napps.amlight.sdntrace import constants
from napps.kytos.of_core.v0x01.flow import Action as Action10
from napps.kytos.of_core.v0x04.flow import Action as Action13
from napps.kytos.of_core.v0x04.match_fields import MatchFieldFactory
from pyof.v0x01.common.flow_match import FlowWildCards
from pyof.v0x04.common.flow_instructions import InstructionType


class GenericFlow():
    """Class to represent a flow.

        This class represents a flow regardless of the OF version."""

    def __init__(self, version='0x01', match=None, idle_timeout=0,
                 hard_timeout=0, duration_sec=0, packet_count=0, byte_count=0,
                 priority=0, table_id=0xff, cookie=None, buffer_id=None,
                 actions=None):
        self.version = version
        self.match = match if match else {}
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout
        self.duration_sec = duration_sec
        self.packet_count = packet_count
        self.byte_count = byte_count
        self.priority = priority
        self.table_id = table_id
        self.cookie = cookie
        self.buffer_id = buffer_id
        self.actions = actions if actions else []

    def __eq__(self, other):
        return self.id == other.id

    @property
    def id(self):
        # pylint: disable=invalid-name
        """Return the hash of the object.
        Calculates the hash of the object by using the hashlib we use md5 of
        strings.
        Returns:
            string: Hash of object.
        """
        hash_result = hashlib.md5()
        hash_result.update(str(self.version).encode('utf-8'))
        for value in self.match.values():
            if self.version == '0x01':
                hash_result.update(str(value).encode('utf-8'))
            else:
                hash_result.update(str(value.value).encode('utf-8'))
        hash_result.update(str(self.idle_timeout).encode('utf-8'))
        hash_result.update(str(self.hard_timeout).encode('utf-8'))
        hash_result.update(str(self.priority).encode('utf-8'))
        hash_result.update(str(self.table_id).encode('utf-8'))
        hash_result.update(str(self.cookie).encode('utf-8'))
        hash_result.update(str(self.buffer_id).encode('utf-8'))

        return hash_result.hexdigest()

    def to_dict(self):
        """Convert flow to a dictionary."""
        flow_dict = {}
        flow_dict['version'] = self.version
        if self.version == '0x01':
            flow_dict.update(self.match)
        else:
            flow_dict.update(self.match_to_dict())
        flow_dict['idle_timeout'] = self.idle_timeout
        flow_dict['hard_timeout'] = self.hard_timeout
        flow_dict['priority'] = self.priority
        flow_dict['table_id'] = self.table_id
        flow_dict['cookie'] = self.cookie
        flow_dict['buffer_id'] = self.buffer_id
        flow_dict['actions'] = []
        for action in self.actions:
            flow_dict['actions'].append(action.as_dict())

        return flow_dict

    def match_to_dict(self):
        """Convert a match in OF 1.3 to a dictionary."""
        # pylint: disable=consider-using-dict-items
        match = {}
        for name in self.match:
            match[name] = self.match[name].value
        return match

    def to_json(self):
        """Return a json version of the flow."""
        return json.dumps(self.to_dict())

    # @staticmethod
    # def from_dict(flow_dict):
    #     """Create a flow from a dict."""
    #     flow = GenericFlow()
    #     for attr_name, value in flow_dict.items():
    #         if attr_name == 'actions':
    #             flow.actions = []
    #             for action in value:
    #                 new_action = ACTION_TYPES[int(action['action_type'])]()
    #                 for action_attr_name,
    #                     action_attr_value in action.items():
    #
    #                     setattr(new_action,
    #                             action_attr_name,
    #                             action_attr_value)
    #                 flow.actions.append(new_action)
    #         else:
    #             setattr(flow, attr_name, value)
    #     return flow

    @classmethod
    def from_flow_stats(cls, flow_stats, version='0x01'):
        """Create a flow from OF flow stats."""
        flow = GenericFlow(version=version)
        flow.idle_timeout = flow_stats.idle_timeout.value
        flow.hard_timeout = flow_stats.hard_timeout.value
        flow.priority = flow_stats.priority.value
        flow.table_id = flow_stats.table_id.value
        flow.duration_sec = flow_stats.duration_sec.value
        flow.packet_count = flow_stats.packet_count.value
        flow.byte_count = flow_stats.byte_count.value
        if version == '0x01':
            flow.match['wildcards'] = flow_stats.match.wildcards.value
            flow.match['in_port'] = flow_stats.match.in_port.value
            flow.match['eth_src'] = flow_stats.match.dl_src.value
            flow.match['eth_dst'] = flow_stats.match.dl_dst.value
            flow.match['vlan_vid'] = flow_stats.match.dl_vlan.value
            flow.match['vlan_pcp'] = flow_stats.match.dl_vlan_pcp.value
            flow.match['eth_type'] = flow_stats.match.dl_type.value
            flow.match['ip_tos'] = flow_stats.match.nw_tos.value
            flow.match['ipv4_src'] = flow_stats.match.nw_src.value
            flow.match['ipv4_dst'] = flow_stats.match.nw_dst.value
            flow.match['ip_proto'] = flow_stats.match.nw_proto.value
            flow.match['tcp_src'] = flow_stats.match.tp_src.value
            flow.match['tcp_dst'] = flow_stats.match.tp_dst.value
            flow.actions = []
            for of_action in flow_stats.actions:
                action = Action10.from_of_action(of_action)
                flow.actions.append(action)
        elif version == '0x04':
            for match in flow_stats.match.oxm_match_fields:
                match_field = MatchFieldFactory.from_of_tlv(match)
                field_name = match_field.name
                if field_name == 'dl_vlan':
                    field_name = 'vlan_vid'
                flow.match[field_name] = match_field
            flow.actions = []
            for instruction in flow_stats.instructions:
                if instruction.instruction_type == \
                        InstructionType.OFPIT_APPLY_ACTIONS:
                    for of_action in instruction.actions:
                        action = Action13.from_of_action(of_action)
                        flow.actions.append(action)
        return flow

    def do_match(self, args):
        """Match a packet against this flow."""
        if self.version == '0x01':
            return self.match10(args)
        if self.version == '0x04':
            return self.match13(args)
        return None

    def match10(self, args):
        """Match a packet against this flow (OF1.0)."""
        log.debug('Matching packet')
        if not self.match['wildcards'] & FlowWildCards.OFPFW_IN_PORT:
            if 'in_port' not in args:
                return False
            if self.match['in_port'] != int(args['in_port']):
                return False
        if not self.match['wildcards'] & FlowWildCards.OFPFW_DL_VLAN_PCP:
            if 'vlan_pcp' not in args:
                return False
            if self.match['vlan_pcp'] != int(args['vlan_pcp']):
                return False
        if not self.match['wildcards'] & FlowWildCards.OFPFW_DL_VLAN:
            if 'vlan_vid' not in args:
                return False
            if self.match['vlan_vid'] != args['vlan_vid'][-1]:
                return False
        if not self.match['wildcards'] & FlowWildCards.OFPFW_DL_SRC:
            if 'eth_src' not in args:
                return False
            if self.match['eth_src'] != args['eth_src']:
                return False
        if not self.match['wildcards'] & FlowWildCards.OFPFW_DL_DST:
            if 'eth_dst' not in args:
                return False
            if self.match['eth_dst'] != args['eth_dst']:
                return False
        if not self.match['wildcards'] & FlowWildCards.OFPFW_DL_TYPE:
            if 'eth_type' not in args:
                return False
            if self.match['eth_type'] != int(args['eth_type']):
                return False
        if self.match['eth_type'] == constants.IPV4:
            flow_ip_int = int(ipaddress.IPv4Address(self.match['ipv4_src']))
            if flow_ip_int != 0:
                mask = ((self.match['wildcards'] &
                         FlowWildCards.OFPFW_NW_SRC_MASK) >>
                        FlowWildCards.OFPFW_NW_SRC_SHIFT)
                mask = min(mask, 32)
                if mask != 32 and 'ipv4_src' not in args:
                    return False
                mask = (0xffffffff << mask) & 0xffffffff
                ip_int = int(ipaddress.IPv4Address(args['ipv4_src']))
                if ip_int & mask != flow_ip_int & mask:
                    return False

            flow_ip_int = int(ipaddress.IPv4Address(self.match['ipv4_dst']))
            if flow_ip_int != 0:
                mask = ((self.match['wildcards'] &
                         FlowWildCards.OFPFW_NW_DST_MASK) >>
                        FlowWildCards.OFPFW_NW_DST_SHIFT)
                mask = min(mask, 32)
                if mask != 32 and 'ipv4_dst' not in args:
                    return False
                mask = (0xffffffff << mask) & 0xffffffff
                ip_int = int(ipaddress.IPv4Address(args['ipv4_dst']))
                if ip_int & mask != flow_ip_int & mask:
                    return False
            if not self.match['wildcards'] & FlowWildCards.OFPFW_NW_TOS:
                if 'ip_tos' not in args:
                    return False
                if self.match['ip_tos'] != int(args['ip_tos']):
                    return False
            if not self.match['wildcards'] & FlowWildCards.OFPFW_NW_PROTO:
                if 'ip_proto' not in args:
                    return False
                if self.match['ip_proto'] != int(args['ip_proto']):
                    return False
            if not self.match['wildcards'] & FlowWildCards.OFPFW_TP_SRC:
                if 'tp_src' not in args:
                    return False
                if self.match['tcp_src'] != int(args['tp_src']):
                    return False
            if not self.match['wildcards'] & FlowWildCards.OFPFW_TP_DST:
                if 'tp_dst' not in args:
                    return False
                if self.match['tcp_dst'] != int(args['tp_dst']):
                    return False
        return self

    def match13(self, args):
        """Match a packet against this flow (OF1.3)."""
        # pylint: disable=consider-using-dict-items
        for name in self.match:
            if name not in args:
                return False
            if name == 'vlan_vid':
                field = args[name][-1]
            else:
                field = args[name]
            if name not in ('ipv4_src', 'ipv4_dst', 'ipv6_src', 'ipv6_dst'):
                if self.match[name].value != field:
                    return False
            else:
                packet_ip = int(ipaddress.ip_address(field))
                ip_addr = self.match[name].value
                if packet_ip & ip_addr.netmask != ip_addr.address:
                    return False
        return self


class Main(KytosNApp):
    """Main class of amlight/flow_stats NApp.

    This class is the entry point for this napp.
    """

    def setup(self):
        """Replace the '__init__' method for the KytosNApp subclass.

        The setup method is automatically called by the controller when your
        application is loaded.

        So, if you have any setup routine, insert it here.
        """
        log.info('Starting Kytos/Amlight flow manager')
        for switch in self.controller.switches.values():
            switch.generic_flows = []
        self.switch_stats_xid = {}
        self.switch_stats_lock = {}

    def execute(self):
        """This method is executed right after the setup method execution.

        You can also use this method in loop mode if you add to the above setup
        method a line like the following example:

            self.execute_as_loop(30)  # 30-second interval.
        """

    def shutdown(self):
        """This method is executed when your napp is unloaded.

        If you have some cleanup procedure, insert it here.
        """

    def flow_from_id(self, flow_id):
        """Flow from given flow_id."""
        for switch in self.controller.switches.values():
            try:
                for flow in switch.generic_flows:
                    if flow.id == flow_id:
                        return flow
            except KeyError:
                pass
        return None

    @rest('flow/match/<dpid>')
    def flow_match(self, dpid):
        """Return first flow matching request."""
        switch = self.controller.get_switch_by_dpid(dpid)
        flow = self.match_flows(switch, format_request(request.args), False)
        if flow:
            return jsonify(flow.to_dict())
        return "No match", 404

    @rest('flow/stats/<dpid>')
    def flow_stats(self, dpid):
        """Return all flows matching request."""
        switch = self.controller.get_switch_by_dpid(dpid)
        if not switch:
            return f"switch {dpid} not found", 404
        flows = self.match_flows(switch, format_request(request.args), True)
        flows = [flow.to_dict() for flow in flows]
        return jsonify(flows)

    @staticmethod
    def match_flows(switch, args, many=True):
        # pylint: disable=bad-staticmethod-argument
        """
        Match the packet in request against the flows installed in the switch.

        Try the match with each flow, in other. If many is True, tries the
        match with all flows, if False, tries until the first match.
        :param args: packet data
        :param many: Boolean, indicating whether to continue after matching the
                first flow or not
        :return: If many, the list of matched flows, or the matched flow
        """
        response = []
        try:
            for flow in switch.generic_flows:
                match = flow.do_match(args)
                if match:
                    if many:
                        response.append(match)
                    else:
                        response = match
                        break
        except AttributeError:
            return None
        if not many and isinstance(response, list):
            return None
        return response

    @staticmethod
    def match_and_apply(switch, args):
        # pylint: disable=bad-staticmethod-argument
        """Match flows and apply actions.

        Match given packet (in args) against the switch flows and,
        if a match flow is found, apply its actions."""
        flow = Main.match_flows(switch, args, False)
        port = None
        actions = None
        # pylint: disable=too-many-nested-blocks
        if flow:
            actions = flow.actions
            if switch.ofp_version == '0x01':
                for action in actions:
                    action_type = action.action_type
                    if action_type == 'output':
                        port = action.port
                    elif action_type == 'set_vlan':
                        if 'vlan_vid' in args:
                            args['vlan_vid'][-1] = action.vlan_id
                        else:
                            args['vlan_vid'] = [action.vlan_id]
            elif switch.ofp_version == '0x04':
                for action in actions:
                    action_type = action.action_type
                    if action_type == 'output':
                        port = action.port
                    if action_type == 'push_vlan':
                        if 'vlan_vid' not in args:
                            args['vlan_vid'] = []
                        args['vlan_vid'].append(0)
                    if action_type == 'pop_vlan':
                        if 'vlan_vid' in args:
                            args['vlan_vid'].pop()
                            if len(args['vlan_vid']) == 0:
                                del args['vlan_vid']
                    if action_type == 'set_vlan':
                        args['vlan_vid'][-1] = action.vlan_id
        return flow, args, port

    @rest('packet_count/<flow_id>')
    def packet_count(self, flow_id):
        """Packet count of an specific flow."""
        flow = self.flow_from_id(flow_id)
        if flow is None:
            return "Flow does not exist", 404
        packet_stats = {
            'flow_id': flow_id,
            'packet_counter': flow.packet_count,
            'packet_per_second': flow.packet_count / flow.duration_sec
            }
        return jsonify(packet_stats)

    @rest('bytes_count/<flow_id>')
    def bytes_count(self, flow_id):
        """Bytes count of an specific flow."""
        flow = self.flow_from_id(flow_id)
        if flow is None:
            return "Flow does not exist", 404
        bytes_stats = {
            'flow_id': flow_id,
            'bytes_counter': flow.byte_count,
            'bits_per_second': flow.byte_count * 8 / flow.duration_sec
            }
        return jsonify(bytes_stats)

    @rest('packet_count/per_flow/<dpid>')
    def packet_count_per_flow(self, dpid):
        """Per flow packet count."""
        return self.flows_counters('packet_count',
                                   dpid,
                                   counter='packet_counter',
                                   rate='packet_per_second')

    @rest('packet_count/sum/<dpid>')
    def packet_count_sum(self, dpid):
        """Sum of packet count flow stats."""
        return self.flows_counters('packet_count',
                                   dpid,
                                   total=True)

    @rest('bytes_count/per_flow/<dpid>')
    def bytes_count_per_flow(self, dpid):
        """Per flow bytes count."""
        return self.flows_counters('byte_count',
                                   dpid,
                                   counter='bytes_counter',
                                   rate='bits_per_second')

    @rest('bytes_count/sum/<dpid>')
    def bytes_count_sum(self, dpid):
        """Sum of bytes count flow stats."""
        return self.flows_counters('byte_count',
                                   dpid,
                                   total=True)

    def flows_counters(self, field, dpid, counter=None, rate=None,
                       total=False):
        """Calculate flows statistics.

        The returned statistics are both per flow and for the sum of flows
        """
        # pylint: disable=too-many-arguments
        # pylint: disable=unused-variable
        start_date = request.args.get('start_date', 0)
        end_date = request.args.get('end_date', 0)
        # pylint: enable=unused-variable

        if total:
            count_flows = 0
        else:
            count_flows = []
            if not counter:
                counter = field
            if not rate:
                rate = field

        # We don't have statistics persistence yet, so for now this only works
        # for start and end equals to zero
        flows = self.controller.get_switch_by_dpid(dpid).generic_flows

        for flow in flows:
            count = getattr(flow, field)
            if total:
                count_flows += count
            else:
                per_second = count / flow.duration_sec
                if rate.startswith('bits'):
                    per_second *= 8
                count_flows.append({'flow_id': flow.id,
                                    counter: count,
                                    rate: per_second})

        return jsonify(count_flows)

    @listen_to('kytos/of_core.v0x01.messages.in.ofpt_stats_reply')
    def on_stats_reply_0x01(self, event):
        """Capture flow stats messages for v0x01 switches."""
        self.handle_stats_reply_0x01(event)

    def handle_stats_reply_0x01(self, event):
        """Handle stats replies for v0x01 switches."""
        msg = event.content['message']
        if msg.body_type == common01.StatsType.OFPST_FLOW:
            switch = event.source.switch
            self.handle_stats_reply(msg, switch)

    def handle_stats_reply(self, msg, switch):
        """Insert flows received in the switch list of flows."""
        try:
            old_flows = switch.generic_flows
        except AttributeError:
            old_flows = []
        is_new_xid = (
            int(msg.header.xid) != self.switch_stats_xid.get(switch.id, 0)
        )
        is_last_part = msg.flags.value % 2 == 0
        self.switch_stats_lock.setdefault(switch.id, Lock())
        with self.switch_stats_lock[switch.id]:
            if is_new_xid:
                switch.generic_new_flows = []
                self.switch_stats_xid[switch.id] = int(msg.header.xid)
            for flow_stats in msg.body:
                flow = GenericFlow.from_flow_stats(flow_stats,
                                                   switch.ofp_version)
                switch.generic_new_flows.append(flow)
            if is_last_part:
                switch.generic_flows = switch.generic_new_flows
                switch.generic_flows.sort(
                    key=lambda f: (f.priority, f.duration_sec),
                    reverse=True
                )
        if is_new_xid and is_last_part and switch.generic_flows != old_flows:
            # Generate an event informing that flows have changed
            event = KytosEvent('amlight/flow_stats.flows_updated')
            event.content['switch'] = switch.dpid
            self.controller.buffers.app.put(event)

    @listen_to('kytos/of_core.flow_stats.received')
    def handle_stats_received(self, event):
        """Capture and handle flow stats messages for OpenFlow 1.3."""
        msg = event.content['message']
        switch = event.source.switch
        if msg.multipart_type == common04.MultipartType.OFPMP_FLOW:
            try:
                replies_flows = event.content['replies_flows']
                self.handle_stats_reply_received(msg, switch, replies_flows)
            except AttributeError as err:
                log.error(err)

    def handle_stats_reply_received(self, msg, switch, replies_flows):
        """Iterate on the replies and set the generic flows"""
        flow = GenericFlow.from_flow_stats(replies_flows, switch.ofp_version)
        switch.generic_new_flows.append(flow)
        switch.generic_flows = switch.generic_new_flows
        switch.generic_flows.sort(
            key=lambda f: (f.priority, f.duration_sec),
            reverse=True
        )
        if int(msg.header.xid) != self.switch_stats_xid.get(switch.id, 0):
            # Generate an event informing that flows have changed
            event = KytosEvent('amlight/flow_stats.flows_updated')
            event.content['switch'] = switch.dpid
            self.controller.buffers.app.put(event)
