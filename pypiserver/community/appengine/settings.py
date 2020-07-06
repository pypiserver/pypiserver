"""Stores main configurations for the app engine pypiserver plugin"""

import os


class GlobalSettings:
    """Main plugin configuration attributes.

    Attributes: 
        TIER: dev / staging / production,
        LOCAL_DIRECTORY: name of the folder containing repository contents locally
        REMOTE_DIRECTORY: name of the folder containing repository files remotely

    Environmental variables:
        TIER: reading tier is used to set the application tier
        LOCAL_PACKAGE_DIRECTORY: to retrieve the LOCAL_DIRECTORY
        REMOTE_PACKAGE_DIRECTORY: to retrieve the REMOTE_DIRECTORY
    """
    DEV_TIER = "dev"
    TIER = os.getenv("TIER", DEV_TIER)
    RUNNING_DEV = TIER == DEV_TIER

    LOCAL_DIRECTORY = os.getenv(
        "LOCAL_PACKAGE_DIRECTORY", "./packages" if RUNNING_DEV else "/tmp")
    REMOTE_DIRECTORY = os.getenv(
        "REMOTE_PACKAGE_DIRECTORY", "./.remote_packages" if RUNNING_DEV else "/packages")
