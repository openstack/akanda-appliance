# Copyright 2014 DreamHost, LLC
#
# Author: DreamHost, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from unittest2 import TestCase

import mock

from astara_router.drivers import hostname, ip

CONFIG = mock.Mock()
CONFIG.hostname = 'astara'
CONFIG.management_address = 'fdca:3ba5:a17a:acda:f816:3eff:fe66:33b6'


class HostnameTestCase(TestCase):
    """
    """
    def setUp(self):
        self.mock_execute = mock.patch('astara_router.utils.execute').start()
        self.mock_replace_file = mock.patch(
            'astara_router.utils.replace_file'
        ).start()
        self.addCleanup(mock.patch.stopall)

        self.mgr = hostname.HostnameManager()

    def test_update_hostname(self):
        self.mgr.update_hostname(CONFIG)
        self.mock_execute.assert_has_calls([
            mock.call(['hostname', 'astara'],
                      'sudo astara-rootwrap /etc/rootwrap.conf'),
            mock.call(['mv', '/tmp/hostname', '/etc/hostname'],
                      'sudo astara-rootwrap /etc/rootwrap.conf')
        ])

    def test_update_hosts(self):
        expected = mock.call('/tmp/hosts', '\n'.join([
            '127.0.0.1  localhost',
            '::1  localhost ip6-localhost ip6-loopback',
            'fdca:3ba5:a17a:acda:f816:3eff:fe66:33b6  astara'
        ]))
        self.mgr.update_hosts(CONFIG)
        self.mock_execute.assert_has_calls([
            mock.call(['mv', '/tmp/hosts', '/etc/hosts'],
                      'sudo astara-rootwrap /etc/rootwrap.conf')
        ])
        self.mock_replace_file.assert_has_calls([expected])
