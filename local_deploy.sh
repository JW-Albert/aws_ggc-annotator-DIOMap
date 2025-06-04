#!/bin/bash
gdk component build
sudo /greengrass/v2/bin/greengrass-cli deployment create \
  --recipeDir $PWD/greengrass-build/recipes \
  --artifactDir $PWD/greengrass-build/artifacts \
  --merge "{COMPONENT_NAME}=1.0.0"