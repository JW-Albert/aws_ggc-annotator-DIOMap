#!/usr/bin/env python3

import argparse
import json
import logging
import sys
import traceback
import time
import re

from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

from dio_map import DIOMap

logger = logging.getLogger(__name__)

def configure_logging(log_level: str):
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(stream=sys.stdout, level=level)
    logger.setLevel(level)

def fix_and_parse_rules(raw: str):
    # 加 key 的雙引號
    fixed = re.sub(r'(\b\w+\b)\s*:', r'"\1":', raw)
    # 加 value 的雙引號（忽略數字與 true/false/null）
    fixed = re.sub(r':\s*([a-zA-Z_][\w\-]*)', r':"\1"', fixed)
    return json.loads(fixed)

def main():
    parser = argparse.ArgumentParser(description="DIOMap Greengrass component")

    parser.add_argument("--thing-name",
                        type=str,
                        required=True,
                        help="Greengrass Thing name")

    parser.add_argument("--shadow-name",
                        type=str,
                        required=True,
                        help="Greengrass shadow name")

    parser.add_argument("--log-level",
                        type=str,
                        default="INFO",
                        help="Log level (default: INFO)")

    parser.add_argument("--annotated-feature-topic",
                        type=str,
                        required=True,
                        help="Topic to publish annotated messages")
    
    parser.add_argument("--feature-topic",
                        type=str,
                        required=True,
                        help="Feature topic to subscribe to")

    parser.add_argument("--rules",
                        type=str,
                        required=True,
                        help="Rules JSON string, e.g., '[{\"name\": \"GPIOState-1111\", \"label\": \"running\"}]'")

    args = parser.parse_args()

    configure_logging(args.log_level)

    try:
        # 設定與初始化
        ipc_client = GreengrassCoreIPCClientV2()
        rules = fix_and_parse_rules(args.rules)
        dio_map = DIOMap(ipc_client, args.thing_name , args.shadow_name, args.feature_topic, args.annotated_feature_topic, rules)

        # 初始化 GPIO 狀態
        dio_map.init_shadow_state()
        logger.info(f"Initial GPIO state: {dio_map.current_gpio_state}")

        # 訂閱 shadow 變更
        dio_map.subscribe_shadow_topic()
        logger.info(f"Subscribed to shadow topic: {args.shadow_name}")

        # 訂閱 feature
        dio_map.subscribe_feature_topic()
        logger.info(f"Subscribed to feature topic: {args.feature_topic}")

        # Prevent exit to keep subscription alive
        while True:
            time.sleep(10) # 一定要加，不然 CPU 會爆掉 (主程式沒做事就可以休息久一點)

    except Exception as e:
        logger.error("Fatal error: %s", e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
