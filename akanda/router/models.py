import abc
import os
import re

import netaddr


class ModelBase(object):
    __metaclass__ = abc.ABCMeta

    def __eq__(self, other):
        return type(self) == type(other) and vars(self) == vars(other)


class Interface(ModelBase):
    """
    """
    def __init__(self, ifname=None, addresses=[], groups=None, flags=None,
                 lladdr=None, mtu=1500, media=None, description=None,
                 **extra_params):
        self.ifname = ifname
        self.description = description
        self.addresses = addresses
        self.groups = groups or []
        self.flags = flags or []
        self.lladdr = lladdr
        self.mtu = mtu
        self.media = media
        self.extra_params = extra_params

    def __repr__(self):
        return '<Interface: %s %s>' % (self.ifname,
                                       [str(a) for a in self.addresses])

    def __eq__(self, other):
        """Check model equality only on limit fields."""
        return (type(self) == type(other) and
                self.ifname == other.ifname and
                self.addresses == other.addresses and
                self.description == other.description and
                self.mtu == other.mtu and
                self.groups == other.groups)

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        if not value:
            self._description = ''
        elif re.match('\w*$', value):
            self._description = value
        else:
            raise ValueError('Description must be chars from [a-zA-Z0-9_]')

    @property
    def addresses(self):
        return self._addresses

    @addresses.setter
    def addresses(self, value):
        self._addresses = [netaddr.IPNetwork(a) for a in value]

    @property
    def is_up(self):
        if ('state' in self.extra_params and
            self.extra_params['state'].lower() == 'up'):
            return 'UP'
        return 'UP' in self.flags

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def to_dict(self, extended=False):
        include = ['ifname', 'groups', 'mtu', 'lladdr', 'media']
        if extended:
            include.extend(['flags', 'extra_params'])
        retval = dict(
            [(k, v) for k, v in vars(self).iteritems() if k in include])
        retval['description'] = self.description
        retval['addresses'] = self.addresses
        retval['state'] = (self.is_up and 'up') or 'down'
        return retval


class FilterRule(ModelBase):
    """
    """
    def __init__(self, action=None, interface=None, family=None,
                 protocol=None, source=None, source_port=None,
                 destination_interface=None,
                 destination=None, destination_port=None,
                 redirect=None, redirect_port=None):

        self.action = action
        self.interface = interface
        self.family = family
        self.protocol = protocol
        self.source = source
        self.source_port = source_port
        self.destination_interface = destination_interface
        self.destination = destination
        self.destination_port = destination_port
        self.redirect = redirect
        self.redirect_port = redirect_port

    def __setattr__(self, name, value):
        if name != 'action' and not value:
            pass
        elif name == 'action':
            if value not in ('pass', 'block'):
                raise ValueError("Action must be 'pass' or 'block' not '%s'" %
                                 value)
        elif name in ('source', 'destination'):
            if '/' in value:
                value = netaddr.IPNetwork(value)
        elif name == 'redirect':
            value = netaddr.IPAddress(value)
        elif name.endswith('_port'):
            value = int(value)
        elif name == 'family':
            if value not in ('inet', 'inet6'):
                raise ValueError("Family must be 'inet', 'inet6', None and not"
                                 " %s" % value)
        elif name == 'protocol':
            if value not in ('tcp', 'udp', 'imcp'):
                raise ValueError("Protocol must be tcp|udp|imcp not '%s'." %
                                 value)

        super(FilterRule, self).__setattr__(name, value)

    @property
    def pf_rule(self):
        retval = [self.action]
        if self.interface:
            retval.append('on %s' % self.interface)
        if self.family:
            retval.append(self.family)
        if self.protocol:
            retval.append('proto %s' % self.protocol)
        if self.source or self.source_port:
            retval.append('from')
            if self.source:
                retval.append(str(self.source))
            if self.source_port:
                retval.append('port %s' % self.source_port)
        if (self.destination_interface
                or self.destination
                or self.destination_port):
            retval.append('to')
            if self.destination_interface:
                retval.append(self.destination_interface)
            if self.destination:
                retval.append(str(self.destination))
            if self.destination_port:
                retval.append('port %s' % self.destination_port)
        if self.redirect or self.redirect_port:
            retval.append('rdr-to')
            if self.redirect:
                retval.append(str(self.redirect))
            if self.redirect_port:
                retval.append('port %s' % self.redirect_port)
        return ' '.join(retval)

    @classmethod
    def from_dict(cls, d):
        return FilterRule(**d)


class Anchor(ModelBase):
    def __init__(self, name, rules=[]):
        self.name = name
        self.rules = rules

    @property
    def pf_rule(self):
        pf_rules = '\n\t'.join([r.pf_rule for r in self.rules])
        return "anchor %s {\n%s\n}\n" % (self.name, pf_rules)

    def external_pf_rule(self, base_dir):

        path = os.path.abspath(os.path.join(base_dir, self.name))
        return 'anchor %s\nload anchor %s from %s' % (self.name,
                                                      self.name,
                                                      path)


