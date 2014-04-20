from __future__ import unicode_literals, print_function
import six
from contextlib import contextmanager
from xml.etree import ElementTree as etree


CNAME_TAGS = ('system-out',)
CNAME_PATTERN = '<![CDATA[{}]]>'
TAG_PATTERN = '<{tag}>{content}</{tag}>'


@contextmanager
def patch_etree_cname(etree):
    """
    Patch ElementTree's _serialize_xml function so that it will
    write text as CDATA tag for tags tags defined in CNAME_TAGS.

    >>> import re
    >>> from xml.etree import ElementTree
    >>> xml_string = '''
    ... <testsuite name="nosetests" tests="1" errors="0" failures="0" skip="0">
    ...     <testcase classname="some.class.Foo" name="test_foo" time="0.001">
    ...         <system-out>Some output here</system-out>
    ...     </testcase>
    ... </testsuite>
    ... '''
    >>> tree = ElementTree.fromstring(xml_string)
    >>> with patch_etree_cname(ElementTree):
    ...    saved = ElementTree.tostring(tree)
    >>> found = re.findall(r'<system-out>(.*?)</system-out>', saved)[0]
    >>> print(found)
    <![CDATA[Some output here]]>
    """
    original_serialize = etree._serialize_xml

    def _serialize_xml(write, elem, encoding, qnames, namespaces):
        if elem.tag in CNAME_TAGS:
            write(TAG_PATTERN.format(tag=elem.tag,
                                     content=CNAME_PATTERN.format(elem.text)))
        else:
            original_serialize(write, elem, encoding, qnames, namespaces)

    etree._serialize_xml = etree._serialize['xml'] = _serialize_xml

    yield

    etree._serialize_xml = etree._serialize['xml'] = original_serialize


def merge_trees(*trees):
    """
    Merge all given XUnit ElementTrees into a single ElementTree.
    This combines all of the children test-cases and also merges
    all of the metadata of how many tests were executed, etc.
    """
    first_tree = trees[0]
    first_root = first_tree.getroot()

    if len(trees) == 0:
        return first_tree

    for tree in trees[1:]:
        root = tree.getroot()

        # append children elements (testcases)
        first_root.extend(root.getchildren())

        # combine root attributes which stores the number
        # of executed tests, skipped tests, etc
        for key, value in first_root.attrib.items():
            if not value.isdigit():
                continue
            combined = six.text_type(int(value) + int(root.attrib.get(key, '0')))
            first_root.set(key, combined)

    return first_tree


def merge_xunit(files, output):
    """
    Merge the given xunit xml files into a single output xml file.
    """
    trees = []

    for f in files:
        trees.append(etree.parse(f))

    merged = merge_trees(*trees)

    with patch_etree_cname(etree):
        merged.write(output, encoding='utf-8', xml_declaration=True)
