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
from napps.amlight.flow_stats.main import Main
from napps.kytos.of_core.v0x04.flow import Action as Action40
from napps.kytos.of_core.v0x04.flow import Flow as Flow40
from napps.kytos.of_core.v0x04.match_fields import MatchFieldFactory
from napps.kytos.of_core.v0x04.flow import Match as Match40
from pyof.foundation.basic_types import UBInt32


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
        flow = Flow40()
        flow.actions = [
            Action40.from_dict(
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
        flow = Flow40()
        flow.actions = [
            Action40.from_dict(
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
        flow = self._get_mocked_flow_stats()
        flow.id = flow_id
        switch = MagicMock()
        switch.flows = [flow]
        self.napp.controller.switches = {"1": switch}
        self.napp.controller.get_switch_by_dpid = MagicMock()
        self.napp.controller.get_switch_by_dpid.return_value = switch

    def _get_rest_response(self, rest_name, url_id):
        """Helper method to call a rest endpoint."""
        # call rest
        api = get_test_client(get_controller_mock(), self.napp)
        url = f"{self.server_name_url}/{rest_name}/{url_id}"
        response = api.get(url, content_type="application/json")

        return response

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

    def test_handle_stats_reply_received(self, mock_from_flow):
        """Test handle_stats_reply_received call."""
        event_switch = MagicMock()
        flows_mock = self._get_mocked_multipart_replies_flows()
        self.napp.handle_stats_reply_received(event_switch, flows_mock)

        self.assertEqual(event_switch.flows[0].id, 456)