class AddressBookEntry(ModelBase):
    def __init__(self, name, cidrs=[]):
        self.name = name
        self.cidrs = cidrs

    @property
    def cidrs(self):
        return self._cidrs

    @cidrs.setter
    def cidrs(self, values):
        self._cidrs = [netaddr.IPNetwork(a) for a in values]

    @property
    def pf_rule(self):
        return 'table <%s> {%s}' % (self.name, ', '.join(map(str, self.cidrs)))

    def external_pf_rule(self, base_dir):
        path = os.path.abspath(os.path.join(base_dir, self.name))
        return 'table %s\npersist file "%s"' % (self.name,
                                                path)

    def external_table_data(self):
        return '\n'.join(map(str, self.cidrs))


class Allocation(ModelBase):
    def __init__(self, lladdr, ip_address, hostname):
        self.lladdr = lladdr
        self.ip_address = ip_address
        self.hostname = hostname


class StaticRoute(ModelBase):
    def __init__(self, destination, next_hop):
        self.destination = destination
        self.next_hop = next_hop

    @property
    def destination(self):
        return self._destination

    @destination.setter
    def destination(self, value):
        self._destination = netaddr.IPNetwork(value)

    @property
    def next_hop(self):
        return self._next_hop

    @next_hop.setter
    def next_hop(self, value):
        self._next_hop = netaddr.IPAddress(value)

    def to_dict(self):
        return dict(destination=self.destination, next_hop=self.next_hop)


class Network(ModelBase):
    STATIC = 'static'
    RA = 'ra'
    DHCP = 'dhcp'

    def __init__(self, id_, interface, name=None, external_access=False,
                 v4_conf_service=STATIC, v6_conf_service=STATIC,
                 address_allocations=[]):
        self.id = id_
        self.interface = interface
        self.name = name
        self.external_access = external_access
        self.v4_conf_service = v4_conf_service
        self.v6_conf_service = v6_conf_service
        self.address_allocations = address_allocations

    @property
    def v4_conf_service(self):
        return self._v4_conf_service

    @v4_conf_service.setter
    def v4_conf_service(self, value):
        if value not in (self.DHCP, self.STATIC):
            msg = ('v4_conf_service must be one of dhcp|static not (%s).' %
                   value)
            raise ValueError(msg)
        self._v4_conf_service = value

    @property
    def v6_conf_service(self):
        return self._v6_conf_service

    @v6_conf_service.setter
    def v6_conf_service(self, value):
        if value not in (self.DHCP, self.RA, self.STATIC):
            msg = ('v6_conf_service must be one of dhcp|ra|static not (%s).' %
                   value)
            raise ValueError(msg)
        self._v6_conf_service = value

    @classmethod
    def from_dict(cls, d):
        return cls(
            d['network_id'],
            name=d['name'],
            interface=Interface.from_dict(d['interface']),
            external_access=bool(d.get('external_access')),
            v6_conf_service=d.get('v6_conf_service', cls.STATIC),
            v4_conf_service=d.get('v4_conf_service', cls.STATIC),
            address_allocations=[Allocation(*a) for a in d['allocations']])


class Configuration(ModelBase):
    def __init__(self, conf_dict={}):
        self.networks = [Network.from_dict(n) for n in conf_dict['networks']]
        self.static_routes = [StaticRoute(*r) for r in
                              conf_dict.get('static_routes', [])]

        self.address_book = {}
        for name, cidrs in conf_dict.get('address_book', {}).iteritems():
            self.address_book[name] = AddressBookEntry(name, cidrs)

        self.anchors = [
            Anchor(a['name'], [FilterRule.from_dict(r) for r in a['rules']])
            for a in conf_dict.get('anchors', [])]

    def validate(self):
        """Validate anchor rules to ensure that ifaces and tables exist."""

        errors = []

        for anchor in self.anchors:
            for rule in anchor.rules:
                interfaces = set(n.interface.ifname for n in self.networks)
                for iface in (rule.interface, rule.destination_interface):
                    if iface and iface not in interfaces:
                        errors.append((rule, '%s does not exist' % iface))

                for address in (rule.source, rule.destination):
                    if not address or isinstance(address, netaddr.IPNetwork):
                        pass
                    elif address in self.address_book:
                        pass
                    else:
                        reason = '%s is not in the address book' % address
                        errors.append((rule, reason))

        self.errors = ["'%s' %s" % e for e in errors]
        return not bool(self.errors)

    def to_dict(self):
        fields = ('networks', 'address_book', 'anchors', 'static_routes')
        return dict((f, getattr(self, f)) for f in fields)
