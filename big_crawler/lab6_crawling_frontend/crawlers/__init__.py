"""This module defines a abstract crawler class and specialized children.

The `BasePlugin` is contained in `plugin.py` and is the abstract class,
every other class inherits from.

Author: Johannes Müller <j.mueller@reply.de>
"""

from . import eurlex, search, bafin, eba, buba_notifications, buba_circular

__all__ = [eurlex.EurlexPlugin,
           search.SearchPlugin,
           bafin.BafinPlugin,
           eba.EBAPlugin,
           buba_notifications.BubaNotificationsPlugin,
           buba_circular.BubaCircularPlugin]
