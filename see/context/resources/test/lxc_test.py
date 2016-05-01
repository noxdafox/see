import mock
import libvirt
import difflib
import unittest

from see.context.resources import lxc


def compare(text1, text2):
    """Utility function for comparing text and returining differences."""
    diff = difflib.ndiff(text1.splitlines(True), text2.splitlines(True))
    return '\n' + '\n'.join(diff)


class DomainXMLTest(unittest.TestCase):
    def test_domain_xml(self):
        """XML with no network and no filesystem."""
        config = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices /></domain>"""
        results = lxc.domain_xml('foo', config, [])
        self.assertEqual(results, expected, compare(results, expected))

    def test_domain_xml_filesystem(self):
        """XML with filesystem."""
        config = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><filesystem type="mount">""" +\
                   """<source dir="foo" /><target dir="bar" /></filesystem></devices></domain>"""
        results = lxc.domain_xml('foo', config, [('foo', 'bar')])
        self.assertEqual(results, expected, compare(results, expected))

    def test_domain_xml_modifies(self):
        """Fields are modified if existing."""
        config = """<domain><name>bar</name><uuid>bar</uuid></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><filesystem type="mount">""" +\
                   """<source dir="foo" /><target dir="bar" /></filesystem></devices></domain>"""
        results = lxc.domain_xml('foo', config, [('foo', 'bar')])
        self.assertEqual(results, expected, compare(results, expected))

    def test_domain_xml_network(self):
        """XML with network fields are modified if existing."""
        config = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><filesystem type="mount">""" +\
                   """<source dir="foo" /><target dir="bar" /></filesystem><interface type="network">""" +\
                   """<source network="foo" /></interface></devices></domain>"""
        results = lxc.domain_xml('foo', config, [('foo', 'bar')], network_name='foo')
        self.assertEqual(results, expected, compare(results, expected))

    def test_domain_xml_network_modifies(self):
        """XML with network."""
        config = """<domain><devices><interface type="network">""" +\
                 """<source network="bar"/></interface></devices></domain>"""
        expected = """<domain><devices><interface type="network"><source network="foo" /></interface>""" +\
                   """<filesystem type="mount"><source dir="foo" /><target dir="bar" /></filesystem>""" +\
                   """</devices><name>foo</name><uuid>foo</uuid></domain>"""
        results = lxc.domain_xml('foo', config, [('foo', 'bar')], network_name='foo')
        self.assertEqual(results, expected, compare(results, expected))


class DomainCreateTest(unittest.TestCase):
    def test_create(self):
        """Create with no network and no filesystem."""
        xml = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices /></domain>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        with mock.patch('see.context.resources.lxc.open', mock.mock_open(read_data=xml), create=True):
            lxc.domain_create(hypervisor, 'foo', {'configuration': '/foo'})
        results = hypervisor.defineXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))

    def test_create_filesystem(self):
        """Create with single filesystem."""
        xml = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><filesystem type="mount">""" +\
                   """<source dir="/bar/foo" /><target dir="/baz" /></filesystem></devices></domain>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        with mock.patch('see.context.resources.lxc.open', mock.mock_open(read_data=xml), create=True):
            with mock.patch('see.context.resources.lxc.os.makedirs'):
                lxc.domain_create(hypervisor, 'foo', {'configuration': '/foo', 'filesystem':
                                                      {'source_path': '/bar',
                                                       'target_path': '/baz'}})
        results = hypervisor.defineXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))

    def test_create_filesystems(self):
        """Create with multiple filesystem."""
        xml = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><filesystem type="mount">""" +\
                   """<source dir="/bar/foo" /><target dir="/baz" /></filesystem><filesystem type="mount">""" +\
                   """<source dir="/dead/foo" /><target dir="/beef" /></filesystem></devices></domain>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        with mock.patch('see.context.resources.lxc.open', mock.mock_open(read_data=xml), create=True):
            with mock.patch('see.context.resources.lxc.os.makedirs'):
                lxc.domain_create(hypervisor, 'foo', {'configuration': '/foo', 'filesystem':
                                                      [{'source_path': '/bar',
                                                        'target_path': '/baz'},
                                                       {'source_path': '/dead',
                                                        'target_path': '/beef'}]})
        results = hypervisor.defineXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))

    def test_create_network(self):
        """Create with network."""
        xml = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><filesystem type="mount">""" +\
                   """<source dir="/bar/foo" /><target dir="/baz" /></filesystem><interface type="network">""" +\
                   """<source network="foo" /></interface></devices></domain>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        with mock.patch('see.context.resources.lxc.open', mock.mock_open(read_data=xml), create=True):
            with mock.patch('see.context.resources.lxc.os.makedirs'):
                lxc.domain_create(hypervisor, 'foo', {'configuration': '/foo', 'filesystem':
                                                      {'source_path': '/bar',
                                                       'target_path': '/baz'}}, network_name='foo')
        results = hypervisor.defineXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))


class DomainDelete(unittest.TestCase):
    def test_delete_destroy(self):
        """Domain is destroyed if active."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = True
        lxc.domain_delete(domain, logger, None)
        self.assertTrue(domain.destroy.called)

    def test_delete_destroy_error(self):
        """Domain destroy raises error."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = True
        domain.destroy.side_effect = libvirt.libvirtError("BOOM")
        lxc.domain_delete(domain, logger, None)
        self.assertTrue(domain.undefine.called)

    def test_delete_undefine(self):
        """Domain is undefined."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = False
        lxc.domain_delete(domain, logger, None)
        self.assertTrue(domain.undefine.called)

    @mock.patch('see.context.resources.lxc.os.path.exists')
    def test_delete_undefine_error(self, os_mock):
        """Domain undefine raises error."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = False
        domain.undefine.side_effect = libvirt.libvirtError("BOOM")
        lxc.domain_delete(domain, logger, '/foo/bar/baz')
        self.assertTrue(os_mock.called)

    @mock.patch('see.context.resources.lxc.shutil.rmtree')
    @mock.patch('see.context.resources.lxc.os.path.exists')
    def test_delete_filesystem(self, os_mock, rm_mock):
        """Domain is undefined."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = False
        os_mock.return_value = True
        lxc.domain_delete(domain, logger, 'foo/bar/baz')
        rm_mock.assert_called_with('foo/bar/baz')


