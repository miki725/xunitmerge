from __future__ import unicode_literals, print_function
from contextlib import contextmanager
from xml.etree import ElementTree as etree
from xml.sax.saxutils import quoteattr

import six


CNAME_TAGS = ('system-out', 'system-err', 'skipped', 'error', 'failure')
CNAME_PATTERN = '<![CDATA[{}]]>'
TAG_PATTERN = '<{tag}{attrs}>{text}</{tag}>'


@contextmanager
def patch_etree_cname(etree):
    """
    Patch ElementTree's _serialize_xml function so that it will
    write text as CDATA tag for tags tags defined in CNAME_TAGS.

    >>> import re
    >>> from xml.etree import ElementTree
    >>> xml_string = '''
    ... <testsuite name="nosetests" tests="1" errors="0" failures="0" skip="0">
    ...     <testcase classname="some.class.Foo" name="test_system_out" time="0.001">
    ...         <system-out>Some output here</system-out>
    ...     </testcase>
    ...     <testcase classname="some.class.Foo" name="test_skipped" time="0.001">
    ...         <skipped type="unittest.case.SkipTest" message="Skipped">Skipped</skipped>
    ...     </testcase>
    ...     <testcase classname="some.class.Foo" name="test_error" time="0.001">
    ...         <error type="KeyError" message="Error here">Error here</error>
    ...     </testcase>
    ...     <testcase classname="some.class.Foo" name="test_failure" time="0.001">
    ...         <failure type="AssertionError" message="Failure here">Failure here</failure>
    ...     </testcase>
    ... </testsuite>
    ... '''
    >>> tree = ElementTree.fromstring(xml_string)
    >>> with patch_etree_cname(ElementTree):
    ...    saved = str(ElementTree.tostring(tree))
    >>> systemout = re.findall(r'(<system-out>.*?</system-out>)', saved)[0]
    >>> print(systemout)
    <system-out><![CDATA[Some output here]]></system-out>
    >>> skipped = re.findall(r'(<skipped.*?</skipped>)', saved)[0]
    >>> print(skipped)
    <skipped message="Skipped" type="unittest.case.SkipTest"><![CDATA[Skipped]]></skipped>
    >>> error = re.findall(r'(<error.*?</error>)', saved)[0]
    >>> print(error)
    <error message="Error here" type="KeyError"><![CDATA[Error here]]></error>
    >>> failure = re.findall(r'(<failure.*?</failure>)', saved)[0]
    >>> print(failure)
    <failure message="Failure here" type="AssertionError"><![CDATA[Failure here]]></failure>
    """
    original_serialize = etree._serialize_xml

    def _serialize_xml(write, elem, *args, **kwargs):
        if elem.tag in CNAME_TAGS:
            attrs = ' '.join(
                ['{}={}'.format(k, quoteattr(v))
                 for k, v in sorted(elem.attrib.items())]
            )
            attrs = ' ' + attrs if attrs else ''
            text = CNAME_PATTERN.format(elem.text)
            content = TAG_PATTERN.format(
                tag=elem.tag,
                attrs=attrs,
                text=text
            )
            if six.PY3:
                pass
            else:
                # ensure py2 's encoding
                content = content.encode('utf-8')
            write(content)
        else:
            original_serialize(write, elem, *args, **kwargs)

    etree._serialize_xml = etree._serialize['xml'] = _serialize_xml

    yield

    etree._serialize_xml = etree._serialize['xml'] = original_serialize


def merge_trees(*trees):
    """
    Merge all given XUnit ElementTrees into a single ElementTree.
    This combines all of the children test-cases and also merges
    all of the metadata of how many tests were executed, etc.
    """
    def collecter():
        while True:
            elem = yield
            if not len(elem):
                return
            for key in stats.keys():
                value = elem.attrib.get(key)
                if value:
                    stats[key] = float(value) + float(stats.get(key, 0))
                    if key != 'time':
                        stats[key] = int(stats[key])

    if len(trees) == 1:
        return trees[0]

    merged_root = etree.Element('testsuites')
    merged_tree = etree.ElementTree(merged_root)

    stats = {
        'tests': 0,
        'disabled': 0,
        'skipped': 0,
        'failures': 0,
        'errors': 0,
        'time': 0
    }

    for tree in trees:
        root = tree.getroot()
        merged_root.extend(root.getchildren())

    c = collecter()
    next(c)
    for child in merged_root.getchildren():
        c.send(child)
    c.close()

    for key, value in stats.items():
        merged_root.set(key, six.text_type(value))

    try:
        del merged_root.attrib['name']
    except KeyError:
        pass

    return merged_tree


def merge_xunit(files, output, callback=None):
    """
    Merge the given xunit xml files into a single output xml file.

    If callback is not None, it will be called with the merged ElementTree
    before the output file is written (useful for applying other fixes to
    the merged file). This can either modify the element tree in place (and
    return None) or return a completely new ElementTree to be written.
    """
    trees = [etree.parse(f) for f in files]

    merged = merge_trees(*trees)

    if callback is not None:
        result = callback(merged)
        if result is not None:
            merged = result

    with patch_etree_cname(etree):
        merged.write(output, encoding='utf-8', xml_declaration=True)
