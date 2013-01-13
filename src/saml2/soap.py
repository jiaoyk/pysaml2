#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011 Umeå University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Suppport for the client part of the SAML2.0 SOAP binding.
"""
import logging

from saml2 import create_class_from_element_tree
from saml2.samlp import NAMESPACE as SAMLP_NAMESPACE
from saml2.schema import soapenv

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    try:
        import cElementTree as ElementTree
    except ImportError:
        #noinspection PyUnresolvedReferences
        from elementtree import ElementTree


logger = logging.getLogger(__name__)

class XmlParseError(Exception):
    pass

class WrongMessageType(Exception):
    pass

def parse_soap_enveloped_saml_response(text):
    tags = ['{%s}Response' % SAMLP_NAMESPACE, 
            '{%s}LogoutResponse' % SAMLP_NAMESPACE]
    return parse_soap_enveloped_saml_thingy(text, tags)

def parse_soap_enveloped_saml_attribute_query(text):
    expected_tag = '{%s}AttributeQuery' % SAMLP_NAMESPACE
    return parse_soap_enveloped_saml_thingy(text, [expected_tag])

def parse_soap_enveloped_saml_logout_request(text):
    expected_tag = '{%s}LogoutRequest' % SAMLP_NAMESPACE
    return parse_soap_enveloped_saml_thingy(text, [expected_tag])

def parse_soap_enveloped_saml_authentication_request(text):
    expected_tag = '{%s}AuthenticationRequest' % SAMLP_NAMESPACE
    return parse_soap_enveloped_saml_thingy(text, [expected_tag])

def parse_soap_enveloped_saml_artifact_resolve(text):
    expected_tag = '{%s}ArtifactResolve' % SAMLP_NAMESPACE
    return parse_soap_enveloped_saml_thingy(text, [expected_tag])

def parse_soap_enveloped_saml_artifact_response(text):
    expected_tag = '{%s}ArtifactResponse' % SAMLP_NAMESPACE
    return parse_soap_enveloped_saml_thingy(text, [expected_tag])

def parse_soap_enveloped_saml_name_id_mapping_request(text):
    expected_tag = '{%s}NameIDMappingRequest' % SAMLP_NAMESPACE
    return parse_soap_enveloped_saml_thingy(text, [expected_tag])

def parse_soap_enveloped_saml_name_id_mapping_response(text):
    expected_tag = '{%s}NameIDMappingResponse' % SAMLP_NAMESPACE
    return parse_soap_enveloped_saml_thingy(text, [expected_tag])

#def parse_soap_enveloped_saml_logout_response(text):
#    expected_tag = '{%s}LogoutResponse' % SAMLP_NAMESPACE
#    return parse_soap_enveloped_saml_thingy(text, [expected_tag])

def parse_soap_enveloped_saml_thingy(text, expected_tags):
    """Parses a SOAP enveloped SAML thing and returns the thing as
    a string.
    
    :param text: The SOAP object as XML string
    :param expected_tags: What the tag of the SAML thingy is expected to be.
    :return: SAML thingy as a string
    """
    envelope = ElementTree.fromstring(text)

    assert envelope.tag == '{%s}Envelope' % soapenv.NAMESPACE
    
    assert len(envelope) >= 1
    body = None
    for part in envelope:
        if part.tag == '{%s}Body' % soapenv.NAMESPACE:
            assert len(part) == 1
            body = part
            break

    if body is None:
        return ""
    
    saml_part = body[0]
    if saml_part.tag in expected_tags:
        return ElementTree.tostring(saml_part, encoding="UTF-8")
    else:
        raise WrongMessageType("Was '%s' expected '%s'" % (saml_part.tag,
                                                            expected_tags))

import re

NS_AND_TAG = re.compile("\{([^}]+)\}(.*)")

def class_instances_from_soap_enveloped_saml_thingies(text, modules):
    """Parses a SOAP enveloped header and body SAML thing and returns the
    thing as a dictionary class instance.

    :param text: The SOAP object as XML
    :param modules: modules representing xsd schemas
    :return: SAML thingy as a class instance
    """
    try:
        envelope = ElementTree.fromstring(text)
    except Exception, exc:
        raise XmlParseError("%s" % exc)

    assert envelope.tag == '{%s}Envelope' % soapenv.NAMESPACE
    assert len(envelope) >= 1
    env = {"header":[], "body":None}
    
    for part in envelope:
        if part.tag == '{%s}Body' % soapenv.NAMESPACE:
            assert len(part) == 1
            m = NS_AND_TAG.match(part[0].tag)
            ns,tag = m.groups()
            for module in modules:
                if module.NAMESPACE == ns:
                    try:
                        target = module.ELEMENT_BY_TAG[tag]
                        env["body"] = create_class_from_element_tree(target,
                                                                     part[0])
                    except KeyError:
                        continue
        elif part.tag == "{%s}Header" % soapenv.NAMESPACE:
            for item in part:
                m = NS_AND_TAG.match(item.tag)
                ns,tag = m.groups()
                for module in modules:
                    if module.NAMESPACE == ns:
                        try:
                            target = module.ELEMENT_BY_TAG[tag]
                            env["header"].append(create_class_from_element_tree(
                                                                    target,
                                                                    item))
                        except KeyError:
                            continue

    return env

def make_soap_enveloped_saml_thingy(thingy, headers=None):
    """ Returns a soap envelope containing a SAML request
    as a text string.
    
    :param thingy: The SAML thingy
    :return: The SOAP envelope as a string
    """
    soap_envelope = soapenv.Envelope()

    if headers:
        _header = soapenv.Header()
        _header.add_extension_elements(headers)
        soap_envelope.header = _header

    soap_envelope.body = soapenv.Body()
    soap_envelope.body.add_extension_element(thingy)

    return "%s" % soap_envelope

def soap_fault(message=None, actor=None, code=None, detail=None):
    """ Create a SOAP Fault message

    :param message: Human readable error message
    :param actor: Who discovered the error
    :param code: Error code
    :param detail: More specific error message
    :return: A SOAP Fault message as a string
    """
    _string = _actor = _code = _detail = None

    if message:
        _string = soapenv.Fault_faultstring(text=message)
    if actor:
        _actor = soapenv.Fault_faultactor(text=actor)
    if code:
        _code = soapenv.Fault_faultcode(text=code)
    if detail:
        _detail = soapenv.Fault_detail(text=detail)

    fault = soapenv.Fault(
        faultcode=_code,
        faultstring=_string,
        faultactor=_actor,
        detail=_detail,
    )

    return "%s" % fault
