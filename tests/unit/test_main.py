"""Module to test the main napp file."""
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch
from kytos.lib.helpers import (
    get_controller_mock,
    get_test_client,
    get_kytos_event_mock,
    get_switch_mock,
)
from napps.amlight.flow_stats.main import GenericFlow, Main
from napps.kytos.of_core.v0x01.flow import Action as Action10
from napps.kytos.of_core.v0x04.flow import Action as Action40
from napps.kytos.of_core.v0x04.match_fields import (
    MatchDLVLAN,
    MatchFieldFactory,
)
from pyof.foundation.basic_types import UBInt32
from pyof.v0x04.common.flow_instructions import InstructionType


# pylint: disable=too-many-public-methods, too-many-lines
class TestMain(TestCase):
    """Test the Main class."""

    def setUp(self):
        """Execute steps before each tests.

        Set the server_name_url_url from amlight/flow_stats
        """
        self.server_name_url = "http://localhost:8181/api/amlight/flow_stats"
        self.napp = Main(get_controller_mock())

    @staticmethod
    def get_napp_urls(napp):
        """Return the amlight/flow_stats urls.

        The urls will be like:

        urls = [
            (options, methods, url)
        ]

        """
        controller = napp.controller
        controller.api_server.register_napp_endpoints(napp)

        urls = []
        for rule in controller.api_server.app.url_map.iter_rules():
            options = {}
            for arg in rule.arguments:
                options[arg] = f"[{0}]".format(arg)

            if f"{napp.username}/{napp.name}" in str(rule):
                urls.append((options, rule.methods, f"{str(rule)}"))

        return urls

    def test_verify_api_urls(self):
        """Verify all APIs registered."""

        expected_urls = [
            (
                {"dpid": "[dpid]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/flow_stats/flow/match/ ",
            ),
            (
                {"dpid": "[dpid]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/flow_stats/flow/stats/",
            ),
            (
                {"flow_id": "[flow_id]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/flow_stats/packet_count/",
            ),
            (
                {"flow_id": "[flow_id]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/flow_stats/bytes_count/",
            ),
            (
                {"dpid": "[dpid]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/flow_stats/packet_count/per_flow/",
            ),
            (
                {"dpid": "[dpid]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/flow_stats/packet_count/sum/",
            ),
            (
                {"dpid": "[dpid]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/flow_stats/bytes_count/per_flow/",
            ),
            (
                {"dpid": "[dpid]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/flow_stats/bytes_count/sum/",
            ),
        ]
        urls = self.get_napp_urls(self.napp)
        self.assertEqual(len(expected_urls), len(urls))

    def test_packet_count__fail(self):
        """Test packet_count rest call with wrong flow_id."""
        flow_id = "123456789"
        rest_name = "packet_count"
        response = self._get_rest_response(rest_name, flow_id)

        self.assertEqual(response.data, b"Flow does not exist")

    def test_packet_count(self):
        """Test packet_count rest call."""
        flow_id = "1"
        rest_name = "packet_count"
        self._patch_switch_flow(flow_id)
        response = self._get_rest_response(rest_name, flow_id)

        json_response = json.loads(response.data)
        self.assertEqual(json_response["flow_id"], flow_id)
        self.assertEqual(json_response["packet_counter"], 40)
        self.assertEqual(json_response["packet_per_second"], 2.0)

    def test_bytes_count_fail(self):
        """Test bytes_count rest call with wrong flow_id."""
        flow_id = "123456789"
        rest_name = "bytes_count"
        response = self._get_rest_response(rest_name, flow_id)

        self.assertEqual(response.data, b"Flow does not exist")

    def test_bytes_count(self):
        """Test bytes_count rest call."""
        flow_id = "1"
        rest_name = "bytes_count"
        self._patch_switch_flow(flow_id)
        response = self._get_rest_response(rest_name, flow_id)

        json_response = json.loads(response.data)
        self.assertEqual(json_response["flow_id"], flow_id)
        self.assertEqual(json_response["bytes_counter"], 10)
        self.assertEqual(json_response["bits_per_second"], 4.0)

    def test_packet_count_per_flow(self):
        """Test packet_count_per_flow rest call."""
        flow_id = "1"
        rest_name = "packet_count/per_flow"
        self._patch_switch_flow(flow_id)

        dpid_id = 111
        response = self._get_rest_response(rest_name, dpid_id)

        json_response = json.loads(response.data)
        self.assertEqual(json_response[0]["flow_id"], flow_id)
        self.assertEqual(json_response[0]["packet_counter"], 40)
        self.assertEqual(json_response[0]["packet_per_second"], 2.0)

    def test_packet_count_sum(self):
        """Test packet_count_sum rest call."""
        flow_id = "1"
        rest_name = "packet_count/sum"
        self._patch_switch_flow(flow_id)

        dpid_id = 111
        response = self._get_rest_response(rest_name, dpid_id)
        json_response = json.loads(response.data)

        self.assertEqual(json_response, 40)

    def test_bytes_count_per_flow(self):
        """Test bytes_count_per_flow rest call."""
        flow_id = "1"
        rest_name = "bytes_count/per_flow"
        self._patch_switch_flow(flow_id)

        dpid_id = 111
        response = self._get_rest_response(rest_name, dpid_id)

        json_response = json.loads(response.data)
        self.assertEqual(json_response[0]["flow_id"], flow_id)
        self.assertEqual(json_response[0]["bytes_counter"], 10)
        self.assertEqual(json_response[0]["bits_per_second"], 4.0)

    def test_bytes_count_sum(self):
        """Test bytes_count_sum rest call."""
        flow_id = "1"
        rest_name = "bytes_count/sum"
        self._patch_switch_flow(flow_id)

        dpid_id = 111
        response = self._get_rest_response(rest_name, dpid_id)
        json_response = json.loads(response.data)

        self.assertEqual(json_response, 10)

    @patch("napps.amlight.flow_stats.main.Main.match_flows")
    def test_flow_match(self, mock_match_flows):
        """Test flow_match rest call."""
        flow = GenericFlow()
        flow.actions = [
            Action10.from_dict(
                {
                    "action_type": "output",
                    "port": "1",
                }
            ),
        ]
        flow.version = "0x04"
        mock_match_flows.return_value = flow

        flow_id = "1"
        rest_name = "flow/match"
        self._patch_switch_flow(flow_id)

        dpid_id = "aa:00:00:00:00:00:00:11"
        response = self._get_rest_response(rest_name, dpid_id)
        json_response = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_response["actions"][0]["action_type"], "output")
        self.assertEqual(json_response["actions"][0]["port"], "1")
        self.assertEqual(json_response["version"], "0x04")

    @patch("napps.amlight.flow_stats.main.Main.match_flows")
    def test_flow_match_fail(self, mock_match_flows):
        """Test flow_match rest call."""
        mock_match_flows.return_value = None

        flow_id = "1"
        rest_name = "flow/match"
        self._patch_switch_flow(flow_id)

        dpid_id = "aa:00:00:00:00:00:00:11"
        response = self._get_rest_response(rest_name, dpid_id)

        self.assertEqual(response.status_code, 404)

    @patch("napps.amlight.flow_stats.main.Main.match_flows")
    def test_flow_stats(self, mock_match_flows):
        """Test flow_match rest call."""
        flow = GenericFlow()
        flow.actions = [
            Action10.from_dict(
                {
                    "action_type": "output",
                    "port": "1",
                }
            ),
        ]
        flow.version = "0x04"
        mock_match_flows.return_value = [flow]

        flow_id = "1"
        rest_name = "flow/stats"
        self._patch_switch_flow(flow_id)

        dpid_id = "aa:00:00:00:00:00:00:11"
        response = self._get_rest_response(rest_name, dpid_id)
        json_response = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        print(json_response)
        self.assertEqual(json_response[0]["actions"][0]["action_type"],
                         "output")
        self.assertEqual(json_response[0]["actions"][0]["port"], "1")
        self.assertEqual(json_response[0]["version"], "0x04")

    def _patch_switch_flow(self, flow_id):
        """Helper method to patch controller to return switch/flow data."""
        # patching the flow_stats object in the switch
        self.napp.controller.switches = MagicMock()
        flow = self._get_mocked_flow_stats()
        flow.id = flow_id
        switch = MagicMock()
        switch.generic_flows = [flow]
        self.napp.controller.switches.values.return_value = [switch]
        self.napp.controller.get_switch_by_dpid = MagicMock()
        self.napp.controller.get_switch_by_dpid.return_value = switch

    def _get_rest_response(self, rest_name, url_id):
        """Helper method to call a rest endpoint."""
        # call rest
        api = get_test_client(get_controller_mock(), self.napp)
        url = f"{self.server_name_url}/{rest_name}/{url_id}"
        response = api.get(url, content_type="application/json")

        return response

    # pylint: disable=no-self-use
    def _get_mocked_flow_stats(self):
        """Helper method to create a mock flow_stats object."""
        flow_stats = MagicMock()
        flow_stats.id = 123
        flow_stats.byte_count = 10
        flow_stats.duration_sec = 20
        flow_stats.duration_nsec = 30
        flow_stats.packet_count = 40
        return flow_stats

    def _get_mocked_multipart_replies_flows(self):
        """Helper method to create mock multipart replies flows"""
        flow = self._get_mocked_flow_base()

        instruction = MagicMock()
        flow.instructions = [instruction]

        replies_flows = [flow]
        return replies_flows

    def _get_mocked_flow_base(self):
        """Helper method to create a mock flow object."""
        flow = MagicMock()
        flow.id = 456
        flow.switch = None
        flow.table_id = None
        flow.match = None
        flow.priority = None
        flow.idle_timeout = None
        flow.hard_timeout = None
        flow.cookie = None
        flow.stats = self._get_mocked_flow_stats()
        return flow

    @patch("napps.amlight.flow_stats.main.GenericFlow.from_flow_stats")
    def test_handle_stats_reply(self, mock_from_flow):
        """Test handle_stats_reply rest call."""
        mock_from_flow.return_value = self._get_mocked_flow_base()

        def side_effect(event):
            self.assertTrue(f"{event}", "amlight/flow_stats.flows_updated")
            self.assertTrue(event.content["switch"], 111)

        self.napp.controller = MagicMock()
        self.napp.controller.buffers.app.put.side_effect = side_effect

        msg = MagicMock()
        msg.flags.value = 2
        msg.body = [self._get_mocked_flow_stats()]
        event_switch = MagicMock()
        event_switch.generic_flows = []
        event_switch.dpid = 111
        self.napp.handle_stats_reply(msg, event_switch)

        # Check if important trace dont trigger the event
        # It means that the CP trace is the same to the DP trace
        self.napp.controller.buffers.app.put.assert_called_once()

        # Check mocked flow id
        self.assertEqual(event_switch.generic_flows[0].id, 456)

    @patch("napps.amlight.flow_stats.main.Main.handle_stats_reply_received")
    def test_handle_stats_received(self, mock_handle_stats):
        """Test handle_stats_received function."""

        switch_v0x04 = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        replies_flows = self._get_mocked_multipart_replies_flows()
        name = "kytos/of_core.flow_stats.received"
        content = {"switch": switch_v0x04, "replies_flows": replies_flows}

        event = get_kytos_event_mock(name=name, content=content)

        self.napp.handle_stats_received(event)
        mock_handle_stats.assert_called_once()

    @patch("napps.amlight.flow_stats.main.Main.handle_stats_reply_received")
    def test_handle_stats_received_fail(self, mock_handle_stats):
        """Test handle_stats_received function for
        fail when replies_flows is not in content."""

        switch_v0x04 = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        name = "kytos/of_core.flow_stats.received"
        content = {"switch": switch_v0x04}

        event = get_kytos_event_mock(name=name, content=content)

        self.napp.handle_stats_received(event)
        mock_handle_stats.assert_not_called()

    @patch("napps.amlight.flow_stats.main.GenericFlow.from_replies_flows")
    def test_handle_stats_reply_received(self, mock_from_flow):
        """Test handle_stats_reply_received call."""
        mock_from_flow.return_value = self._get_mocked_flow_base()

        self.napp.controller = MagicMock()

        event_switch = MagicMock()
        event_switch.dpid = 111
        flows_mock = self._get_mocked_multipart_replies_flows()
        self.napp.handle_stats_reply_received(event_switch, [flows_mock])

        self.assertEqual(event_switch.generic_flows[0].id, 456)


# pylint: disable=too-many-public-methods, too-many-lines
class TestGenericFlow(TestCase):
    """Test the GenericFlow class."""

    # pylint: disable=no-member
    def test_from_flow_stats__x01(self):
        """Test from_flow_stats method 0x01 version."""
        flow_stats = MagicMock()

        flow_stats.actions = [
            Action10.from_dict(
                {
                    "action_type": "output",
                    "port": UBInt32(1),
                }
            ).as_of_action(),
        ]

        result = GenericFlow.from_flow_stats(flow_stats, version="0x01")

        self.assertEqual(result.idle_timeout, flow_stats.idle_timeout.value)
        self.assertEqual(result.hard_timeout, flow_stats.hard_timeout.value)
        self.assertEqual(result.priority, flow_stats.priority.value)
        self.assertEqual(result.table_id, flow_stats.table_id.value)
        self.assertEqual(result.duration_sec, flow_stats.duration_sec.value)
        self.assertEqual(result.packet_count, flow_stats.packet_count.value)
        self.assertEqual(result.byte_count, flow_stats.byte_count.value)

        exp_match = flow_stats.match
        self.assertEqual(result.match["wildcards"], exp_match.wildcards.value)
        self.assertEqual(result.match["in_port"], exp_match.in_port.value)
        self.assertEqual(result.match["eth_src"], exp_match.dl_src.value)
        self.assertEqual(result.match["eth_dst"], exp_match.dl_dst.value)
        self.assertEqual(result.match["vlan_vid"], exp_match.dl_vlan.value)
        self.assertEqual(result.match["vlan_pcp"], exp_match.dl_vlan_pcp.value)
        self.assertEqual(result.match["eth_type"], exp_match.dl_type.value)
        self.assertEqual(result.match["ip_tos"], exp_match.nw_tos.value)
        self.assertEqual(result.match["ipv4_src"], exp_match.nw_src.value)
        self.assertEqual(result.match["ipv4_dst"], exp_match.nw_dst.value)
        self.assertEqual(result.match["ip_proto"], exp_match.nw_proto.value)
        self.assertEqual(result.match["tcp_src"], exp_match.tp_src.value)
        self.assertEqual(result.match["tcp_dst"], exp_match.tp_dst.value)

    def test_from_flow_stats__x04_match(self):
        """Test from_flow_stats method 0x04 version with match."""
        flow_stats = MagicMock()
        flow_stats.actions = [
            Action10.from_dict(
                {
                    "action_type": "output",
                    "port": UBInt32(1),
                }
            ).as_of_action(),
        ]

        flow_stats.match.oxm_match_fields = [MatchDLVLAN(42).as_of_tlv()]

        result = GenericFlow.from_flow_stats(flow_stats, version="0x04")

        match_expect = MatchFieldFactory.from_of_tlv(
            flow_stats.match.oxm_match_fields[0]
        )
        self.assertEqual(result.match["vlan_vid"], match_expect)

    def test_from_flow_stats__x04_action(self):
        """Test from_flow_stats method 0x04 version with action."""
        flow_stats = MagicMock()

        action_dict = {
            "action_type": "output",
            "port": UBInt32(1),
        }
        instruction = MagicMock()
        instruction.instruction_type = InstructionType.OFPIT_APPLY_ACTIONS
        instruction.actions = [Action40.from_dict(action_dict).as_of_action()]
        flow_stats.instructions = [instruction]

        result = GenericFlow.from_flow_stats(flow_stats, version="0x04")
        self.assertEqual(result.actions[0].as_dict(), action_dict)

    # pylint: disable=no-member
    def test_from_replies_flows(self):
        """Test from_replies_flows function."""
        replies_flow = MagicMock()

        replies_flow.match.oxm_match_fields = [MatchDLVLAN(42).as_of_tlv()]

        action_dict = {
            "action_type": "output",
            "port": UBInt32(1),
        }
        instruction = MagicMock()
        instruction.instruction_type = InstructionType.OFPIT_APPLY_ACTIONS
        instruction.actions = [Action40.from_dict(action_dict).as_of_action()]
        replies_flow.instructions = [instruction]

        result = GenericFlow.from_replies_flows(replies_flow)

        self.assertEqual(result.idle_timeout, replies_flow.idle_timeout.value)
        self.assertEqual(result.hard_timeout, replies_flow.hard_timeout.value)
        self.assertEqual(result.priority, replies_flow.priority.value)
        self.assertEqual(result.table_id, replies_flow.table_id.value)
        self.assertEqual(result.cookie, replies_flow.cookie.value)
        self.assertEqual(result.duration_sec, replies_flow.duration_sec.value)
        self.assertEqual(result.packet_count, replies_flow.packet_count.value)
        self.assertEqual(result.byte_count, replies_flow.byte_count.value)
        self.assertEqual(result.duration_sec, replies_flow.duration_sec.value)
        self.assertEqual(result.packet_count, replies_flow.packet_count.value)
        self.assertEqual(result.byte_count, replies_flow.byte_count.value)

        match_expect = MatchFieldFactory.from_of_tlv(
            replies_flow.match.oxm_match_fields[0]
        )
        self.assertEqual(result.match["vlan_vid"], match_expect)
        self.assertEqual(result.actions[0].as_dict(), action_dict)

    def test_to_dict__x01(self):
        """Test to_dict method 0x01 version."""
        action = Action10.from_dict(
            {
                "action_type": "set_vlan",
                "vlan_id": 6,
            }
        )
        match = {}
        match["in_port"] = 11

        generic_flow = GenericFlow(
            version="0x01",
            match=match,
            idle_timeout=1,
            hard_timeout=2,
            duration_sec=3,
            packet_count=4,
            byte_count=5,
            priority=6,
            table_id=7,
            cookie=8,
            buffer_id=9,
            actions=[action],
        )

        result = generic_flow.to_dict()

        expected = {
            "version": "0x01",
            "idle_timeout": 1,
            "in_port": 11,
            "hard_timeout": 2,
            "priority": 6,
            "table_id": 7,
            "cookie": 8,
            "buffer_id": 9,
            "actions": [{"vlan_id": 6, "action_type": "set_vlan"}],
        }

        self.assertEqual(result, expected)

    def test_to_dict__x04(self):
        """Test to_dict method 0x04 version."""
        match = {}
        match["in_port"] = MagicMock()
        match["in_port"].value = 22

        generic_flow = GenericFlow(
            version="0x04",
            match=match,
        )

        result = generic_flow.to_dict()
        expected = {
            "version": "0x04",
            "in_port": 22,
            "idle_timeout": 0,
            "hard_timeout": 0,
            "priority": 0,
            "table_id": 255,
            "cookie": None,
            "buffer_id": None,
            "actions": [],
        }

        self.assertEqual(result, expected)

    def test_match_to_dict(self):
        """Test match_to_dict method for 0x04 version."""
        match = {}
        match["in_port"] = MagicMock()
        match["in_port"].value = 22
        match["vlan_vid"] = MagicMock()
        match["vlan_vid"].value = 123

        generic_flow = GenericFlow(
            version="0x04",
            match=match,
        )
        result = generic_flow.match_to_dict()
        expected = {"in_port": 22, "vlan_vid": 123}

        self.assertEqual(result, expected)

    def test_match_to_dict__empty_match(self):
        """Test match_to_dict method for 0x04 version, with empty matches."""
        generic_flow = GenericFlow(version="0x04")
        result = generic_flow.match_to_dict()
        self.assertEqual(result, {})

    def test_id__x01(self):
        """Test id method 0x01 version."""
        action = Action10.from_dict(
            {
                "action_type": "set_vlan",
                "vlan_id": 6,
            }
        )
        match = {}
        match["in_port"] = 11

        generic_flow = GenericFlow(
            version="0x01",
            match=match,
            idle_timeout=1,
            hard_timeout=2,
            priority=6,
            table_id=7,
            cookie=8,
            buffer_id=9,
            actions=[action],
        )

        self.assertEqual(generic_flow.id, "78d18f2cffd3eaa069afbf0995b90db9")

    def test_id__x04(self):
        """Test id method 0x04 version."""
        match = {}
        match["in_port"] = MagicMock()
        match["in_port"].value = 22
        match["vlan_vid"] = MagicMock()
        match["vlan_vid"].value = 123

        generic_flow = GenericFlow(
            version="0x04",
            match=match,
            idle_timeout=1,
            hard_timeout=2,
            priority=6,
            table_id=7,
            cookie=8,
            buffer_id=9,
        )

        self.assertEqual(generic_flow.id, "2d843f76b8b254fad6c6e2a114590440")
