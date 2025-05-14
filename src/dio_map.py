import json
import logging
import traceback

from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import SubscriptionResponseMessage
from awsiot.greengrasscoreipc.model import JsonMessage, PublishMessage

logger = logging.getLogger(__name__)

class DIOMap:
    def __init__(self, ipc_client: GreengrassCoreIPCClientV2, thing_name: str, shadow_name: str, feature_topic: str, annotated_topic: str, rules: list):
        self.ipc_client = ipc_client
        self.thing_name = thing_name
        self.shadow_name = shadow_name
        self.feature_topic = feature_topic
        self.annotated_topic = annotated_topic
        self.current_gpio_state = None
        self.rules_map = {rule["name"]: rule["label"] for rule in rules}
        self.latest_feature_data = {}

    def init_shadow_state(self):
        try:
            response = self.ipc_client.get_thing_shadow(
                thing_name=self.thing_name,
                shadow_name=self.shadow_name
            )
            shadow_json = json.loads(response.payload.decode("utf-8"))
            self.current_gpio_state = shadow_json.get("state", {}).get("reported", {}).get("gpio_state", [])
            logger.info(f"[Init] Got initial gpio_state from shadow: {self.current_gpio_state}")
        except Exception as e:
            logger.error("Failed to get initial shadow state: %s", e)
            traceback.print_exc()


    def _on_feature_stream_event(self, event: SubscriptionResponseMessage):
        try:
            msg = event.json_message.message # {"timestamp":1.7459860725371535E9,"feature_interval":1.0,"n_extracted_sps":12845.0,"n_feature":1.0,"n_channel":3.0,"data":{"rms":{"X":8.899282026856554E-4,"Y":3.0311158468426244E-4,"Z":4.081027119857277E-4}}}
            tags = []

            gpio_state_str = ''.join(str(i) for i in self.current_gpio_state) if isinstance(self.current_gpio_state, list) else str(self.current_gpio_state)
            tag = self.rules_map.get(f"GPIOState-{gpio_state_str}", None)

            # Append tags to the message
            if tag:
                tags.append(tag)
            msg["tags"] = tags

            logger.debug(f"[FeatureTopic] Using gpio_state: {gpio_state_str}, Tag: {tag}")
            self.publish(msg)

        except Exception as e:
            logger.error("Error in feature_topic message: %s", e)
            traceback.print_exc()

    def _on_shadow_stream_event(self, event: SubscriptionResponseMessage):
        try:
            msg_str = event.binary_message.message.decode("utf-8")
            msg = json.loads(msg_str)
            logger.info(f"[ShadowTopic] Received shadow update: {msg}")
            self.current_gpio_state = msg.get("state", {}).get("reported", {}).get("gpio_state", [])
            logger.info(f"[ShadowTopic] Updated gpio_state: {self.current_gpio_state}")
        except Exception as e:
            logger.error("Error in shadow_topic message: %s", e)
            traceback.print_exc()

    def subscribe_shadow_topic(self):
        self.ipc_client.subscribe_to_topic(
            topic=f"$aws/things/{self.thing_name}/shadow/name/imPHMGPIOState/update/accepted",
            on_stream_event=self._on_shadow_stream_event,
            on_stream_error=self._on_stream_error,
            on_stream_closed=self._on_stream_closed
        )

    def subscribe_feature_topic(self):
        self.ipc_client.subscribe_to_topic(
            topic=self.feature_topic,
            on_stream_event=self._on_feature_stream_event,
            on_stream_error=self._on_stream_error,
            on_stream_closed=self._on_stream_closed
        )

    def publish(self, msg: dict):
        try:
            publish_message = PublishMessage(json_message=JsonMessage(message=msg))
            self.ipc_client.publish_to_topic_async(
                topic=self.annotated_topic,
                publish_message=publish_message
            )
            logger.debug(f"Published enriched message: {msg}")
        except Exception as e:
            logger.error("Failed to publish enriched message: %s", e)
            traceback.print_exc()

    def _on_stream_error(self, error: Exception) -> bool:
        logger.error("Stream error: %s", error)
        traceback.print_exc()
        return False

    def _on_stream_closed(self) -> None:
        logger.info("Subscription stream closed.")