class ResourcesTest(unittest.TestCase):
    @mock.patch('see.context.resources.network.lookup')
    @mock.patch('see.context.resources.lxc.libvirt')
    @mock.patch('see.context.resources.lxc.domain_create')
    def test_initialize_default(self, create_mock, libvirt_mock,
                                network_lookup_mock):
        """Resources initializer with no extra value."""
        resources = lxc.LXCResources('foo', {'domain': 'bar'})
        libvirt_mock.open.assert_called_with('lxc:///')
        create_mock.assert_called_with(resources.hypervisor, 'foo', 'bar', network_name=None)

    @mock.patch('see.context.resources.network.lookup')
    @mock.patch('see.context.resources.lxc.libvirt')
    @mock.patch('see.context.resources.lxc.domain_create')
    def test_initialize_hypervisor(self, create_mock, libvirt_mock,
                                   network_lookup_mock):
        """Resources initializer with hypervisor."""
        resources = lxc.LXCResources('foo', {'domain': 'bar', 'hypervisor': 'baz'})
        libvirt_mock.open.assert_called_with('baz')
        create_mock.assert_called_with(resources.hypervisor, 'foo', 'bar', network_name=None)

    @mock.patch('see.context.resources.lxc.libvirt')
    @mock.patch('see.context.resources.lxc.network')
    @mock.patch('see.context.resources.lxc.domain_create')
    def test_initialize_network(self, create_mock, network_mock, libvirt_mock):
        """Resources initializer with network."""
        network = mock.Mock()
        network.name.return_value = 'baz'
        network_mock.lookup = mock.Mock()
        network_mock.create.return_value = network

        resources = lxc.LXCResources('foo', {'domain': 'bar',
                                             'network': 'baz',
                                             'disk': {'image': '/foo/bar'}})
        network_mock.create.assert_called_with(resources.hypervisor, 'foo', 'baz')
        create_mock.assert_called_with(resources.hypervisor, 'foo', 'bar',
                                       network_name='baz')

    @mock.patch('see.context.resources.lxc.libvirt')
    @mock.patch('see.context.resources.lxc.domain_create')
    @mock.patch('see.context.resources.network.lookup')
    @mock.patch('see.context.resources.network.delete')
    @mock.patch('see.context.resources.lxc.domain_delete')
    def test_cleanup_no_creation(self, delete_mock, network_delete_mock,
                                 network_lookup_mock, create_mock,
                                 libvirt_mock):
        """Resources are released on cleanup. Network not created"""
        resources = lxc.LXCResources('foo', {'domain': 'bar'})
        resources._domain = mock.Mock()
        resources._network = mock.Mock()
        resources._hypervisor = mock.Mock()
        resources.cleanup()
        delete_mock.assert_called_with(resources.domain, mock.ANY, None)
        self.assertFalse(network_delete_mock.called)
        self.assertTrue(resources._hypervisor.close.called)

    @mock.patch('see.context.resources.lxc.libvirt')
    @mock.patch('see.context.resources.lxc.domain_create')
    @mock.patch('see.context.resources.network.lookup')
    @mock.patch('see.context.resources.network.delete')
    @mock.patch('see.context.resources.lxc.domain_delete')
    def test_cleanup_creation(self, delete_mock, network_delete_mock,
                              network_lookup_mock, create_mock, libvirt_mock):
        """Resources are released on cleanup. Network created"""
        resources = lxc.LXCResources('foo', {'domain': 'bar',
                                             'network': {}})
        resources._domain = mock.Mock()
        resources._network = mock.Mock()
        resources._hypervisor = mock.Mock()
        resources.cleanup()
        delete_mock.assert_called_with(resources.domain, mock.ANY, None)
        network_delete_mock.assert_called_with(resources.network)
        self.assertTrue(resources._hypervisor.close.called)

    @mock.patch('see.context.resources.lxc.libvirt')
    @mock.patch('see.context.resources.lxc.domain_create')
    @mock.patch('see.context.resources.network.lookup')
    @mock.patch('see.context.resources.network.delete')
    @mock.patch('see.context.resources.lxc.domain_delete')
    def test_cleanup_filesystem(self, delete_mock, network_delete_mock,
                                network_lookup_mock, create_mock, libvirt_mock):
        """Shared folder is cleaned up."""
        resources = lxc.LXCResources('foo', {'domain': 'bar', 'filesystem':
                                             {'source_path': '/bar',
                                              'target_path': '/baz'}})
        resources._domain = mock.Mock()
        resources._network = mock.Mock()
        resources._hypervisor = mock.Mock()
        resources.cleanup()
        delete_mock.assert_called_with(resources.domain, mock.ANY, '/bar/foo')
