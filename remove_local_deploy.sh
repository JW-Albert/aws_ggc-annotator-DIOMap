#!/bin/bash
sudo /greengrass/v2/bin/greengrass-cli \
    --ggcRootPath /greengrass/v2 deployment create \
    --remove "{COMPONENT_NAME}" \