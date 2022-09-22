"""Main module of amlight/flow_stats Kytos Network Application.

This NApp does operations with flows not covered by Kytos itself.
"""
# pylint: disable=too-many-return-statements,too-many-instance-attributes
# pylint: disable=too-many-arguments,too-many-branches,too-many-statements

import hashlib
import ipaddress
import json
from threading import Lock

from flask import jsonify, request
from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import listen_to
from napps.amlight.flow_stats.utils import format_request
from napps.kytos.of_core.v0x04.flow import Action as Action13
from napps.kytos.of_core.v0x04.match_fields import MatchFieldFactory

# pylint: disable=too-many-public-methods
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
        for switch in self.controller.switches.copy().values():
            switch.stat_flows = []

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
        for switch in self.controller.switches.copy().values():
            try:
                for flow in switch.stat_flows: 
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
            for flow in switch.stat_flows: 
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
            if switch.ofp_version == '0x04':
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
            'packet_counter': flow.stats.packet_count,
            'packet_per_second': flow.stats.packet_count / flow.stats.duration_sec
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
            'bytes_counter': flow.stats.byte_count,
            'bits_per_second': flow.stats.byte_count * 8 / flow.stats.duration_sec
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
        flows = self.controller.get_switch_by_dpid(dpid).stat_flows 

        for flow in flows:
            count = getattr(flow, field)
            if total:
                count_flows += count
            else:
                per_second = count / flow.stats.duration_sec
                if rate.startswith('bits'):
                    per_second *= 8
                count_flows.append({'flow_id': flow.id,
                                    counter: count,
                                    rate: per_second})

        return jsonify(count_flows)

    @listen_to('kytos/of_core.flow_stats.received')
    def on_stats_received(self, event):
        """Capture flow stats messages for OpenFlow 1.3."""
        self.handle_stats_received(event)

    def handle_stats_received(self, event):
        """Handle flow stats messages for OpenFlow 1.3."""
        switch = event.content['switch']
        if 'replies_flows' in event.content:
            replies_flows = event.content['replies_flows']
            self.handle_stats_reply_received(switch, replies_flows)

    def handle_stats_reply_received(self, switch, replies_flows):
        """Iterate on the replies and set the list of flows"""
        switch.stat_flows = replies_flows
        switch.stat_flows.sort(
                    key=lambda f: (f.priority, f.stats.duration_sec),
                    reverse=True
                    )
