# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Name:         mei/test_main.py
# Purpose:      Tests for mei/base.py
#
# Authors:      Christopher Antila
#
# Copyright:    Copyright © 2014 Michael Scott Cuthbert and the music21 Project
# License:      LGPL or BSD, see license.txt
#------------------------------------------------------------------------------
'''
Tests for :mod:`music21.mei.base`.
'''

# part of the whole point is to test protect things too
# pylint: disable=protected-access

# this often happens on TestCase subclasses
# pylint: disable=too-many-public-methods

# a test that uses only assertions on the Mocks will have no-self-use
# pylint: disable=no-self-use

# if we mock many things, this may be triggered
# pylint: disable=too-many-arguments

# pylint is bad at guessing types in these tests---reasonably so
# pylint: disable=maybe-no-member

import unittest
try:
    # this works in Python 3.3+
    from unittest import mock  # pylint: disable=no-name-in-module
except ImportError:
    try:
        # system library overrides the built-in
        import mock
    except ImportError:
        # last resort
        from music21.ext import mock

# To have working MagicMock objects, we can't use cElementTree even though it would be faster.
# The C implementation provides some methods/attributes dynamically (notably "tag"), so MagicMock
# won't know to mock them, and raises an exception instead.
from xml.etree import ElementTree as ETree

from collections import defaultdict
from fractions import Fraction

from music21 import articulations
from music21 import bar
from music21 import clef
from music21 import duration
from music21 import instrument
from music21 import interval
from music21 import key
from music21 import meter
from music21 import note
from music21 import pitch
from music21 import spanner
from music21 import stream
from music21 import tie

from music21.ext import six
from six.moves import xrange  # pylint: disable=redefined-builtin,import-error,unused-import
from six.moves import range  # pylint: disable=redefined-builtin,import-error,unused-import

# Importing from base.py
import music21.mei.base as base
from music21.mei.base import _XMLID
from music21.mei.base import _MEINS


class TestMeiToM21Class(unittest.TestCase):
    '''Tests for the MeiToM21Converter class.'''

    def testInit1(self):
        '''__init__(): no argument gives an "empty" MeiToM21Converter instance'''
        actual = base.MeiToM21Converter()
        self.assertIsNotNone(actual.documentRoot)
        self.assertIsInstance(actual.m21Attr, defaultdict)
        self.assertIsInstance(actual.slurBundle, spanner.SpannerBundle)

    def testInit2(self):
        '''__init__(): a valid MEI file is prepared properly'''
        inputFile = '''<?xml version="1.0" encoding="UTF-8"?>
                       <mei xmlns="http://www.music-encoding.org/ns/mei" meiversion="2013">
                       <music><score></score></music></mei>'''
        actual = base.MeiToM21Converter(inputFile)
        # NB: at first I did this:
        # self.assertIsInstance(actual.documentRoot, ETree.Element)
        # ... but that doesn't work in Python 2, and I couldn't figure out why.
        self.assertIsNotNone(actual.documentRoot)
        self.assertEqual('{}mei'.format(_MEINS), actual.documentRoot.tag)
        self.assertIsInstance(actual.m21Attr, defaultdict)
        self.assertIsInstance(actual.slurBundle, spanner.SpannerBundle)

    def testInit3(self):
        '''__init__(): an invalid XML file causes an MeiValidityError'''
        inputFile = 'this is not an XML file'
        self.assertRaises(base.MeiValidityError, base.MeiToM21Converter, inputFile)
        try:
            base.MeiToM21Converter(inputFile)
        except base.MeiValidityError as theError:
            self.assertEqual(base._INVALID_XML_DOC, theError.args[0])

    def testInit4(self):
        '''__init__(): a MusicXML file causes an MeiElementError'''
        inputFile = '''<?xml version="1.0" encoding="UTF-8"?>
                       <!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 2.0 Partwise//EN"
                                                       "http://www.musicxml.org/dtds/partwise.dtd">
                       <score-partwise></score-partwise>'''
        self.assertRaises(base.MeiElementError, base.MeiToM21Converter, inputFile)
        try:
            base.MeiToM21Converter(inputFile)
        except base.MeiElementError as theError:
            self.assertEqual(base._WRONG_ROOT_ELEMENT.format('score-partwise'), theError.args[0])


#------------------------------------------------------------------------------
class TestThings(unittest.TestCase):
    '''Tests for utility functions.'''

    def testSafePitch1(self):
        '''safePitch(): when ``name`` is a valid pitch name'''
        name = 'D#6'
        expected = pitch.Pitch('D#6')
        actual = base.safePitch(name)
        self.assertEqual(expected.name, actual.name)
        self.assertEqual(expected.accidental, actual.accidental)
        self.assertEqual(expected.octave, actual.octave)

    def testSafePitch2(self):
        '''safePitch(): when ``name`` is not a valid pitch name'''
        name = ''
        expected = pitch.Pitch()
        actual = base.safePitch(name)
        self.assertEqual(expected.name, actual.name)
        self.assertEqual(expected.accidental, actual.accidental)
        self.assertEqual(expected.octave, actual.octave)

    def testSafePitch3(self):
        '''safePitch(): when ``name`` is not given, but there are various kwargs'''
        expected = pitch.Pitch('D#6')
        actual = base.safePitch(name='D', accidental='#', octave='6')
        self.assertEqual(expected.name, actual.name)
        self.assertEqual(expected.accidental, actual.accidental)
        self.assertEqual(expected.octave, actual.octave)

    def testSafePitch4(self):
        '''safePitch(): when 2nd argument is None'''
        expected = pitch.Pitch('D6')
        actual = base.safePitch(name='D', accidental=None, octave='6')
        self.assertEqual(expected.name, actual.name)
        self.assertEqual(expected.accidental, actual.accidental)
        self.assertEqual(expected.octave, actual.octave)

    def testAllPartsPresent1(self):
        '''allPartsPresent(): one <staffDef>, no repeats'''
        staffDefs = [mock.MagicMock(spec_set=ETree.Element)]
        staffDefs[0].get = mock.MagicMock(return_value='1')
        elem = mock.MagicMock(spec_set=ETree.Element)
        elem.findall = mock.MagicMock(return_value=staffDefs)
        expected = ['1']
        actual = base.allPartsPresent(elem)
        self.assertSequenceEqual(expected, actual)

    def testAllPartsPresent2(self):
        '''allPartsPresent(): four <staffDef>s'''
        staffDefs = [mock.MagicMock(spec_set=ETree.Element) for _ in xrange(4)]
        for i in xrange(4):
            staffDefs[i].get = mock.MagicMock(return_value=str(i + 1))
        elem = mock.MagicMock(spec_set=ETree.Element)
        elem.findall = mock.MagicMock(return_value=staffDefs)
        expected = list('1234')
        actual = base.allPartsPresent(elem)
        self.assertSequenceEqual(expected, actual)

    def testAllPartsPresent3(self):
        '''allPartsPresent(): four unique <staffDef>s, several repeats'''
        staffDefs = [mock.MagicMock(spec_set=ETree.Element) for _ in xrange(12)]
        for i in xrange(12):
            staffDefs[i].get = mock.MagicMock(return_value=str((i % 4) + 1))
        elem = mock.MagicMock(spec_set=ETree.Element)
        elem.findall = mock.MagicMock(return_value=staffDefs)
        expected = list('1234')
        actual = base.allPartsPresent(elem)
        self.assertSequenceEqual(expected, actual)

    def testAllPartsPresent4(self):
        '''allPartsPresent(): error: no <staffDef>s'''
        elem = mock.MagicMock(spec_set=ETree.Element)
        self.assertRaises(base.MeiValidityError, base.allPartsPresent, elem)
        try:
            base.allPartsPresent(elem)
        except base.MeiValidityError as mvErr:
            self.assertEqual(base._SEEMINGLY_NO_PARTS, mvErr.args[0])

    def testTimeSigFromAttrs(self):
        '''_timeSigFromAttrs(): that it works (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'meter.count': '3', 'meter.unit': '8'})
        expectedRatioString = '3/8'
        actual = base._timeSigFromAttrs(elem)
        self.assertEqual(expectedRatioString, actual.ratioString)

    def testKeySigFromAttrs1(self):
        '''_keySigFromAttrs(): using @key.pname, @key.accid, and @key.mode (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'key.pname': 'B', 'key.accid': 'f',
                                                      'key.mode': 'minor'})
        expectedTPNWC = 'b-'
        actual = base._keySigFromAttrs(elem)
        self.assertIsInstance(actual, key.Key)
        self.assertEqual(expectedTPNWC, actual.tonicPitchNameWithCase)

    def testKeySigFromAttrs2(self):
        '''_keySigFromAttrs(): using @key.sig, and @key.mode (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'key.sig': '6s', 'key.mode': 'minor'})
        expectedSharps = 6
        expectedMode = 'minor'
        actual = base._keySigFromAttrs(elem)
        self.assertIsInstance(actual, key.KeySignature)
        self.assertEqual(expectedSharps, actual.sharps)
        self.assertEqual(expectedMode, actual.mode)

    def testTranspositionFromAttrs1(self):
        '''_transpositionFromAttrs(): descending transposition (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'trans.semi': '-3', 'trans.diat': '-2'})
        expectedName = 'm-3'
        actual = base._transpositionFromAttrs(elem)
        self.assertIsInstance(actual, interval.Interval)
        self.assertEqual(expectedName, actual.directedName)

    def testTranspositionFromAttrs2(self):
        '''_transpositionFromAttrs(): ascending transposition (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'trans.semi': '7', 'trans.diat': '4'})
        expectedName = 'P5'
        actual = base._transpositionFromAttrs(elem)
        self.assertIsInstance(actual, interval.Interval)
        self.assertEqual(expectedName, actual.directedName)

    def testTranspositionFromAttrs3(self):
        '''_transpositionFromAttrs(): large ascending interval (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'trans.semi': '19', 'trans.diat': '11'})
        expectedName = 'P12'
        actual = base._transpositionFromAttrs(elem)
        self.assertIsInstance(actual, interval.Interval)
        self.assertEqual(expectedName, actual.directedName)

    def testTranspositionFromAttrs4(self):
        '''_transpositionFromAttrs(): alternate octave spec (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'trans.semi': '12', 'trans.diat': '0'})
        expectedName = 'P8'
        actual = base._transpositionFromAttrs(elem)
        self.assertIsInstance(actual, interval.Interval)
        self.assertEqual(expectedName, actual.directedName)

    def testTranspositionFromAttrs5(self):
        '''_transpositionFromAttrs(): alternate large descending interval (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'trans.semi': '-19', 'trans.diat': '-4'})
        expectedName = 'P-12'
        actual = base._transpositionFromAttrs(elem)
        self.assertIsInstance(actual, interval.Interval)
        self.assertEqual(expectedName, actual.directedName)

    def testTranspositionFromAttrs6(self):
        '''_transpositionFromAttrs(): alternate ascending sixteenth interval (integration test)'''
        elem = ETree.Element('{mei}staffDef', attrib={'trans.semi': '26', 'trans.diat': '1'})
        expectedName = 'M16'
        actual = base._transpositionFromAttrs(elem)
        self.assertIsInstance(actual, interval.Interval)
        self.assertEqual(expectedName, actual.directedName)

    def testRemoveOctothorpe1(self):
        '''removeOctothorpe(): when there's an octothorpe'''
        xmlid = '#14ccdc11-8090-49f4-b094-5935f534131a'
        expected = '14ccdc11-8090-49f4-b094-5935f534131a'
        actual = base.removeOctothorpe(xmlid)
        self.assertEqual(expected, actual)

    def testRemoveOctothorpe2(self):
        '''removeOctothorpe(): when there's not an octothorpe'''
        xmlid = 'b05c3007-bc49-4bc2-a970-bb5700cb634d'
        expected = 'b05c3007-bc49-4bc2-a970-bb5700cb634d'
        actual = base.removeOctothorpe(xmlid)
        self.assertEqual(expected, actual)

    @mock.patch('music21.mei.base._makeArticList')
    def testArticFromElement(self, mockMakeList):
        '''articFromElement(): very straight-forward test'''
        elem = ETree.Element('artic', attrib={'artic': 'yes'})
        mockMakeList.return_value = 5
        actual = base.articFromElement(elem)
        self.assertEqual(5, actual)
        mockMakeList.assert_called_once_with('yes')

    @mock.patch('music21.mei.base._accidentalFromAttr')
    def testAccidFromElement(self, mockAccid):
        '''accidFromElement(): very straight-forward test'''
        elem = ETree.Element('accid', attrib={'accid': 'yes'})
        mockAccid.return_value = 5
        actual = base.accidFromElement(elem)
        self.assertEqual(5, actual)
        mockAccid.assert_called_once_with('yes')

    def testGetVoiceId1(self):
        '''getVoiceId(): usual case'''
        theVoice = stream.Voice()
        theVoice.id = 42
        fromThese = [None, theVoice, stream.Stream(), stream.Part(), 900]
        expected = 42
        actual = base.getVoiceId(fromThese)
        self.assertEqual(expected, actual)

    def testGetVoiceId2(self):
        '''getVoiceId(): no Voice objects causes RuntimeError'''
        fromThese = [None, stream.Stream(), stream.Part(), 900]
        self.assertRaises(RuntimeError, base.getVoiceId, fromThese)

    def testGetVoiceId3(self):
        '''getVoiceId(): three Voice objects causes RuntimeError'''
        firstVoice = stream.Voice()
        firstVoice.id = 42
        otherVoice = stream.Voice()
        otherVoice.id = 24
        fromThese = [None, firstVoice, stream.Stream(), stream.Part(), otherVoice, 900]
        self.assertRaises(RuntimeError, base.getVoiceId, fromThese)


#------------------------------------------------------------------------------
class TestAttrTranslators(unittest.TestCase):
    '''Tests for the one-to-one (string-to-simple-datatype) converter functions.'''

    def testAttrTranslator1(self):
        '''_attrTranslator(): the usual case works properly when "attr" is in "mapping"'''
        attr = 'two'
        name = 'numbers'
        mapping = {'one': 1, 'two': 2, 'three': 3}
        expected = 2
        actual = base._attrTranslator(attr, name, mapping)
        self.assertEqual(expected, actual)

    def testAttrTranslator2(self):
        '''_attrTranslator(): exception is raised properly when "attr" isn't found'''
        attr = 'four'
        name = 'numbers'
        mapping = {'one': 1, 'two': 2, 'three': 3}
        expected = 'Unexpected value for "numbers" attribute: four'
        self.assertRaises(base.MeiValueError, base._attrTranslator, attr, name, mapping)
        try:
            base._attrTranslator(attr, name, mapping)
        except base.MeiValueError as mvErr:
            self.assertEqual(expected, mvErr.args[0])

    @mock.patch('music21.mei.base._attrTranslator')
    def testAccidental(self, mockTrans):
        '''_accidentalFromAttr(): ensure proper arguments to _attrTranslator'''
        attr = 's'
        base._accidentalFromAttr(attr)
        mockTrans.assert_called_once_with(attr, 'accid', base._ACCID_ATTR_DICT)

    @mock.patch('music21.mei.base._attrTranslator')
    def testAccidGes(self, mockTrans):
        '''_accidGesFromAttr(): ensure proper arguments to _attrTranslator'''
        attr = 's'
        base._accidGesFromAttr(attr)
        mockTrans.assert_called_once_with(attr, 'accid.ges', base._ACCID_GES_ATTR_DICT)

    @mock.patch('music21.mei.base._attrTranslator')
    def testDuration(self, mockTrans):
        '''_qlDurationFromAttr(): ensure proper arguments to _attrTranslator'''
        attr = 's'
        base._qlDurationFromAttr(attr)
        mockTrans.assert_called_once_with(attr, 'dur', base._DUR_ATTR_DICT)

    @mock.patch('music21.mei.base._attrTranslator')
    def testArticulation1(self, mockTrans):
        '''_articulationFromAttr(): ensure proper arguments to _attrTranslator'''
        attr = 'marc'
        mockTrans.return_value = mock.MagicMock(name='asdf', return_value=5)
        expected = (5,)
        actual = base._articulationFromAttr(attr)
        mockTrans.assert_called_once_with(attr, 'artic', base._ARTIC_ATTR_DICT)
        self.assertEqual(expected, actual)

    @mock.patch('music21.mei.base._attrTranslator')
    def testArticulation2(self, mockTrans):
        '''_articulationFromAttr(): proper handling of "marc-stacc"'''
        attr = 'marc-stacc'
        expected = (articulations.StrongAccent, articulations.Staccato)
        actual = base._articulationFromAttr(attr)
        self.assertEqual(0, mockTrans.call_count)
        for i in xrange(len(expected)):
            self.assertTrue(isinstance(actual[i], expected[i]))

    @mock.patch('music21.mei.base._attrTranslator')
    def testArticulation3(self, mockTrans):
        '''_articulationFromAttr(): proper handling of "ten-stacc"'''
        attr = 'ten-stacc'
        expected = (articulations.Tenuto, articulations.Staccato)
        actual = base._articulationFromAttr(attr)
        self.assertEqual(0, mockTrans.call_count)
        for i in xrange(len(expected)):
            self.assertTrue(isinstance(actual[i], expected[i]))

    @mock.patch('music21.mei.base._attrTranslator')
    def testArticulation4(self, mockTrans):
        '''_articulationFromAttr(): proper handling of not-found'''
        attr = 'garbage'
        expected = 'error message'
        mockTrans.side_effect = base.MeiValueError(expected)
        self.assertRaises(base.MeiValueError, base._articulationFromAttr, attr)
        mockTrans.assert_called_once_with(attr, 'artic', base._ARTIC_ATTR_DICT)
        try:
            base._articulationFromAttr(attr)
        except base.MeiValueError as mvErr:
            self.assertEqual(expected, mvErr.args[0])

    @mock.patch('music21.mei.base._articulationFromAttr')
    def testArticList1(self, mockArtic):
        '''_makeArticList(): properly handles single-articulation lists'''
        attr = 'acc'
        mockArtic.return_value = ['accent']
        expected = ['accent']
        actual = base._makeArticList(attr)
        self.assertEqual(expected, actual)

    @mock.patch('music21.mei.base._articulationFromAttr')
    def testArticList2(self, mockArtic):
        '''_makeArticList(): properly handles multi-articulation lists'''
        attr = 'acc stacc marc'
        mockReturns = [['accent'], ['staccato'], ['marcato']]
        mockArtic.side_effect = lambda x: mockReturns.pop(0)
        expected = ['accent', 'staccato', 'marcato']
        actual = base._makeArticList(attr)
        self.assertEqual(expected, actual)

    @mock.patch('music21.mei.base._articulationFromAttr')
    def testArticList3(self, mockArtic):
        '''_makeArticList(): properly handles the compound articulations'''
        attr = 'acc marc-stacc marc'
        mockReturns = [['accent'], ['marcato', 'staccato'], ['marcato']]
        mockArtic.side_effect = lambda *x: mockReturns.pop(0)
        expected = ['accent', 'marcato', 'staccato', 'marcato']
        actual = base._makeArticList(attr)
        self.assertEqual(expected, actual)

    def testOctaveShift1(self):
        '''_getOctaveShift(): properly handles positive displacement'''
        dis = '15'
        disPlace = 'above'
        expected = 2
        actual = base._getOctaveShift(dis, disPlace)
        self.assertEqual(expected, actual)

    def testOctaveShift2(self):
        '''_getOctaveShift(): properly handles negative displacement'''
        dis = '22'
        disPlace = 'below'
        expected = -3
        actual = base._getOctaveShift(dis, disPlace)
        self.assertEqual(expected, actual)

    def testOctaveShift3(self):
        '''_getOctaveShift(): properly handles positive displacement with "None"'''
        dis = '8'
        disPlace = None
        expected = 1
        actual = base._getOctaveShift(dis, disPlace)
        self.assertEqual(expected, actual)

    def testOctaveShift4(self):
        '''_getOctaveShift(): properly positive two "None" args'''
        dis = None
        disPlace = None
        expected = 0
        actual = base._getOctaveShift(dis, disPlace)
        self.assertEqual(expected, actual)

    def testBarlineFromAttr1(self):
        '''_barlineFromAttr(): rptboth'''
        right = 'rptboth'
        expected = (bar.Repeat('end', times=2), bar.Repeat('start'))
        actual = base._barlineFromAttr(right)
        self.assertEqual(type(expected[0]), type(actual[0]))
        self.assertEqual(type(expected[1]), type(actual[1]))

    def testBarlineFromAttr2(self):
        '''_barlineFromAttr(): rptend'''
        right = 'rptend'
        expected = bar.Repeat('end', times=2)
        actual = base._barlineFromAttr(right)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.direction, expected.direction)
        self.assertEqual(expected.times, expected.times)

    def testBarlineFromAttr3(self):
        '''_barlineFromAttr(): rptstart'''
        right = 'rptstart'
        expected = bar.Repeat('start')
        actual = base._barlineFromAttr(right)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.direction, expected.direction)
        self.assertEqual(expected.times, expected.times)

    def testBarlineFromAttr4(self):
        '''_barlineFromAttr(): end (--> final)'''
        right = 'end'
        expected = bar.Barline('final')
        actual = base._barlineFromAttr(right)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.style, expected.style)

    def testTieFromAttr1(self):
        '''_tieFromAttr(): "i"'''
        right = ''
        expected = tie.Tie('start')
        actual = base._tieFromAttr(right)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.type, expected.type)

    def testTieFromAttr2(self):
        '''_tieFromAttr(): "ti"'''
        right = ''
        expected = tie.Tie('continue')
        actual = base._tieFromAttr(right)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.type, expected.type)

    def testTieFromAttr3(self):
        '''_tieFromAttr(): "m"'''
        right = ''
        expected = tie.Tie('continue')
        actual = base._tieFromAttr(right)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.type, expected.type)

    def testTieFromAttr4(self):
        '''_tieFromAttr(): "t"'''
        right = ''
        expected = tie.Tie('stop')
        actual = base._tieFromAttr(right)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.type, expected.type)


#------------------------------------------------------------------------------
class TestNoteFromElement(unittest.TestCase):
    '''Tests for noteFromElement()'''
    # NOTE: For this TestCase, in the unit tests, if you get...
    #       AttributeError: 'str' object has no attribute 'call_count'
    #       ... it means a test failure, because the str should have been a MagicMock but was
    #       replaced with a string by the unit under test.

    @mock.patch('music21.note.Note')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.safePitch')
    @mock.patch('music21.mei.base.makeDuration')
    def testUnit1(self, mockMakeDuration, mockSafePitch, mockProcEmbEl, mockNote):
        '''
        noteFromElement(): all the basic attributes (i.e., @pname, @accid, @oct, @dur, @dots)

        (mostly-unit test; mock out Note, _processEmbeddedElements(), safePitch(), and makeDuration())
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'accid': 's', 'oct': '2', 'dur': '4',
                                             'dots': '1'})
        mockMakeDuration.return_value = 'makeDuration() return'
        mockSafePitch.return_value = 'safePitch() return'
        mockNewNote = mock.MagicMock()
        mockNote.return_value = mockNewNote
        mockProcEmbEl.return_value = []
        expected = mockNewNote

        actual = base.noteFromElement(elem, None)

        self.assertEqual(expected, mockNewNote, actual)
        mockSafePitch.assert_called_once_with('D', '#', '2')
        mockMakeDuration.assert_called_once_with(1.0, 1)
        mockNote.assert_called_once_with(mockSafePitch.return_value)
        self.assertEqual(0, mockNewNote.id.call_count)
        self.assertEqual(0, mockNewNote.articulations.extend.call_count)
        self.assertEqual(0, mockNewNote.tie.call_count)
        self.assertEqual(mockMakeDuration.return_value, mockNewNote.duration)

    def testIntegration1a(self):
        '''
        noteFromElement(): all the elements that go in Note.__init__()...
                           'pname', 'accid', 'oct', 'dur', 'dots'
        (corresponds to testUnit1() with no mocks)
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'accid': 's', 'oct': '2', 'dur': '4',
                                             'dots': '1'})
        actual = base.noteFromElement(elem)
        self.assertEqual('D#2', actual.nameWithOctave)
        self.assertEqual(1.5, actual.quarterLength)
        self.assertEqual(1, actual.duration.dots)

    def testIntegration1b(self):
        '''
        noteFromElement(): all the elements that go in Note.__init__()...
                           'pname', 'accid', 'oct', 'dur', 'dots'
        (this has different arguments than testIntegration1a())
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'accid': 'n', 'oct': '2', 'dur': '4'})
        actual = base.noteFromElement(elem)
        self.assertEqual('D2', actual.nameWithOctave)
        self.assertEqual(1.0, actual.quarterLength)
        self.assertEqual(0, actual.duration.dots)

    @mock.patch('music21.note.Note')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.safePitch')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.pitch.Accidental')
    def testUnit2(self, mockAccid, mockMakeDuration, mockSafePitch, mockProcEmbEl, mockNote):
        '''
        noteFromElement(): adds <artic>, <accid>, and <dot> elements held within

        (mostly-unit test; mock out Note, _processEmbeddedElements(), safePitch(), and makeDuration())
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'oct': '2', 'dur': '4'})
        # accid: s, dots: 1, artic: stacc
        mockMakeDuration.return_value = 'makeDuration() return'
        mockSafePitch.return_value = 'safePitch() return'
        mockAccid.return_value = 'an accidental'
        mockNewNote = mock.MagicMock()
        mockNote.return_value = mockNewNote
        mockProcEmbEl.return_value = [1, '#', articulations.Staccato()]
        expected = mockNewNote
        expMockMakeDur = [mock.call(1.0, 0), mock.call(1.0, 1)]

        actual = base.noteFromElement(elem, None)

        self.assertEqual(expected, mockNewNote, actual)
        mockSafePitch.assert_called_once_with('D', None, '2')
        mockNewNote.pitch.accidental = mockAccid.return_value
        self.assertEqual(1, mockNewNote.articulations.append.call_count)
        self.assertIsInstance(mockNewNote.articulations.append.call_args_list[0][0][0],
                              articulations.Staccato)
        self.assertEqual(expMockMakeDur, mockMakeDuration.call_args_list)
        mockNote.assert_called_once_with(mockSafePitch.return_value)
        self.assertEqual(0, mockNewNote.id.call_count)
        self.assertEqual(0, mockNewNote.articulations.extend.call_count)
        self.assertEqual(0, mockNewNote.tie.call_count)
        self.assertEqual(mockMakeDuration.return_value, mockNewNote.duration)

    def testIntegration2(self):
        '''
        noteFromElement(): adds <artic>, <accid>, and <dot> elements held within
        (corresponds to testUnit2() with no mocks)
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'oct': '2', 'dur': '2'})
        elem.append(ETree.Element('{}dot'.format(_MEINS)))
        elem.append(ETree.Element('{}artic'.format(_MEINS), attrib={'artic': 'stacc'}))
        elem.append(ETree.Element('{}accid'.format(_MEINS), attrib={'accid': 's'}))

        actual = base.noteFromElement(elem)

        self.assertEqual('D#2', actual.nameWithOctave)
        self.assertEqual(3.0, actual.quarterLength)
        self.assertEqual(1, actual.duration.dots)
        self.assertEqual(1, len(actual.articulations))
        self.assertIsInstance(actual.articulations[0], articulations.Staccato)

    @mock.patch('music21.note.Note')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.safePitch')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base._makeArticList')
    @mock.patch('music21.mei.base._tieFromAttr')
    @mock.patch('music21.mei.base.addSlurs')
    def testUnit3(self, mockSlur, mockTie, mockArticList, mockMakeDuration, mockSafePitch, mockProcEmbEl, mockNote):
        '''
        noteFromElement(): adds @xml:id, @artic, and @tie attributes, and the slurBundle

        (mostly-unit test; mock out Note, _processEmbeddedElements(), safePitch(), and makeDuration())
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'accid': 's', 'oct': '2', 'dur': '4',
                                             'dots': '1', 'artic': 'stacc', _XMLID: '123',
                                             'tie': 'i1'})
        mockMakeDuration.return_value = 'makeDuration() return'
        mockSafePitch.return_value = 'safePitch() return'
        mockNewNote = mock.MagicMock()
        mockNote.return_value = mockNewNote
        mockProcEmbEl.return_value = []
        mockArticList.return_value = ['staccato!']
        mockTie.return_value = 'a tie!'
        expected = mockNewNote

        actual = base.noteFromElement(elem, 'slur bundle')

        self.assertEqual(expected, mockNewNote, actual)
        mockSafePitch.assert_called_once_with('D', '#', '2')
        mockMakeDuration.assert_called_once_with(1.0, 1)
        mockNote.assert_called_once_with(mockSafePitch.return_value)
        self.assertEqual('123', mockNewNote.id)
        mockNewNote.articulations.extend.assert_called_once_with(['staccato!'])
        self.assertEqual('a tie!', mockNewNote.tie)
        self.assertEqual(mockMakeDuration.return_value, mockNewNote.duration)
        mockSlur.assert_called_once_with(elem, mockNewNote, 'slur bundle')

    def testIntegration3(self):
        '''
        noteFromElement(): adds @xml:id, @artic, and @tie attributes, and the slurBundle
        (corresponds to testUnit3() with no mocks)
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'accid': 's', 'oct': '2', 'dur': '4',
                                             'dots': '1', _XMLID: 'asdf1234', 'artic': 'stacc',
                                             'tie': 'i1'})
        slurBundle = spanner.SpannerBundle()

        actual = base.noteFromElement(elem, slurBundle)

        self.assertEqual('D#2', actual.nameWithOctave)
        self.assertEqual(1.5, actual.quarterLength)
        self.assertEqual(1, actual.duration.dots)
        self.assertEqual('asdf1234', actual.id)
        self.assertEqual(1, len(actual.articulations))
        self.assertIsInstance(actual.articulations[0], articulations.Staccato)
        self.assertEqual(tie.Tie('start'), actual.tie)

    @mock.patch('music21.note.Note')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.safePitch')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.scaleToTuplet')
    @mock.patch('music21.pitch.Accidental')
    def testUnit4(self, mockAccid, mockTuplet, mockMakeDuration, mockSafePitch, mockProcEmbEl, mockNote):
        '''
        noteFromElement(): adds tuplet-related attributes; plus @m21Beam where the
            duration doesn't require adjusting beams

        (mostly-unit test)
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'oct': '2', 'dur': '4',
                                             'm21TupletNum': '5', 'm21TupletNumbase': '4',
                                             'm21TupletSearch': 'start',
                                             'accid.ges': 's', 'm21Beam': 'start'})
        mockSafePitch.return_value = 'safePitch() return'
        mockNewNote = mock.MagicMock()
        mockNewNote.beams = mock.MagicMock()
        mockMakeDuration.return_value = mock.MagicMock()
        mockMakeDuration.return_value.type = 'quarter'
        mockNote.return_value = mockNewNote
        mockProcEmbEl.return_value = []
        mockTuplet.return_value = 'made the tuplet'
        mockAccid.return_value = 'the accidental'
        expected = mockTuplet.return_value

        actual = base.noteFromElement(elem, 'slur bundle')

        self.assertEqual(expected, actual)
        mockSafePitch.assert_called_once_with('D', None, '2')
        mockMakeDuration.assert_called_once_with(1.0, 0)
        mockNote.assert_called_once_with(mockSafePitch.return_value)
        mockTuplet.assert_called_once_with(mockNewNote, elem)
        mockAccid.assert_called_once_with('#')
        self.assertEqual(0, mockNewNote.beams.fill.call_count)

    def testIntegration4(self):
        '''
        noteFromElement(): @m21TupletNum
        (corresponds to testUnit4() with no mocks)
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'oct': '2', 'dur': '4',
                                             'm21TupletNum': '5', 'm21TupletNumbase': '4',
                                             'm21TupletSearch': 'start',
                                             'accid.ges': 's', 'm21Beam': 'start'})
        slurBundle = spanner.SpannerBundle()

        actual = base.noteFromElement(elem, slurBundle)

        self.assertEqual('D#2', actual.nameWithOctave)
        self.assertEqual(1.0, actual.quarterLength)
        self.assertEqual('quarter', actual.duration.type)
        self.assertEqual('5', actual.m21TupletNum)
        self.assertEqual('4', actual.m21TupletNumbase)
        self.assertEqual('start', actual.m21TupletSearch)

    @mock.patch('music21.note.Note')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.safePitch')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.duration.GraceDuration')
    def testUnit5(self, mockGrace, mockMakeDuration, mockSafePitch, mockProcEmbEl, mockNote):
        '''
        noteFromElement(): test @grace and @m21Beam where the duration requires adjusting beams

        (mostly-unit test)
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'oct': '2', 'dur': '16',
                                             'm21Beam': 'start', 'grace': 'acc'})
        mockSafePitch.return_value = 'safePitch() return'
        mockNewNote = mock.MagicMock()
        mockNewNote.beams = mock.MagicMock()
        mockNote.return_value = mockNewNote
        mockProcEmbEl.return_value = []
        mockGrace.return_value = mock.MagicMock(spec_set=duration.Duration)
        mockGrace.return_value.type = '16th'
        expected = mockNewNote

        actual = base.noteFromElement(elem, 'slur bundle')

        self.assertEqual(expected, actual)
        mockSafePitch.assert_called_once_with('D', None, '2')
        mockMakeDuration.assert_called_once_with(0.25, 0)
        mockNote.assert_called_once_with(mockSafePitch.return_value)
        mockNewNote.beams.fill.assert_called_once_with('16th', 'start')
        self.assertEqual(mockGrace.return_value, mockNewNote.duration)

    def testIntegration5(self):
        '''
        noteFromElement(): test @grace and @m21Beam where the duration requires adjusting beams
        (corresponds to testUnit5() with no mocks)
        '''
        elem = ETree.Element('note', attrib={'pname': 'D', 'oct': '2', 'dur': '16',
                                             'm21Beam': 'start', 'grace': 'acc'})
        slurBundle = spanner.SpannerBundle()

        actual = base.noteFromElement(elem, slurBundle)

        self.assertEqual('D2', actual.nameWithOctave)
        self.assertEqual(0.0, actual.quarterLength)
        self.assertEqual('16th', actual.duration.type)
        self.assertTrue(1, actual.beams.beamsList[0].number)
        self.assertTrue('start', actual.beams.beamsList[0].type)
        self.assertTrue(2, actual.beams.beamsList[1].number)
        self.assertTrue('start', actual.beams.beamsList[1].type)

    # NOTE: consider adding to previous tests rather than making new ones


#------------------------------------------------------------------------------
class TestRestFromElement(unittest.TestCase):
    '''Tests for restFromElement() and spaceFromElement()'''

    @mock.patch('music21.note.Rest')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.scaleToTuplet')
    def testUnit1(self, mockTuplet, mockMakeDur, mockRest):
        '''
        restFromElement(): test @dur, @dots, @xml:id, and tuplet-related attributes
        '''
        elem = ETree.Element('rest', attrib={'dur': '4', 'dots': '1', _XMLID: 'the id',
                                             'm21TupletNum': '5', 'm21TupletNumbase': '4',
                                             'm21TupletType': 'start'})
        mockMakeDur.return_value = 'the duration'
        mockNewRest = mock.MagicMock('new rest')
        mockRest.return_value = mockNewRest
        mockTuplet.return_value = 'tupletized'
        expected = mockTuplet.return_value

        actual = base.restFromElement(elem)

        self.assertEqual(expected, actual)
        mockRest.assert_called_once_with(duration=mockMakeDur.return_value)
        mockMakeDur.assert_called_once_with(1.0, 1)
        mockTuplet.assert_called_once_with(mockRest.return_value, elem)
        self.assertEqual('the id', mockNewRest.id)

    def testIntegration1(self):
        '''
        restFromElement(): test @dur, @dots, @xml:id, and tuplet-related attributes

        (without mock objects)
        '''
        elem = ETree.Element('rest', attrib={'dur': '4', 'dots': '1', _XMLID: 'the id',
                                             'm21TupletNum': '5', 'm21TupletNumbase': '4',
                                             'm21TupletType': 'start'})

        actual = base.restFromElement(elem)

        self.assertEqual(Fraction(6, 5), actual.quarterLength)
        self.assertEqual(1, actual.duration.dots)
        self.assertEqual('the id', actual.id)
        self.assertEqual('start', actual.duration.tuplets[0].type)

    @mock.patch('music21.note.SpacerRest')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.scaleToTuplet')
    def testUnit2(self, mockTuplet, mockMakeDur, mockSpacer):
        '''
        spaceFromElement(): test @dur, @dots, @xml:id, and tuplet-related attributes
        '''
        elem = ETree.Element('rest', attrib={'dur': '4', 'dots': '1', _XMLID: 'the id',
                                             'm21TupletNum': '5', 'm21TupletNumbase': '4',
                                             'm21TupletType': 'start'})
        mockMakeDur.return_value = 'the duration'
        mockNewSpace = mock.MagicMock('new rest')
        mockSpacer.return_value = mockNewSpace
        mockTuplet.return_value = 'tupletized'
        expected = mockTuplet.return_value

        actual = base.spaceFromElement(elem)

        self.assertEqual(expected, actual)
        mockSpacer.assert_called_once_with(duration=mockMakeDur.return_value)
        mockMakeDur.assert_called_once_with(1.0, 1)
        mockTuplet.assert_called_once_with(mockSpacer.return_value, elem)
        self.assertEqual('the id', mockNewSpace.id)

    def testIntegration2(self):
        '''
        spaceFromElement(): test @dur, @dots, @xml:id, and tuplet-related attributes

        (without mock objects)
        '''
        elem = ETree.Element('space', attrib={'dur': '4', 'dots': '1', _XMLID: 'the id',
                                              'm21TupletNum': '5', 'm21TupletNumbase': '4',
                                              'm21TupletType': 'start'})

        actual = base.spaceFromElement(elem)

        self.assertEqual(Fraction(6, 5), actual.quarterLength)
        self.assertEqual(1, actual.duration.dots)
        self.assertEqual('the id', actual.id)
        self.assertEqual('start', actual.duration.tuplets[0].type)

    @mock.patch('music21.mei.base.restFromElement')
    def testUnit3(self, mockRest):
        '''
        mRestFromElement(): reacts properly to an Element with the @dur attribute
        '''
        elem = ETree.Element('mRest', attrib={'dur': '2'})
        mockRest.return_value = 'the rest'

        actual = base.mRestFromElement(elem)

        self.assertEqual(mockRest.return_value, actual)
        mockRest.assert_called_once_with(elem, None)

    @mock.patch('music21.mei.base.restFromElement')
    def testUnit4(self, mockRest):
        '''
        mRestFromElement(): reacts properly to an Element without the @dur attribute
        '''
        elem = ETree.Element('mRest')
        mockRest.return_value = mock.MagicMock()

        actual = base.mRestFromElement(elem)

        self.assertEqual(mockRest.return_value, actual)
        mockRest.assert_called_once_with(elem, None)
        self.assertTrue(actual.m21wasMRest)

    @mock.patch('music21.mei.base.spaceFromElement')
    def testUnit5(self, mockSpace):
        '''
        mSpaceFromElement(): reacts properly to an Element with the @dur attribute
        '''
        elem = ETree.Element('mSpace', attrib={'dur': '2'})
        mockSpace.return_value = 'the spacer'

        actual = base.mSpaceFromElement(elem)

        self.assertEqual(mockSpace.return_value, actual)
        mockSpace.assert_called_once_with(elem, None)

    @mock.patch('music21.mei.base.spaceFromElement')
    def testUnit6(self, mockSpace):
        '''
        mSpaceFromElement(): reacts properly to an Element without the @dur attribute
        '''
        elem = ETree.Element('mSpace')
        mockSpace.return_value = mock.MagicMock()

        actual = base.mSpaceFromElement(elem)

        self.assertEqual(mockSpace.return_value, actual)
        mockSpace.assert_called_once_with(elem, None)
        self.assertTrue(actual.m21wasMRest)


#------------------------------------------------------------------------------
class TestChordFromElement(unittest.TestCase):
    '''Tests for chordFromElement()'''
    # NOTE: For this TestCase, in the unit tests, if you get...
    #       AttributeError: 'str' object has no attribute 'call_count'
    #       ... it means a test failure, because the str should have been a MagicMock but was
    #       replaced with a string by the unit under test.

    @staticmethod
    def makeNoteElems(pname, accid, octArg, dur, dots):
        '''Factory function for the Element objects that are a <note>.'''
        return ETree.Element('{}note'.format(_MEINS), pname=pname, accid=accid, oct=octArg, dur=dur, dots=dots)

    @mock.patch('music21.chord.Chord')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.noteFromElement')
    def testUnit1(self, mockNoteFromE, mockMakeDuration, mockProcEmbEl, mockChord):
        '''
        chordFromElement(): all the basic attributes (i.e., @pname, @accid, @oct, @dur, @dots)
        '''
        elem = ETree.Element('chord', attrib={'dur': '4', 'dots': '1'})
        noteElements = [TestChordFromElement.makeNoteElems(x, None, '4', '8', None) for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        mockNoteFromE.return_value = 'a note'
        mockMakeDuration.return_value = 'makeDuration() return'
        mockNewChord = mock.MagicMock()
        mockChord.return_value = mockNewChord
        mockProcEmbEl.return_value = []

        actual = base.chordFromElement(elem, None)

        self.assertEqual(mockNewChord, actual)
        mockMakeDuration.assert_called_once_with(1.0, 1)
        mockChord.assert_called_once_with(notes=[mockNoteFromE.return_value for _ in range(3)])
        self.assertEqual(0, mockNewChord.id.call_count)
        self.assertEqual(0, mockNewChord.articulations.extend.call_count)
        self.assertEqual(0, mockNewChord.tie.call_count)
        self.assertEqual(mockMakeDuration.return_value, mockNewChord.duration)

    def testIntegration1(self):
        '''
        chordFromElement(): all the basic attributes (i.e., @pname, @accid, @oct, @dur, @dots)

        (corresponds to testUnit1() with no mocks)
        '''
        elem = ETree.Element('chord', attrib={'dur': '4', 'dots': '1'})
        noteElements = [TestChordFromElement.makeNoteElems(x, 'n', '4', '8', '0') for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        expectedName = 'Chord {C-natural in octave 4 | E-natural in octave 4 | G-natural in octave 4} Dotted Quarter'
        actual = base.chordFromElement(elem)
        self.assertEqual(expectedName, actual.fullName)

    @mock.patch('music21.chord.Chord')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.noteFromElement')
    def testUnit2(self, mockNoteFromE, mockMakeDuration, mockProcEmbEl, mockChord):
        '''
        chordFromElement(): adds an <artic> element held within
        '''
        elem = ETree.Element('chord', attrib={'dur': '4', 'dots': '1'})
        noteElements = [TestChordFromElement.makeNoteElems(x, None, '4', '8', None) for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        elem.append(ETree.Element('{}artic'.format(_MEINS), artic='stacc'))
        mockNoteFromE.return_value = 'a note'
        mockMakeDuration.return_value = 'makeDuration() return'
        mockNewChord = mock.MagicMock()
        mockChord.return_value = mockNewChord
        mockProcEmbEl.return_value = [articulations.Staccato()]
        expected = mockNewChord

        actual = base.chordFromElement(elem, None)

        self.assertEqual(expected, mockNewChord, actual)
        mockMakeDuration.assert_called_once_with(1.0, 1)
        mockChord.assert_called_once_with(notes=[mockNoteFromE.return_value for _ in range(3)])
        self.assertEqual(1, mockNewChord.articulations.append.call_count)
        self.assertIsInstance(mockNewChord.articulations.append.call_args_list[0][0][0],
                              articulations.Staccato)
        self.assertEqual(0, mockNewChord.id.call_count)
        self.assertEqual(0, mockNewChord.articulations.extend.call_count)
        self.assertEqual(0, mockNewChord.tie.call_count)
        self.assertEqual(mockMakeDuration.return_value, mockNewChord.duration)

    def testIntegration2(self):
        '''
        noteFromElement(): adds <artic>, <accid>, and <dot> elements held within

        (corresponds to testUnit2() with no mocks)
        '''
        elem = ETree.Element('chord', attrib={'dur': '4', 'dots': '1'})
        noteElements = [TestChordFromElement.makeNoteElems(x, 'n', '4', '8', '0') for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        elem.append(ETree.Element('{}artic'.format(_MEINS), artic='stacc'))
        expectedName = 'Chord {C-natural in octave 4 | E-natural in octave 4 | G-natural in octave 4} Dotted Quarter'
        actual = base.chordFromElement(elem)
        self.assertEqual(expectedName, actual.fullName)
        self.assertEqual(1, len(actual.articulations))
        self.assertIsInstance(actual.articulations[0], articulations.Staccato)

    @mock.patch('music21.chord.Chord')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.noteFromElement')
    @mock.patch('music21.mei.base._makeArticList')
    @mock.patch('music21.mei.base._tieFromAttr')
    @mock.patch('music21.mei.base.addSlurs')
    def testUnit3(self, mockSlur, mockTie, mockArticList, mockNoteFromE, mockMakeDuration, mockProcEmbEl, mockChord):
        '''
        chordFromElement(): adds @xml:id, @artic, and @tie attributes, and the slurBundle
        '''
        elem = ETree.Element('chord', attrib={'dur': '4', 'dots': '1', 'artic': 'stacc',
                                              _XMLID: '123', 'tie': 'i1'})
        noteElements = [TestChordFromElement.makeNoteElems(x, None, '4', '8', None) for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        mockNoteFromE.return_value = 'a note'
        mockMakeDuration.return_value = 'makeDuration() return'
        mockNewChord = mock.MagicMock()
        mockChord.return_value = mockNewChord
        mockProcEmbEl.return_value = []
        mockArticList.return_value = ['staccato!']
        mockTie.return_value = 'a tie!'

        actual = base.chordFromElement(elem, 'slur bundle')

        self.assertEqual(mockNewChord, actual)
        mockMakeDuration.assert_called_once_with(1.0, 1)
        mockChord.assert_called_once_with(notes=[mockNoteFromE.return_value for _ in range(3)])
        self.assertEqual(mockMakeDuration.return_value, mockNewChord.duration)
        mockNewChord.articulations.extend.assert_called_once_with(['staccato!'])
        self.assertEqual('123', mockNewChord.id)
        self.assertEqual('a tie!', mockNewChord.tie)
        mockSlur.assert_called_once_with(elem, mockNewChord, 'slur bundle')

    def testIntegration3(self):
        '''
        noteFromElement(): adds @xml:id, @artic, and @tie attributes, and the slurBundle

        (corresponds to testUnit3() with no mocks)
        '''
        elem = ETree.Element('chord', attrib={'dur': '4', 'dots': '1', 'artic': 'stacc',
                                              _XMLID: 'asdf1234', 'tie': 'i1'})
        noteElements = [TestChordFromElement.makeNoteElems(x, 'n', '4', '8', '0') for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        expectedName = 'Chord {C-natural in octave 4 | E-natural in octave 4 | G-natural in octave 4} Dotted Quarter'
        actual = base.chordFromElement(elem)
        self.assertEqual(expectedName, actual.fullName)
        self.assertEqual(1, len(actual.articulations))
        self.assertIsInstance(actual.articulations[0], articulations.Staccato)
        self.assertEqual('asdf1234', actual.id)
        self.assertEqual(tie.Tie('start'), actual.tie)

    @mock.patch('music21.chord.Chord')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.noteFromElement')
    @mock.patch('music21.mei.base.scaleToTuplet')
    def testUnit4(self, mockTuplet, mockNoteFromE, mockMakeDuration, mockProcEmbEl, mockChord):
        '''
        chordFromElement(): adds tuplet-related attributes
        '''
        elem = ETree.Element('chord', attrib={'dur': '4', 'm21TupletNum': '5', 'm21TupletNumbase': '4',
                                              'm21TupletSearch': 'start', 'm21Beam': 'start'})
        noteElements = [TestChordFromElement.makeNoteElems(x, None, '4', '8', None) for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        mockNoteFromE.return_value = 'a note'
        mockMakeDuration.return_value = mock.MagicMock(spec_set=duration.Duration)
        mockMakeDuration.return_value.type = 'quarter'
        mockNewChord = mock.MagicMock()
        mockChord.return_value = mockNewChord
        mockProcEmbEl.return_value = []
        mockTuplet.return_value = 'tupletified'
        expected = mockTuplet.return_value

        actual = base.chordFromElement(elem, 'slur bundle')

        self.assertEqual(expected, actual)
        mockMakeDuration.assert_called_once_with(1.0, 0)
        mockChord.assert_called_once_with(notes=[mockNoteFromE.return_value for _ in range(3)])
        self.assertEqual(mockMakeDuration.return_value, mockNewChord.duration)
        mockTuplet.assert_called_once_with(mockNewChord, elem)
        self.assertEqual(0, mockNewChord.beams.fill.call_count)

    def testIntegration4(self):
        '''
        noteFromElement(): adds tuplet-related attributes

        (corresponds to testUnit4() with no mocks)
        '''
        elem = ETree.Element('chord', attrib={'dur': '4', 'm21TupletNum': '5', 'm21TupletNumbase': '4',
                                              'm21TupletSearch': 'start', 'm21Beam': 'start'})
        noteElements = [TestChordFromElement.makeNoteElems(x, 'n', '4', '8', '0') for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        expectedName = 'Chord {C-natural in octave 4 | E-natural in octave 4 | G-natural in octave 4} Quarter'

        actual = base.chordFromElement(elem)

        self.assertEqual(expectedName, actual.fullName)
        self.assertEqual('5', actual.m21TupletNum)
        self.assertEqual('4', actual.m21TupletNumbase)
        self.assertEqual('start', actual.m21TupletSearch)

    @mock.patch('music21.chord.Chord')
    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.makeDuration')
    @mock.patch('music21.mei.base.noteFromElement')
    @mock.patch('music21.duration.GraceDuration')
    def testUnit5(self, mockGrace, mockNoteFromE, mockMakeDuration, mockProcEmbEl, mockChord):
        '''
        chordFromElement(): test @grace and @m21Beam when the duration does require adjusting the beams
        '''
        elem = ETree.Element('chord', attrib={'dur': '16', 'm21Beam': 'start', 'grace': 'acc'})
        noteElements = [TestChordFromElement.makeNoteElems(x, None, '4', '8', None) for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        mockNoteFromE.return_value = 'a note'
        mockGrace.return_value = mock.MagicMock(spec_set=duration.Duration)
        mockGrace.return_value.type = '16th'
        mockNewChord = mock.MagicMock()
        mockChord.return_value = mockNewChord
        mockProcEmbEl.return_value = []
        expected = mockNewChord

        actual = base.chordFromElement(elem, 'slur bundle')

        self.assertEqual(expected, actual)
        mockMakeDuration.assert_called_once_with(0.25, 0)
        mockChord.assert_called_once_with(notes=[mockNoteFromE.return_value for _ in range(3)])
        self.assertEqual(mockGrace.return_value, mockNewChord.duration)
        mockNewChord.beams.fill.assert_called_once_with('16th', 'start')

    def testIntegration5(self):
        '''
        noteFromElement(): @grace and @m21Beam when the duration does require adjusting the beams

        (corresponds to testUnit5() with no mocks)
        '''
        elem = ETree.Element('chord', attrib={'dur': '16', 'm21Beam': 'start', 'grace': 'acc'})
        noteElements = [TestChordFromElement.makeNoteElems(x, 'n', '4', '8', '0') for x in ('c', 'e', 'g')]
        for eachElement in noteElements:
            elem.append(eachElement)
        expectedName = 'Chord {C-natural in octave 4 | E-natural in octave 4 | G-natural in octave 4} 16th'

        actual = base.chordFromElement(elem)

        self.assertEqual(expectedName, actual.fullName)
        self.assertEqual(0.0, actual.quarterLength)
        self.assertEqual('16th', actual.duration.type)
        self.assertTrue(1, actual.beams.beamsList[0].number)
        self.assertTrue('start', actual.beams.beamsList[0].type)
        self.assertTrue(2, actual.beams.beamsList[1].number)
        self.assertTrue('start', actual.beams.beamsList[1].type)

    # NOTE: consider adding to previous tests rather than making new ones


#------------------------------------------------------------------------------
class TestClefFromElement(unittest.TestCase):
    '''Tests for clefFromElement()'''
    # NOTE: in this function's integration tests, the Element.tag attribute doesn't actually matter

    @mock.patch('music21.clef.clefFromString')
    @mock.patch('music21.clef.PercussionClef')
    @mock.patch('music21.clef.TabClef')
    def testUnit1a(self, mockTabClef, mockPercClef, mockClefFromString):
        '''
        clefFromElement(): all the elements that go in clef.clefFromString()...
                           'shape', 'line', 'dis', and 'dis.place'
        (mostly-unit test; only mock out clef and the ElementTree.Element)
        '''
        elem = mock.MagicMock()
        expectedGetOrder = [mock.call('shape'), mock.call('shape'), mock.call('shape'),
                            mock.call('line'), mock.call('dis'), mock.call('dis.place')]
        expectedGetOrder.extend([mock.ANY for _ in xrange(1)])  # additional calls to elem.get(), not part of this test
        elemGetReturns = ['theClefShape', 'theClefShape', 'theClefShape', '2', '8', 'above']
        elem.get.side_effect = lambda *x: elemGetReturns.pop(0) if len(elemGetReturns) > 0 else None
        mockClefFromString.return_value = mock.MagicMock(name='clefFromString()')
        expected = mockClefFromString.return_value

        actual = base.clefFromElement(elem)

        self.assertEqual(expected, actual)
        mockClefFromString.assert_called_once_with_('theClefShape2', 1)
        self.assertSequenceEqual(expectedGetOrder, elem.get.call_args_list)
        self.assertEqual(0, mockTabClef.call_count)
        self.assertEqual(0, mockPercClef.call_count)

    @mock.patch('music21.clef.clefFromString')
    @mock.patch('music21.clef.PercussionClef')
    @mock.patch('music21.clef.TabClef')
    def testUnit1b(self, mockTabClef, mockPercClef, mockClefFromString):
        '''
        clefFromElement(): same as testUnit1a() but with 'perc' "shape"
        '''
        elem = mock.MagicMock()
        expectedGetOrder = [mock.call('shape')]
        expectedGetOrder.extend([mock.ANY for _ in xrange(1)])  # additional calls to elem.get(), not part of this test
        elemGetReturns = ['perc']
        elem.get.side_effect = lambda *x: elemGetReturns.pop(0) if len(elemGetReturns) > 0 else None
        mockPercClef.return_value = mock.MagicMock(name='PercussionClef()')
        expected = mockPercClef.return_value

        actual = base.clefFromElement(elem)

        self.assertEqual(expected, actual)
        self.assertEqual(0, mockClefFromString.call_count)
        self.assertSequenceEqual(expectedGetOrder, elem.get.call_args_list)
        self.assertEqual(0, mockTabClef.call_count)
        self.assertEqual(1, mockPercClef.call_count)

    @mock.patch('music21.clef.clefFromString')
    @mock.patch('music21.clef.PercussionClef')
    @mock.patch('music21.clef.TabClef')
    def testUnit1c(self, mockTabClef, mockPercClef, mockClefFromString):
        '''
        clefFromElement(): same as testUnit1c() but with 'TAB' "shape"
        '''
        elem = mock.MagicMock()
        expectedGetOrder = [mock.call('shape'), mock.call('shape')]
        expectedGetOrder.extend([mock.ANY for _ in xrange(1)])  # additional calls to elem.get(), not part of this test
        elemGetReturns = ['TAB', 'TAB']
        elem.get.side_effect = lambda *x: elemGetReturns.pop(0) if len(elemGetReturns) > 0 else None
        mockPercClef.return_value = mock.MagicMock(name='PercussionClef()')
        expected = mockTabClef.return_value

        actual = base.clefFromElement(elem)

        self.assertEqual(expected, actual)
        self.assertEqual(0, mockClefFromString.call_count)
        self.assertSequenceEqual(expectedGetOrder, elem.get.call_args_list)
        self.assertEqual(1, mockTabClef.call_count)
        self.assertEqual(0, mockPercClef.call_count)

    def testIntegration1a(self):
        '''
        clefFromElement(): all the elements that go in clef.clefFromString()...
                           'shape', 'line', 'dis', and 'dis.place'
        (corresponds to testUnit1a, with real objects)
        '''
        clefElem = ETree.Element('clef')
        clefAttribs = {'shape': 'G', 'line': '2', 'dis': '8', 'dis.place': 'above'}
        for eachKey in clefAttribs:
            clefElem.set(eachKey, clefAttribs[eachKey])
        expectedClass = clef.Treble8vaClef

        actual = base.clefFromElement(clefElem)

        self.assertEqual(expectedClass, actual.__class__)

    def testIntegration1b(self):
        '''
        PercussionClef

        (corresponds to testUnit1b, with real objects)
        '''
        clefElem = ETree.Element('clef')
        clefAttribs = {'shape': 'perc'}
        for eachKey in clefAttribs:
            clefElem.set(eachKey, clefAttribs[eachKey])
        expectedClass = clef.PercussionClef

        actual = base.clefFromElement(clefElem)

        self.assertEqual(expectedClass, actual.__class__)

    def testIntegration1c(self):
        '''
        TabClef

        (corresponds to testUnit1c, with real objects)
        '''
        clefElem = ETree.Element('clef')
        clefAttribs = {'shape': 'TAB'}
        for eachKey in clefAttribs:
            clefElem.set(eachKey, clefAttribs[eachKey])
        expectedClass = clef.TabClef

        actual = base.clefFromElement(clefElem)

        self.assertEqual(expectedClass, actual.__class__)

    @mock.patch('music21.clef.clefFromString')
    @mock.patch('music21.clef.PercussionClef')
    @mock.patch('music21.clef.TabClef')
    def testUnit2(self, mockTabClef, mockPercClef, mockClefFromString):
        '''
        clefFromElement(): adds the "xml:id" attribute
        '''
        elem = mock.MagicMock()
        expectedGetOrder = [mock.call('shape'), mock.call(_XMLID), mock.call(_XMLID)]
        expectedGetOrder.extend([mock.ANY for _ in xrange(0)])  # additional calls to elem.get(), not part of this test
        elemGetReturns = ['perc', 'theXMLID', 'theXMLID']
        elem.get.side_effect = lambda *x: elemGetReturns.pop(0) if len(elemGetReturns) > 0 else None
        mockPercClef.return_value = mock.MagicMock(name='PercussionClef()')
        expected = mockPercClef.return_value

        actual = base.clefFromElement(elem)

        self.assertEqual(expected, actual)
        self.assertEqual(0, mockClefFromString.call_count)
        self.assertSequenceEqual(expectedGetOrder, elem.get.call_args_list)
        self.assertEqual(0, mockTabClef.call_count)
        self.assertEqual(1, mockPercClef.call_count)
        self.assertEqual('theXMLID', actual.id)



#------------------------------------------------------------------------------
class TestLayerFromElement(unittest.TestCase):
    '''Tests for layerFromElement()'''

    @mock.patch('music21.mei.base.noteFromElement')
    @mock.patch('music21.stream.Voice')
    @mock.patch('music21.mei.base._guessTuplets')
    def testUnit1a(self, mockTuplets, mockVoice, mockNoteFromElement):
        '''
        layerFromElement(): basic functionality (i.e., that the tag-name-to-converter-function
                            mapping works; that tags not in the mapping are ignored; and that a
                            Voice object is returned. And "id" is set from the @n attribute.
        (mostly-unit test; only mock noteFromElement, _guessTuplets, and the ElementTree.Element)
        '''
        theNAttribute = '@n value'
        elem = mock.MagicMock()
        elemGetReturns = [theNAttribute, theNAttribute]
        elem.get.side_effect = lambda *x: elemGetReturns.pop(0) if len(elemGetReturns) else None
        expectedGetOrder = [mock.call('n'), mock.call('n')]
        iterfindReturn = [mock.MagicMock(name='note1'),
                          mock.MagicMock(name='imaginary'),
                          mock.MagicMock(name='note2')]
        iterfindReturn[0].tag = '{}note'.format(base._MEINS)
        iterfindReturn[1].tag = '{}imaginary'.format(base._MEINS)
        iterfindReturn[2].tag = '{}note'.format(base._MEINS)
        elem.iterfind = mock.MagicMock(return_value=iterfindReturn)
        # "MNFE" is "mockNoteFromElement"
        expectedMNFEOrder = [mock.call(iterfindReturn[0], None), mock.call(iterfindReturn[2], None)]
        mockNFEreturns = ['mockNoteFromElement return 1', 'mockNoteFromElement return 2']
        mockNoteFromElement.side_effect = lambda *x: mockNFEreturns.pop(0)
        mockTuplets.side_effect = lambda x: x
        mockVoice.return_value = mock.MagicMock(spec_set=stream.Stream(), name='Voice')
        expectedAppendCalls = [mock.call(mockNFEreturns[0]), mock.call(mockNFEreturns[1])]

        actual = base.layerFromElement(elem)

        elem.iterfind.assert_called_once_with('*')
        self.assertEqual(mockVoice.return_value, actual)
        self.assertSequenceEqual(expectedMNFEOrder, mockNoteFromElement.call_args_list)
        mockVoice.assert_called_once_with()
        self.assertSequenceEqual(expectedAppendCalls, mockVoice.return_value._appendCore.call_args_list)
        mockVoice.return_value._elementsChanged.assert_called_once_with()
        self.assertEqual(theNAttribute, actual.id)
        self.assertSequenceEqual(expectedGetOrder, elem.get.call_args_list)

    @mock.patch('music21.mei.base.noteFromElement')
    @mock.patch('music21.stream.Voice')
    @mock.patch('music21.mei.base._guessTuplets')
    def testUnit1b(self, mockTuplets, mockVoice, mockNoteFromElement):
        '''
        Same as testUnit1a() *but* with ``overrideN`` provided.
        '''
        elem = mock.MagicMock()
        iterfindReturn = [mock.MagicMock(name='note1'),
                          mock.MagicMock(name='imaginary'),
                          mock.MagicMock(name='note2')]
        iterfindReturn[0].tag = '{}note'.format(base._MEINS)
        iterfindReturn[1].tag = '{}imaginary'.format(base._MEINS)
        iterfindReturn[2].tag = '{}note'.format(base._MEINS)
        elem.iterfind = mock.MagicMock(return_value=iterfindReturn)
        # "MNFE" is "mockNoteFromElement"
        expectedMNFEOrder = [mock.call(iterfindReturn[0], None), mock.call(iterfindReturn[2], None)]
        mockNFEreturns = ['mockNoteFromElement return 1', 'mockNoteFromElement return 2']
        mockNoteFromElement.side_effect = lambda *x: mockNFEreturns.pop(0)
        mockTuplets.side_effect = lambda x: x
        mockVoice.return_value = mock.MagicMock(spec_set=stream.Stream(), name='Voice')
        expectedAppendCalls = [mock.call(mockNFEreturns[0]), mock.call(mockNFEreturns[1])]
        overrideN = 'my own @n'

        actual = base.layerFromElement(elem, overrideN)

        elem.iterfind.assert_called_once_with('*')
        self.assertEqual(mockVoice.return_value, actual)
        self.assertSequenceEqual(expectedMNFEOrder, mockNoteFromElement.call_args_list)
        mockVoice.assert_called_once_with()
        self.assertSequenceEqual(expectedAppendCalls, mockVoice.return_value._appendCore.call_args_list)
        mockVoice.return_value._elementsChanged.assert_called_once_with()
        self.assertEqual(overrideN, actual.id)
        self.assertEqual(0, elem.get.call_count)

    @mock.patch('music21.mei.base.noteFromElement')
    @mock.patch('music21.stream.Voice')
    @mock.patch('music21.mei.base._guessTuplets')
    def testUnit1c(self, mockTuplets, mockVoice, mockNoteFromElement):  # pylint: disable=unused-argument
        '''
        Same as testUnit1a() *but* without ``overrideN`` or @n.
        '''
        elem = mock.MagicMock()
        elem.get.return_value = None
        iterfindReturn = [mock.MagicMock(name='note1'),
                          mock.MagicMock(name='imaginary'),
                          mock.MagicMock(name='note2')]
        iterfindReturn[0].tag = '{}note'.format(base._MEINS)
        iterfindReturn[1].tag = '{}imaginary'.format(base._MEINS)
        iterfindReturn[2].tag = '{}note'.format(base._MEINS)
        elem.iterfind = mock.MagicMock(return_value=iterfindReturn)
        # NB: we call the layerFromElement() twice, so we need twice the return values here
        # "MNFE" is "mockNoteFromElement"
        mockNFEreturns = ['mockNoteFromElement return 1', 'mockNoteFromElement return 2',
                          'mockNoteFromElement return 1', 'mockNoteFromElement return 2']
        mockNoteFromElement.side_effect = lambda *x: mockNFEreturns.pop(0)
        mockVoice.return_value = mock.MagicMock(spec_set=stream.Stream(), name='Voice')

        self.assertRaises(base.MeiAttributeError, base.layerFromElement, elem)

        try:
            base.layerFromElement(elem)
        except base.MeiAttributeError as maError:
            self.assertEqual(base._MISSING_VOICE_ID, maError.args[0])


    def testIntegration1a(self):
        '''
        layerFromElement(): basic functionality (i.e., that the tag-name-to-converter-function
                            mapping works; that tags not in the mapping are ignored; and that a
                            Voice object is returned. And "xml:id" is set.
        (corresponds to testUnit1a() but without mock objects)
        '''
        inputXML = '''<layer n="so voice ID" xmlns="http://www.music-encoding.org/ns/mei">
                          <note pname="F" oct="2" dur="4" />
                          <note pname="E" oct="2" accid="f" dur="4" />
                          <imaginary awesome="true" />
                      </layer>'''
        elem = ETree.fromstring(inputXML)

        actual = base.layerFromElement(elem)

        self.assertEqual(2, len(actual))
        self.assertEqual('so voice ID', actual.id)
        self.assertEqual(0.0, actual[0].offset)
        self.assertEqual(1.0, actual[1].offset)
        self.assertEqual(1.0, actual[0].quarterLength)
        self.assertEqual(1.0, actual[1].quarterLength)
        self.assertEqual('F2', actual[0].nameWithOctave)
        self.assertEqual('E-2', actual[1].nameWithOctave)


    def testIntegration1b(self):
        '''
        (corresponds to testUnit1b() but without mock objects)
        '''
        inputXML = '''<layer xmlns="http://www.music-encoding.org/ns/mei">
                          <note pname="F" oct="2" dur="4" />
                          <note pname="E" oct="2" accid="f" dur="4" />
                          <imaginary awesome="true" />
                      </layer>'''
        elem = ETree.fromstring(inputXML)

        actual = base.layerFromElement(elem, 'so voice ID')

        self.assertEqual(2, len(actual))
        self.assertEqual('so voice ID', actual.id)
        self.assertEqual(0.0, actual[0].offset)
        self.assertEqual(1.0, actual[1].offset)
        self.assertEqual(1.0, actual[0].quarterLength)
        self.assertEqual(1.0, actual[1].quarterLength)
        self.assertEqual('F2', actual[0].nameWithOctave)
        self.assertEqual('E-2', actual[1].nameWithOctave)


    def testIntegration1c(self):
        '''
        (corresponds to testUnit1c() but without mock objects)
        '''
        inputXML = '''<layer xmlns="http://www.music-encoding.org/ns/mei">
                          <note pname="F" oct="2" dur="4" />
                          <note pname="E" oct="2" accid="f" dur="4" />
                          <imaginary awesome="true" />
                      </layer>'''
        elem = ETree.fromstring(inputXML)

        self.assertRaises(base.MeiAttributeError, base.layerFromElement, elem)

        try:
            base.layerFromElement(elem)
        except base.MeiAttributeError as maError:
            self.assertEqual(base._MISSING_VOICE_ID, maError.args[0])



#------------------------------------------------------------------------------
class TestStaffFromElement(unittest.TestCase):
    '''Tests for staffFromElement()'''

    @mock.patch('music21.mei.base.layerFromElement')
    def testUnit1(self, mockLayerFromElement):
        '''
        staffFromElement(): basic functionality (i.e., that layerFromElement() is called with the
                            right arguments, and with properly-incrementing "id" attributes
        (mostly-unit test; only mock noteFromElement and the ElementTree.Element)
        '''
        elem = mock.MagicMock()
        findallReturn = [mock.MagicMock(name='layer1'),
                         mock.MagicMock(name='layer2'),
                         mock.MagicMock(name='layer3')]
        findallReturn[0].tag = '{}layer'.format(base._MEINS)
        findallReturn[1].tag = '{}layer'.format(base._MEINS)
        findallReturn[2].tag = '{}layer'.format(base._MEINS)
        elem.iterfind = mock.MagicMock(return_value=findallReturn)
        # "MLFE" is "mockLayerFromElement"
        expectedMLFEOrder = [mock.call(findallReturn[i], str(i + 1), slurBundle=None)
                             for i in xrange(len(findallReturn))]
        mockLFEreturns = ['mockLayerFromElement return %i' for i in xrange(len(findallReturn))]
        mockLayerFromElement.side_effect = lambda x, y, slurBundle: mockLFEreturns.pop(0)
        expected = ['mockLayerFromElement return %i' for i in xrange(len(findallReturn))]

        actual = base.staffFromElement(elem)

        elem.iterfind.assert_called_once_with('*')
        self.assertEqual(expected, actual)
        self.assertSequenceEqual(expectedMLFEOrder, mockLayerFromElement.call_args_list)

    def testIntegration1(self):
        '''
        staffFromElement(): basic functionality (i.e., that layerFromElement() is called with the
                            right arguments, and with properly-incrementing "id" attributes
        (corresponds to testUnit1() but without mock objects)
        '''
        inputXML = '''<staff xmlns="http://www.music-encoding.org/ns/mei">
                          <layer>
                              <note pname="F" oct="2" dur="4" />
                          </layer>
                          <layer>
                              <note pname="A" oct="2" dur="4" />
                          </layer>
                          <layer>
                              <note pname="C" oct="2" dur="4" />
                          </layer>
                      </staff>'''
        elem = ETree.fromstring(inputXML)

        actual = base.staffFromElement(elem)

        self.assertEqual(3, len(actual))
        # common to each part
        for i in xrange(len(actual)):
            self.assertEqual(1, len(actual[i]))
            self.assertEqual(0.0, actual[i][0].offset)
            self.assertEqual(1.0, actual[i][0].quarterLength)
        # first part
        self.assertEqual('1', actual[0].id)
        self.assertEqual('F2', actual[0][0].nameWithOctave)
        # second part
        self.assertEqual('2', actual[1].id)
        self.assertEqual('A2', actual[1][0].nameWithOctave)
        # third part
        self.assertEqual('3', actual[2].id)
        self.assertEqual('C2', actual[2][0].nameWithOctave)



#------------------------------------------------------------------------------
class TestStaffDefFromElement(unittest.TestCase):
    '''Tests for staffDefFromElement()'''

    @mock.patch('music21.mei.base.instrDefFromElement')
    @mock.patch('music21.mei.base._timeSigFromAttrs')
    @mock.patch('music21.mei.base._keySigFromAttrs')
    @mock.patch('music21.mei.base.clefFromElement')
    @mock.patch('music21.mei.base._transpositionFromAttrs')
    def testUnit1(self, mockTrans, mockClef, mockKey, mockTime, mockInstr):
        '''
        staffDefFromElement(): proper handling of the following attributes (see function docstring
            for more information).

        @label, @label.abbr  @n, @key.accid, @key.mode, @key.pname, @key.sig, @meter.count,
        @meter.unit, @clef.shape, @clef.line, @clef.dis, @clef.dis.place, @trans.diat, @trans.demi
        '''
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS),
                             attrib={'clef.shape': 'F', 'clef.line': '4', 'clef.dis': 'cd',
                                     'clef.dis.place': 'cdp', 'label': 'the label',
                                     'label.abbr': 'the l.', 'n': '1', 'meter.count': '1',
                                     'key.pname': 'G', 'trans.semi': '123'})
        theInstrDef = ETree.Element('{}instrDef'.format(_MEINS),
                                    attrib={'midi.channel': '1', 'midi.instrnum': '71',
                                            'midi.instrname': 'Clarinet'})
        elem.append(theInstrDef)
        theMockInstrument = mock.MagicMock('mock instrument')
        mockInstr.return_value = theMockInstrument
        mockTime.return_value = 'mockTime return'
        mockKey.return_value = 'mockKey return'
        mockClef.return_value = 'mockClef return'
        mockTrans.return_value = 'mockTrans return'
        expected = {'instrument': mockInstr.return_value,
                    'meter': mockTime.return_value,
                    'key': mockKey.return_value,
                    'clef': mockClef.return_value}
        # attributes on theMockInstrument that should be set by staffDefFromElement()
        expectedAttrs = [('partName', 'the label'), ('partAbbreviation', 'the l.'), ('partId', '1'),
                         ('transposition', mockTrans.return_value)]

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertDictEqual(expected, actual)
        mockInstr.assert_called_once_with(theInstrDef)
        mockTime.assert_called_once_with(elem)
        mockKey.assert_called_once_with(elem)
        # mockClef is more difficult because it's given an Element
        mockTrans.assert_called_once_with(elem)
        # check that all attributes are set with their expected values
        for attrName, attrValue in expectedAttrs:
            self.assertEqual(getattr(theMockInstrument, attrName), attrValue)
        # now mockClef, which got an Element
        mockClef.assert_called_once_with(mock.ANY)  # confirm there was a single one-argument call
        mockClefArg = mockClef.call_args_list[0][0][0]
        self.assertEqual('clef', mockClefArg.tag)
        self.assertEqual('F', mockClefArg.get('shape'))
        self.assertEqual('4', mockClefArg.get('line'))
        self.assertEqual('cd', mockClefArg.get('dis'))
        self.assertEqual('cdp', mockClefArg.get('dis.place'))

    def testIntegration1a(self):
        '''
        staffDefFromElement(): corresponds to testUnit1() without mock objects
        '''
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS),
                             attrib={'clef.shape': 'G', 'clef.line': '2', 'n': '12',
                                     'meter.count': '3', 'meter.unit': '8', 'key.sig': '0',
                                     'key.mode': 'major', 'trans.semi': '-3', 'trans.diat': '-2'})
        theInstrDef = ETree.Element('{}instrDef'.format(_MEINS),
                                    attrib={'midi.channel': '1', 'midi.instrnum': '71',
                                            'midi.instrname': 'Clarinet'})
        elem.append(theInstrDef)

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertIsInstance(actual['instrument'], instrument.Clarinet)
        self.assertIsInstance(actual['meter'], meter.TimeSignature)
        self.assertIsInstance(actual['key'], key.KeySignature)
        self.assertIsInstance(actual['clef'], clef.TrebleClef)
        self.assertEqual('12', actual['instrument'].partId)
        self.assertEqual('3/8', actual['meter'].ratioString)
        self.assertEqual('major', actual['key'].mode)
        self.assertEqual(0, actual['key'].sharps)

    def testIntegration1b(self):
        '''
        staffDefFromElement(): testIntegration1() with <clef> tag inside
        '''
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS),
                             attrib={'n': '12', 'meter.count': '3', 'meter.unit': '8', 'key.sig': '0',
                                     'key.mode': 'major', 'trans.semi': '-3', 'trans.diat': '-2'})
        theInstrDef = ETree.Element('{}instrDef'.format(_MEINS),
                                    attrib={'midi.channel': '1', 'midi.instrnum': '71',
                                            'midi.instrname': 'Clarinet'})
        elem.append(theInstrDef)
        elem.append(ETree.Element('{}clef'.format(_MEINS), attrib={'shape': 'G', 'line': '2'}))

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertIsInstance(actual['instrument'], instrument.Clarinet)
        self.assertIsInstance(actual['meter'], meter.TimeSignature)
        self.assertIsInstance(actual['key'], key.KeySignature)
        self.assertIsInstance(actual['clef'], clef.TrebleClef)
        self.assertEqual('12', actual['instrument'].partId)
        self.assertEqual('3/8', actual['meter'].ratioString)
        self.assertEqual('major', actual['key'].mode)
        self.assertEqual(0, actual['key'].sharps)

    @mock.patch('music21.instrument.fromString')
    @mock.patch('music21.mei.base.instrDefFromElement')
    @mock.patch('music21.mei.base._timeSigFromAttrs')
    @mock.patch('music21.mei.base._keySigFromAttrs')
    @mock.patch('music21.mei.base.clefFromElement')
    @mock.patch('music21.mei.base._transpositionFromAttrs')
    def testUnit2(self, mockTrans, mockClef, mockKey, mockTime, mockInstr, mockFromString):
        '''
        staffDefFromElement(): same as testUnit1() *but* there's no <instrDef> so we have to use
            music21.instrument.fromString()
        '''
        # NB: differences from testUnit1() are marked with a "D1" comment at the end of the line
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS),
                             attrib={'clef.shape': 'F', 'clef.line': '4', 'clef.dis': 'cd',
                                     'clef.dis.place': 'cdp', 'label': 'the label',
                                     'label.abbr': 'the l.', 'n': '1', 'meter.count': '1',
                                     'key.pname': 'G', 'trans.semi': '123'})
        theMockInstrument = mock.MagicMock('mock instrument')
        mockFromString.return_value = theMockInstrument  # D1
        mockTime.return_value = 'mockTime return'
        mockKey.return_value = 'mockKey return'
        mockClef.return_value = 'mockClef return'
        mockTrans.return_value = 'mockTrans return'
        expected = {'instrument': mockFromString.return_value,  # D1
                    'meter': mockTime.return_value,
                    'key': mockKey.return_value,
                    'clef': mockClef.return_value}
        # attributes on theMockInstrument that should be set by staffDefFromElement()
        expectedAttrs = [('partName', 'the label'), ('partAbbreviation', 'the l.'), ('partId', '1'),
                         ('transposition', mockTrans.return_value)]

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertDictEqual(expected, actual)
        self.assertEqual(0, mockInstr.call_count)  # D1
        mockTime.assert_called_once_with(elem)
        mockKey.assert_called_once_with(elem)
        # mockClef is more difficult because it's given an Element
        mockTrans.assert_called_once_with(elem)
        # check that all attributes are set with their expected values
        for attrName, attrValue in expectedAttrs:
            self.assertEqual(getattr(theMockInstrument, attrName), attrValue)
        # now mockClef, which got an Element
        mockClef.assert_called_once_with(mock.ANY)  # confirm there was a single one-argument call
        mockClefArg = mockClef.call_args_list[0][0][0]
        self.assertEqual('clef', mockClefArg.tag)
        self.assertEqual('F', mockClefArg.get('shape'))
        self.assertEqual('4', mockClefArg.get('line'))
        self.assertEqual('cd', mockClefArg.get('dis'))
        self.assertEqual('cdp', mockClefArg.get('dis.place'))

    def testIntegration2(self):
        '''
        staffDefFromElement(): corresponds to testUnit2() but without mock objects
        '''
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS),
                             attrib={'n': '12', 'clef.line': '2', 'clef.shape': 'G', 'key.sig': '0',
                                     'key.mode': 'major', 'trans.semi': '-3', 'trans.diat': '-2',
                                     'meter.count': '3', 'meter.unit': '8', 'label': 'clarinet'})

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertIsInstance(actual['instrument'], instrument.Clarinet)
        self.assertIsInstance(actual['meter'], meter.TimeSignature)
        self.assertIsInstance(actual['key'], key.KeySignature)
        self.assertIsInstance(actual['clef'], clef.TrebleClef)
        self.assertEqual('12', actual['instrument'].partId)
        self.assertEqual('3/8', actual['meter'].ratioString)
        self.assertEqual('major', actual['key'].mode)
        self.assertEqual(0, actual['key'].sharps)

    @mock.patch('music21.instrument.Instrument')
    @mock.patch('music21.instrument.fromString')
    @mock.patch('music21.mei.base.instrDefFromElement')
    @mock.patch('music21.mei.base._timeSigFromAttrs')
    @mock.patch('music21.mei.base._keySigFromAttrs')
    @mock.patch('music21.mei.base.clefFromElement')
    @mock.patch('music21.mei.base._transpositionFromAttrs')
    def testUnit3(self, mockTrans, mockClef, mockKey, mockTime, mockInstr, mockFromString, mockInstrInit):
        '''
        staffDefFromElement(): same as testUnit1() *but* there's no <instrDef> so we have to use
          music21.instrument.fromString() *and* that raises an InstrumentException.
        '''
        # NB: differences from testUnit1() are marked with a "D1" comment at the end of the line
        # NB: differences from testUnit2() are marked with a "D2" comment at the end of the line
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS),
                        attrib={'clef.shape': 'F', 'clef.line': '4', 'clef.dis': 'cd',
                                'clef.dis.place': 'cdp', 'label': 'the label',
                                'label.abbr': 'the l.', 'n': '1', 'meter.count': '1',
                                'key.pname': 'G', 'trans.semi': '123'})
        theMockInstrument = mock.MagicMock('mock instrument')
        mockFromString.side_effect = instrument.InstrumentException  # D2
        mockInstrInit.return_value = theMockInstrument  # D1 & D2
        mockTime.return_value = 'mockTime return'
        mockKey.return_value = 'mockKey return'
        mockClef.return_value = 'mockClef return'
        mockTrans.return_value = 'mockTrans return'
        expected = {'instrument': mockInstrInit.return_value,  # D1 & D2
                    'meter': mockTime.return_value,
                    'key': mockKey.return_value,
                    'clef': mockClef.return_value}
        # attributes on theMockInstrument that should be set by staffDefFromElement()
        # NB: because the part name wasn't recognized by music21, there won't be a part name on the
        #     Instrument... the only reason we get an Instrument at all is because of @trans.semi
        expectedAttrs = [('transposition', mockTrans.return_value)]  # D3

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertDictEqual(expected, actual)
        self.assertEqual(0, mockInstr.call_count)  # D1
        mockTime.assert_called_once_with(elem)
        mockKey.assert_called_once_with(elem)
        # mockClef is more difficult because it's given an Element
        mockTrans.assert_called_once_with(elem)
        # check that all attributes are set with their expected values
        for attrName, attrValue in expectedAttrs:
            self.assertEqual(getattr(theMockInstrument, attrName), attrValue)
        # now mockClef, which got an Element
        mockClef.assert_called_once_with(mock.ANY)  # confirm there was a single one-argument call
        mockClefArg = mockClef.call_args_list[0][0][0]
        self.assertEqual('clef', mockClefArg.tag)
        self.assertEqual('F', mockClefArg.get('shape'))
        self.assertEqual('4', mockClefArg.get('line'))
        self.assertEqual('cd', mockClefArg.get('dis'))
        self.assertEqual('cdp', mockClefArg.get('dis.place'))

    def testIntegration3(self):
        '''
        staffDefFromElement(): corresponds to testUnit3() but without mock objects
        '''
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS),
                             attrib={'n': '12', 'clef.line': '2', 'clef.shape': 'G', 'key.sig': '0',
                                     'key.mode': 'major', 'trans.semi': '-3', 'trans.diat': '-2',
                                     'meter.count': '3', 'meter.unit': '8'})

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertIsInstance(actual['instrument'], instrument.Instrument)
        self.assertIsInstance(actual['meter'], meter.TimeSignature)
        self.assertIsInstance(actual['key'], key.KeySignature)
        self.assertIsInstance(actual['clef'], clef.TrebleClef)
        self.assertEqual('3/8', actual['meter'].ratioString)
        self.assertEqual('major', actual['key'].mode)
        self.assertEqual(0, actual['key'].sharps)
        self.assertEqual('m-3', actual['instrument'].transposition.directedName)

    @mock.patch('music21.instrument.Instrument')
    @mock.patch('music21.instrument.fromString')
    @mock.patch('music21.mei.base.instrDefFromElement')
    @mock.patch('music21.mei.base._timeSigFromAttrs')
    @mock.patch('music21.mei.base._keySigFromAttrs')
    @mock.patch('music21.mei.base.clefFromElement')
    @mock.patch('music21.mei.base._transpositionFromAttrs')
    def testUnit4(self, mockTrans, mockClef, mockKey, mockTime, mockInstr, mockFromString, mockInstrInit):
        '''
        staffDefFromElement(): only specifies a meter
        '''
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS), attrib={'meter.count': '1', 'meter.unit': '3'})
        mockTime.return_value = 'mockTime return'
        mockFromString.side_effect = instrument.InstrumentException  # otherwise staffDefFromElement() thinks it got a real Instrument
        expected = {'meter': mockTime.return_value}

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertDictEqual(expected, actual)

    def testIntegration4(self):
        '''
        staffDefFromElement(): corresponds to testUnit3() but without mock objects
        '''
        # 1.) prepare
        elem = ETree.Element('{}staffDef'.format(_MEINS), attrib={'meter.count': '1', 'meter.unit': '3'})

        # 2.) run
        actual = base.staffDefFromElement(elem)

        # 3.) check
        self.assertIsInstance(actual['meter'], meter.TimeSignature)
        self.assertEqual('1/3', actual['meter'].ratioString)

    @mock.patch('music21.mei.base.staffDefFromElement')
    def testStaffGrpUnit1(self, mockStaffDefFE):
        '''
        staffGrpFromElement(): it's not a complicated function!
        '''
        elem = ETree.Element('staffGrp')
        innerElems = [ETree.Element('{}staffDef'.format(_MEINS), attrib={'n': str(n)}) for n in range(4)]
        for eachElem in innerElems:
            elem.append(eachElem)
        mockStaffDefFE.side_effect = lambda x, y: 'processed {}'.format(x.get('n'))
        expected = {str(n): 'processed {}'.format(n) for n in range(4)}

        actual = base.staffGrpFromElement(elem, None)

        self.assertEqual(expected, actual)
        self.assertEqual(len(innerElems), mockStaffDefFE.call_count)
        for eachElem in innerElems:
            mockStaffDefFE.assert_any_call(eachElem, None)

    def testStaffGrpInt1(self):
        '''
        staffGrpFromElement(): we'll use
        '''
        elem = ETree.Element('staffGrp')
        innerElems = [ETree.Element('{}staffDef'.format(_MEINS),
                                    attrib={'n': str(n + 1), 'key.mode': 'major',
                                            'key.sig': '{}f'.format(n + 1)})
                      for n in range(4)]
        for eachElem in innerElems:
            elem.append(eachElem)
        expected = {'1': {'key': key.KeySignature(sharps=-1, mode='major')},
                    '2': {'key': key.KeySignature(sharps=-2, mode='major')},
                    '3': {'key': key.KeySignature(sharps=-3, mode='major')},
                    '4': {'key': key.KeySignature(sharps=-4, mode='major')}}

        actual = base.staffGrpFromElement(elem, None)

        self.assertDictEqual(expected, actual)



#------------------------------------------------------------------------------
class TestScoreDefFromElement(unittest.TestCase):
    '''Tests for scoreDefFromElement()'''

    @mock.patch('music21.mei.base._timeSigFromAttrs')
    @mock.patch('music21.mei.base._keySigFromAttrs')
    def testUnit1(self, mockKey, mockTime):
        '''
        scoreDefFromElement(): proper handling of the following attributes (see function docstring
            for more information).

        @meter.count, @meter.unit, @key.accid, @key.mode, @key.pname, @key.sig
        '''
        # 1.) prepare
        elem = ETree.Element('staffDef', attrib={'key.sig': '4s', 'key.mode': 'major',
                                                 'meter.count': '3', 'meter.unit': '8'})
        mockTime.return_value = 'mockTime return'
        mockKey.return_value = 'mockKey return'
        expected = {'all-part objects': [mockTime.return_value, mockKey.return_value],
                    'whole-score objects': []}

        # 2.) run
        actual = base.scoreDefFromElement(elem)

        # 3.) check
        self.assertEqual(expected, actual)
        mockTime.assert_called_once_with(elem)
        mockKey.assert_called_once_with(elem)

    def testIntegration1(self):
        '''
        scoreDefFromElement(): corresponds to testUnit1() without mock objects
        '''
        # 1.) prepare
        elem = ETree.Element('staffDef', attrib={'key.sig': '4s', 'key.mode': 'major',
                                                 'meter.count': '3', 'meter.unit': '8'})

        # 2.) run
        actual = base.scoreDefFromElement(elem)

        # 3.) check
        self.assertIsInstance(actual['all-part objects'][0], meter.TimeSignature)
        self.assertIsInstance(actual['all-part objects'][1], key.KeySignature)
        self.assertEqual('3/8', actual['all-part objects'][0].ratioString)
        self.assertEqual('major', actual['all-part objects'][1].mode)
        self.assertEqual(4, actual['all-part objects'][1].sharps)

    @mock.patch('music21.mei.base._timeSigFromAttrs')
    @mock.patch('music21.mei.base._keySigFromAttrs')
    @mock.patch('music21.mei.base.staffGrpFromElement')
    def testUnit2(self, mockStaffGrpFE, mockKey, mockTime):
        '''
        scoreDefFromElement(): test for a <staffGrp> held within
        '''
        # 1.) prepare
        elem = ETree.Element('staffDef', attrib={'key.sig': '4s', 'key.mode': 'major',
                                                 'meter.count': '3', 'meter.unit': '8'})
        staffGrp = ETree.Element('{}staffGrp'.format(_MEINS))
        staffDef = ETree.Element('{}staffDef'.format(_MEINS),
                                 attrib={'n': '1', 'label': 'Clarinet'})
        staffGrp.append(staffDef)
        elem.append(staffGrp)
        mockTime.return_value = 'mockTime return'
        mockKey.return_value = 'mockKey return'
        mockStaffGrpFE.return_value = {'1': {'instrument': 'A clarinet'}}  # but is it "any clarinet," or a specific clarinet in A? Ambiguity!
        expected = {'all-part objects': [mockTime.return_value, mockKey.return_value],
                    'whole-score objects': [],
                    '1': {'instrument': 'A clarinet'}}

        # 2.) run
        actual = base.scoreDefFromElement(elem)

        # 3.) check
        self.assertEqual(expected, actual)
        mockTime.assert_called_once_with(elem)
        mockKey.assert_called_once_with(elem)
        mockStaffGrpFE.assert_called_once_with(staffGrp, None)

    def testIntegration2(self):
        '''
        scoreDefFromElement(): corresponds to testUnit2() without mock objects
        '''
        # 1.) prepare
        elem = ETree.Element('staffDef', attrib={'key.sig': '4s', 'key.mode': 'major',
                                                 'meter.count': '3', 'meter.unit': '8'})
        staffGrp = ETree.Element('{}staffGrp'.format(_MEINS))
        staffDef = ETree.Element('{}staffDef'.format(_MEINS),
                                 attrib={'n': '1', 'label': 'Clarinet'})
        staffGrp.append(staffDef)
        elem.append(staffGrp)

        # 2.) run
        actual = base.scoreDefFromElement(elem)

        # 3.) check
        self.assertIsInstance(actual['all-part objects'][0], meter.TimeSignature)
        self.assertIsInstance(actual['all-part objects'][1], key.KeySignature)
        self.assertEqual('3/8', actual['all-part objects'][0].ratioString)
        self.assertEqual('major', actual['all-part objects'][1].mode)
        self.assertEqual(4, actual['all-part objects'][1].sharps)
        self.assertEqual('1', actual['1']['instrument'].partId)
        self.assertEqual('Clarinet', actual['1']['instrument'].partName)
        self.assertIsInstance(actual['1']['instrument'], instrument.Clarinet)



#------------------------------------------------------------------------------
class TestEmbeddedElements(unittest.TestCase):
    '''Tests for _processesEmbeddedElements()'''

    def testUnit1(self):
        '''
        _processesEmbeddedElements(): that single m21 objects are handled properly
        '''
        mockTranslator = mock.MagicMock(return_value='translator return')
        elements = [ETree.Element('note') for _ in xrange(2)]
        mapping = {'note': mockTranslator}
        expected = ['translator return', 'translator return']
        expectedCalls = [mock.call(elements[0], None), mock.call(elements[1], None)]

        actual = base._processEmbeddedElements(elements, mapping)

        self.assertSequenceEqual(expected, actual)
        self.assertSequenceEqual(expectedCalls, mockTranslator.call_args_list)

    def testUnit2(self):
        '''
        _processesEmbeddedElements(): that iterables of m21 objects are handled properly
        '''
        mockTranslator = mock.MagicMock(return_value='translator return')
        mockBeamTranslator = mock.MagicMock(return_value=['embedded 1', 'embedded 2'])
        elements = [ETree.Element('note'), ETree.Element('beam')]
        mapping = {'note': mockTranslator, 'beam': mockBeamTranslator}
        expected = ['translator return', 'embedded 1', 'embedded 2']

        actual = base._processEmbeddedElements(elements, mapping)

        self.assertSequenceEqual(expected, actual)
        mockTranslator.assert_called_once_with(elements[0], None)
        mockBeamTranslator.assert_called_once_with(elements[1], None)

    @mock.patch('music21.mei.base.environLocal')
    def testUnit3(self, mockEnviron):
        '''
        _processesEmbeddedElements(): that un-translated elements are reported properly
        '''
        mockTranslator = mock.MagicMock(return_value='translator return')
        elements = [ETree.Element('note'), ETree.Element('bream')]
        mapping = {'note': mockTranslator}
        callerName = 'ocean'
        expected = ['translator return']
        exp_err = base._UNPROCESSED_SUBELEMENT.format(elements[1].tag, callerName)

        actual = base._processEmbeddedElements(elements, mapping, callerName)

        self.assertSequenceEqual(expected, actual)
        mockTranslator.assert_called_once_with(elements[0], None)
        mockEnviron.printDebug.assert_called_once_with(exp_err)



#------------------------------------------------------------------------------
class TestAddSlurs(unittest.TestCase):
    '''Tests for addSlurs()'''

    def testUnit1(self):
        '''
        addSlurs(): element with @m21SlurStart is handled correctly
        '''
        theUUID = 'ae0b1570-451f-4ee9-a136-2094e26a797b'
        elem = ETree.Element('note', attrib={'m21SlurStart': theUUID,
                                             'm21SlurEnd': None,
                                             'slur': None})
        slurBundle = mock.MagicMock('slur bundle')
        mockNewSlur = mock.MagicMock('mock slur')
        mockNewSlur.addSpannedElements = mock.MagicMock()
        slurBundle.getByIdLocal = mock.MagicMock(return_value=[mockNewSlur])
        obj = mock.MagicMock('object')
        expected = True

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)
        slurBundle.getByIdLocal.assert_called_once_with(theUUID)
        mockNewSlur.addSpannedElements.assert_called_once_with(obj)

    def testIntegration1(self):
        '''
        addSlurs(): element with @m21SlurStart is handled correctly
        '''
        theUUID = 'ae0b1570-451f-4ee9-a136-2094e26a797b'
        elem = ETree.Element('note', attrib={'m21SlurStart': theUUID,
                                             'm21SlurEnd': None,
                                             'slur': None})
        slurBundle = spanner.SpannerBundle()
        theSlur = spanner.Slur()
        theSlur.idLocal = theUUID
        slurBundle.append(theSlur)
        obj = note.Note('E-7', quarterLength=2.0)
        expected = True

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)
        self.assertSequenceEqual([theSlur], slurBundle.list)
        self.assertSequenceEqual([obj], slurBundle.list[0].getSpannedElements())

    def testUnit2(self):
        '''
        addSlurs(): element with @m21SlurEnd is handled correctly
        '''
        theUUID = 'ae0b1570-451f-4ee9-a136-2094e26a797b'
        elem = ETree.Element('note', attrib={'m21SlurStart': None,
                                             'm21SlurEnd': theUUID,
                                             'slur': None})
        slurBundle = mock.MagicMock('slur bundle')
        mockNewSlur = mock.MagicMock('mock slur')
        mockNewSlur.addSpannedElements = mock.MagicMock()
        slurBundle.getByIdLocal = mock.MagicMock(return_value=[mockNewSlur])
        obj = mock.MagicMock('object')
        expected = True

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)
        slurBundle.getByIdLocal.assert_called_once_with(theUUID)
        mockNewSlur.addSpannedElements.assert_called_once_with(obj)

    # NB: skipping testIntegration2() ... if Integration1 and Unit2 work, this probably does too

    @mock.patch('music21.spanner.Slur')
    def testUnit3(self, mockSlur):
        '''
        addSlurs(): element with @slur is handled correctly (both an 'i' and 't' slur)
        '''
        elem = ETree.Element('note', attrib={'m21SlurStart': None,
                                             'm21SlurEnd': None,
                                             'slur': '1i 2t'})
        slurBundle = mock.MagicMock('slur bundle')
        slurBundle.append = mock.MagicMock('slurBundle.append')
        mockSlur.return_value = mock.MagicMock('mock slur')
        mockSlur.return_value.addSpannedElements = mock.MagicMock()
        mockNewSlur = mock.MagicMock('mock new slur')
        mockNewSlur.addSpannedElements = mock.MagicMock()
        slurBundle.getByIdLocal = mock.MagicMock(return_value=[mockNewSlur])
        obj = mock.MagicMock('object')
        expected = True

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)
        slurBundle.append.assert_called_once_with(mockSlur.return_value)
        mockSlur.return_value.addSpannedElements.assert_called_once_with(obj)
        slurBundle.getByIdLocal.assert_called_once_with('2')
        mockNewSlur.addSpannedElements.assert_called_once_with(obj)

    def testIntegration3(self):
        '''
        addSlurs(): element with @slur is handled correctly (both an 'i' and 't' slur)
        '''
        elem = ETree.Element('note', attrib={'m21SlurStart': None,
                                             'm21SlurEnd': None,
                                             'slur': '1i 2t'})
        slurBundle = spanner.SpannerBundle()
        theSlur = spanner.Slur()
        theSlur.idLocal = '2'
        slurBundle.append(theSlur)
        obj = note.Note('E-7', quarterLength=2.0)
        expected = True

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)
        self.assertSequenceEqual([theSlur, mock.ANY], slurBundle.list)
        self.assertIsInstance(slurBundle.list[1], spanner.Slur)
        self.assertSequenceEqual([obj], slurBundle.list[0].getSpannedElements())
        self.assertSequenceEqual([obj], slurBundle.list[1].getSpannedElements())

    def testUnit4(self):
        '''
        addSlurs(): nothing was added; all three slur-related attributes missing
        '''
        elem = ETree.Element('note', attrib={'m21SlurStart': None,
                                             'm21SlurEnd': None,
                                             'slur': None})
        slurBundle = mock.MagicMock('slur bundle')
        obj = mock.MagicMock('object')
        expected = False

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)

    def testUnit5(self):
        '''
        addSlurs(): nothing was added; @slur is present, but only "medial" indicators
        '''
        elem = ETree.Element('note', attrib={'m21SlurStart': None,
                                             'm21SlurEnd': None,
                                             'slur': '1m 2m'})
        slurBundle = mock.MagicMock('slur bundle')
        obj = mock.MagicMock('object')
        expected = False

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)

    def testUnit6(self):
        '''
        addSlurs(): nothing was added; when the Slur with id of @m21SlurStart can't be found

        NB: this tests that the inner function works---catching the IndexError
        '''
        elem = ETree.Element('note', attrib={'m21SlurStart': '07f5513a-436a-4247-8a5d-85c10c661920',
                                             'm21SlurEnd': None,
                                             'slur': None})
        slurBundle = mock.MagicMock('slur bundle')
        slurBundle.getByIdLocal = mock.MagicMock(side_effect=IndexError)
        obj = mock.MagicMock('object')
        expected = False

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)

    def testIntegration6(self):
        '''
        addSlurs(): nothing was added; when the Slur with id of @m21SlurStart can't be found

        NB: this tests that the inner function works---catching the IndexError
        '''
        elem = ETree.Element('note', attrib={'m21SlurStart': '07f5513a-436a-4247-8a5d-85c10c661920',
                                             'm21SlurEnd': None,
                                             'slur': None})
        slurBundle = spanner.SpannerBundle()
        obj = note.Note('E-7', quarterLength=2.0)
        expected = False

        actual = base.addSlurs(elem, obj, slurBundle)

        self.assertEqual(expected, actual)
        self.assertSequenceEqual([], slurBundle.list)



#------------------------------------------------------------------------------
class TestBeams(unittest.TestCase):
    '''Tests for beams in all their guises.'''

    def testBeamTogether1(self):
        '''
        beamTogether(): with three mock objects, that their "beams" attributes are set properly
        '''
        someThings = [mock.MagicMock() for _ in range(3)]
        for i in xrange(len(someThings)):
            someThings[i].beams = mock.MagicMock('thing {} beams'.format(i))
            someThings[i].beams.__len__.return_value = 0
            someThings[i].beams.fill = mock.MagicMock()
            someThings[i].beams.setAll = mock.MagicMock()
            someThings[i].duration.type = '16th'
        expectedTypes = ['start', 'continue', 'continue']  # first call with "continue"; corrected later in function

        base.beamTogether(someThings)

        for i in xrange(len(someThings)):
            someThings[i].beams.__len__.assert_called_once_with()
            someThings[i].beams.fill.assert_called_once_with('16th', expectedTypes[i])
        someThings[2].beams.setAll.assert_called_once_with('stop')

    def testBeamTogether2(self):
        '''
        beamTogether(): with four mock objects, the middle two of which already have "beams" set
        '''
        someThings = [mock.MagicMock() for _ in range(4)]
        for i in xrange(len(someThings)):
            someThings[i].beams = mock.MagicMock('thing {} beams'.format(i))
            someThings[i].beams.__len__.return_value = 0
            someThings[i].beams.fill = mock.MagicMock()
            someThings[i].beams.setAll = mock.MagicMock()
            someThings[i].duration.type = '16th'
        expectedTypes = ['start', None, None, 'continue']  # first call with "continue"; corrected later in function
        # modifications for test 2
        someThings[1].beams.__len__.return_value = 2
        someThings[2].beams.__len__.return_value = 2

        base.beamTogether(someThings)

        for i in [0, 3]:
            someThings[i].beams.__len__.assert_called_once_with()
            someThings[i].beams.fill.assert_called_once_with('16th', expectedTypes[i])
        someThings[3].beams.setAll.assert_called_once_with('stop')
        for i in [1, 2]:
            self.assertEqual(0, someThings[i].beams.fill.call_count)
            self.assertEqual(0, someThings[i].beams.setAll.call_count)

    def testBeamTogether3(self):
        '''
        beamTogether(): with four mock objects, one of which doesn't have a "beams" attribute
        '''
        someThings = [mock.MagicMock() for _ in range(4)]
        someThings[2] = 5  # this will cause failure if the function tries to set "beams"
        for i in [0, 1, 3]:
            someThings[i].beams = mock.MagicMock('thing {} beams'.format(i))
            someThings[i].beams.__len__.return_value = 0
            someThings[i].beams.fill = mock.MagicMock()
            someThings[i].beams.setAll = mock.MagicMock()
            someThings[i].duration.type = '16th'
        expectedTypes = ['start', 'continue', None, 'continue']  # first call with "continue"; corrected later in function

        base.beamTogether(someThings)

        for i in [0, 1, 3]:
            someThings[i].beams.__len__.assert_called_once_with()
            someThings[i].beams.fill.assert_called_once_with('16th', expectedTypes[i])
        someThings[3].beams.setAll.assert_called_once_with('stop')



#------------------------------------------------------------------------------
class TestPreprocessors(unittest.TestCase):
    '''Tests for the preprocessing helper functions for convertFromString().'''

    def testUnitTies1(self):
        '''
        _ppTies(): that three ties are specified correctly in the m21Attr
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}tie'.format(mei=_MEINS)
        iterfindReturn = []
        for i in xrange(3):
            iterfindReturn.append(ETree.Element('tie', attrib={'startid': 'start {}'.format(i),
                                                               'endid': 'end {}'.format(i)}))
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)

        base._ppTies(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check all the right values were added to the m21Attr dict
        for i in xrange(3):
            self.assertEqual('i', mockConverter.m21Attr['start {}'.format(i)]['tie'])
            self.assertEqual('t', mockConverter.m21Attr['end {}'.format(i)]['tie'])

    @mock.patch('music21.mei.base.environLocal')
    def testUnitTies2(self, mockEnviron):
        '''
        _ppTies(): <tie> without @startid and @endid is properly announced as failing
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}tie'.format(mei=_MEINS)
        iterfindReturn = [ETree.Element('tie', attrib={'tstamp': '4.1', 'tstamp2': '4.2'})]
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)

        base._ppTies(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check all the right values were added to the m21Attr dict
        self.assertEqual(0, len(mockConverter.m21Attr))
        mockEnviron.warn.assert_called_once_with('Importing <tie> without @startid and @endid is not yet supported.')

    @mock.patch('music21.spanner.Slur')
    def testUnitSlurs1(self, mockSlur):
        '''
        _ppSlurs(): that three slurs are specified correctly in the m21Attr, and put in the slurBundle
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}slur'.format(mei=_MEINS)
        iterfindReturn = []
        for i in xrange(3):
            iterfindReturn.append(ETree.Element('slur',
                                                attrib={'startid': 'start {}'.format(i),
                                                        'endid': 'end {}'.format(i)}))
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)
        mockSlur.side_effect = lambda: mock.MagicMock('a fake Slur')
        # the "slurBundle" only needs to support append(), so this can serve as our mock object
        mockConverter.slurBundle = []

        base._ppSlurs(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check things in the slurBundle
        expectedIdLocal = []
        self.assertEqual(3, len(mockConverter.slurBundle))
        for eachSlur in mockConverter.slurBundle:
            self.assertIsInstance(eachSlur, mock.MagicMock)
            self.assertEqual(36, len(eachSlur.idLocal))
            expectedIdLocal.append(eachSlur.idLocal)
        # check all the right values were added to the m21Attr dict
        for i in xrange(3):
            self.assertTrue(mockConverter.m21Attr['start {}'.format(i)]['m21SlurStart'] in expectedIdLocal)
            self.assertTrue(mockConverter.m21Attr['end {}'.format(i)]['m21SlurEnd'] in expectedIdLocal)

    @mock.patch('music21.spanner.Slur')
    @mock.patch('music21.mei.base.environLocal')
    def testUnitSlurs2(self, mockEnviron, mockSlur):
        '''
        _ppSlurs(): <slur> without @startid and @endid is properly announced as failing
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}slur'.format(mei=_MEINS)
        iterfindReturn = [ETree.Element('slur', attrib={'tstamp': '4.1', 'tstamp2': '4.3'})]
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)
        mockSlur.side_effect = lambda: mock.MagicMock('a fake Slur')
        # the "slurBundle" only needs to support append(), so this can serve as our mock object
        mockConverter.slurBundle = []

        base._ppSlurs(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check things in the slurBundle
        self.assertEqual(0, len(mockConverter.slurBundle))
        # check all the right values were added to the m21Attr dict
        self.assertEqual(0, len(mockConverter.m21Attr))
        mockEnviron.warn.assert_called_once_with('Importing <slur> without @startid and @endid is not yet supported.')

    def testUnitBeams1(self):
        '''
        _ppBeams(): that three beamed notes are specified correctly in the m21Attr

        with @plist
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}beamSpan'.format(mei=_MEINS)
        iterfindReturn = []
        for i in xrange(3):
            iterfindReturn.append(ETree.Element('beamSpan',
                                                attrib={'startid': 'start-{}'.format(i),
                                                        'endid': 'end-{}'.format(i),
                                                        'plist': '#start-{j} #mid-{j} #end-{j}'.format(j=i)}))
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)

        base._ppBeams(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check all the right values were added to the m21Attr dict
        for i in xrange(3):
            self.assertEqual('start', mockConverter.m21Attr['start-{}'.format(i)]['m21Beam'])
            self.assertEqual('continue', mockConverter.m21Attr['mid-{}'.format(i)]['m21Beam'])
            self.assertEqual('stop', mockConverter.m21Attr['end-{}'.format(i)]['m21Beam'])

    def testUnitBeams2(self):
        '''
        _ppBeams(): that three beamed notes are specified correctly in the m21Attr

        without @plist
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}beamSpan'.format(mei=_MEINS)
        iterfindReturn = []
        for i in xrange(3):
            iterfindReturn.append(ETree.Element('beamSpan',
                                                attrib={'startid': '#start-{}'.format(i),
                                                        'endid': '#end-{}'.format(i)}))
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)

        base._ppBeams(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check all the right values were added to the m21Attr dict
        for i in xrange(3):
            self.assertEqual('start', mockConverter.m21Attr['start-{}'.format(i)]['m21Beam'])
            self.assertEqual('stop', mockConverter.m21Attr['end-{}'.format(i)]['m21Beam'])

    @mock.patch('music21.mei.base.environLocal')
    def testUnitBeams3(self, mockEnviron):
        '''
        _ppBeams(): <beamSpan> without @startid and @endid is properly announced as failing
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}beamSpan'.format(mei=_MEINS)
        iterfindReturn = [ETree.Element('beamSpan', attrib={'tstamp': '12.4', 'tstamp2': '13.1'})]
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)

        base._ppBeams(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check all the right values were added to the m21Attr dict
        self.assertEqual(0, len(mockConverter.m21Attr))
        mockEnviron.warn.assert_called_once_with('Importing <beamSpan> without @startid and @endid is not yet supported.')

    def testUnitTuplets1(self):
        '''
        _ppTuplets(): that three notes in a tuplet are specified correctly in the m21Attr

        with @plist
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}tupletSpan'.format(mei=_MEINS)
        theNum = 42
        theNumbase = 900
        iterfindReturn = []
        for i in xrange(3):
            iterfindReturn.append(ETree.Element('tupletSpan',
                                                attrib={'plist': '#start-{j} #mid-{j} #end-{j}'.format(j=i),
                                                        'num': theNum,
                                                        'numbase': theNumbase}))
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)

        base._ppTuplets(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check all the right values were added to the m21Attr dict
        for i in xrange(3):
            self.assertEqual(theNum, mockConverter.m21Attr['start-{}'.format(i)]['m21TupletNum'])
            self.assertEqual(theNumbase, mockConverter.m21Attr['start-{}'.format(i)]['m21TupletNumbase'])
            self.assertEqual(theNum, mockConverter.m21Attr['mid-{}'.format(i)]['m21TupletNum'])
            self.assertEqual(theNumbase, mockConverter.m21Attr['mid-{}'.format(i)]['m21TupletNumbase'])
            self.assertEqual(theNum, mockConverter.m21Attr['end-{}'.format(i)]['m21TupletNum'])
            self.assertEqual(theNumbase, mockConverter.m21Attr['end-{}'.format(i)]['m21TupletNumbase'])

    @mock.patch('music21.mei.base.environLocal')
    def testUnitTuplets2(self, mockEnviron):
        '''
        _ppTuplets(): <tupletSpan> without (@startid and @endid) or @plist is properly announced as failing
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}tupletSpan'.format(mei=_MEINS)
        theNum = 42
        theNumbase = 900
        iterfindReturn = [ETree.Element('tupletSpan', attrib={'num': theNum, 'numbase': theNumbase})]
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)
        expWarning = 'Importing <tupletSpan> without @startid and @endid or @plist is not yet supported.'

        base._ppTuplets(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check all the right values were added to the m21Attr dict
        self.assertEqual(0, len(mockConverter.m21Attr))
        mockEnviron.warn.assert_called_once_with(expWarning)

    def testUnitTuplets3(self):
        '''
        _ppTuplets(): that three notes in a tuplet are specified correctly in the m21Attr

        without @plist (this should set @m21TupletSearch attributes)
        '''
        # NB: I'm mocking out the documentRoot because setting up an element tree for a unit test
        #     is much more work than it's worth
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.documentRoot = mock.MagicMock()
        expectedIterfind = './/{mei}music//{mei}score//{mei}tupletSpan'.format(mei=_MEINS)
        theNum = 42
        theNumbase = 900
        iterfindReturn = []
        for i in xrange(3):
            iterfindReturn.append(ETree.Element('tupletSpan',
                                                attrib={'startid': '#start-{j}'.format(j=i),
                                                        'endid': '#end-{j}'.format(j=i),
                                                        'num': theNum,
                                                        'numbase': theNumbase}))
        mockConverter.documentRoot.iterfind = mock.MagicMock(return_value=iterfindReturn)

        base._ppTuplets(mockConverter)

        mockConverter.documentRoot.iterfind.assert_called_once_with(expectedIterfind)
        # check all the right values were added to the m21Attr dict
        for i in (0, 2):
            self.assertEqual(theNum, mockConverter.m21Attr['start-{}'.format(i)]['m21TupletNum'])
            self.assertEqual(theNumbase, mockConverter.m21Attr['start-{}'.format(i)]['m21TupletNumbase'])
            self.assertEqual('start', mockConverter.m21Attr['start-{}'.format(i)]['m21TupletSearch'])
            self.assertEqual(theNum, mockConverter.m21Attr['end-{}'.format(i)]['m21TupletNum'])
            self.assertEqual(theNumbase, mockConverter.m21Attr['end-{}'.format(i)]['m21TupletNumbase'])
            self.assertEqual('end', mockConverter.m21Attr['end-{}'.format(i)]['m21TupletSearch'])

    def testUnitConclude1(self):
        '''
        _ppConclude(): that it works
        '''
        theDocument = '''<mei><music><note xml:id="one"/><note xml:id="two"/></music></mei>'''
        mockConverter = mock.MagicMock(spec_set=base.MeiToM21Converter())
        mockConverter.documentRoot = ETree.fromstring(theDocument)
        mockConverter.m21Attr = defaultdict(lambda: {})
        mockConverter.m21Attr['one']['new'] = '14'
        mockConverter.m21Attr['one']['other'] = '42'
        expNoteOneAttrib = {_XMLID: 'one', 'new': '14', 'other': '42'}
        expNoteTwoAttrib = {_XMLID: 'two'}

        base._ppConclude(mockConverter)

        noteOne = mockConverter.documentRoot.find('*//*[@{}="one"]'.format(_XMLID))
        noteTwo = mockConverter.documentRoot.find('*//*[@{}="two"]'.format(_XMLID))
        self.assertEqual(expNoteOneAttrib, noteOne.attrib)
        self.assertEqual(expNoteTwoAttrib, noteTwo.attrib)


#------------------------------------------------------------------------------
class TestTuplets(unittest.TestCase):
    '''Tests for the tuplet-processing helper function, scaleToTuplet().'''

    def testTuplets1(self):
        '''
        scaleToTuplet(): with three objects, the "tuplet search" attributes are set properly.
        '''
        objs = [mock.MagicMock(spec=note.Note()) for _ in range(3)]
        elem = ETree.Element('tupletDef', attrib={'m21TupletNum': '12', 'm21TupletNumbase': '400',
                                                  'm21TupletSearch': 'the forest'})

        base.scaleToTuplet(objs, elem)

        for obj in objs:
            self.assertEqual('12', obj.m21TupletNum)
            self.assertEqual('400', obj.m21TupletNumbase)
            self.assertEqual('the forest', obj.m21TupletSearch)

    @mock.patch('music21.duration.Tuplet')
    def testTuplets2(self, mockTuplet):
        '''
        scaleToTuplet(): with three objects, their duration is scaled properly. (With @m21TupletType).
        '''
        objs = [mock.MagicMock(spec=note.Note()) for _ in range(3)]
        for obj in objs:
            obj.duration = mock.MagicMock()
            obj.duration.type = 'duration type'
            obj.duration.tuplets = [mock.MagicMock()]
        elem = ETree.Element('tupletDef', attrib={'m21TupletNum': '12', 'm21TupletNumbase': '400',
                                                  'm21TupletType': 'banana'})
        mockTuplet.return_value = 'a Tuplet'
        expectedCall = mock.call(numberNotesActual=12, durationActual='duration type',
                                 numberNotesNormal=400, durationNormal='duration type')

        base.scaleToTuplet(objs, elem)

        self.assertEqual(3, mockTuplet.call_count)
        for eachCall in mockTuplet.call_args_list:
            self.assertEqual(expectedCall, eachCall)
        for obj in objs:
            self.assertEqual('banana', obj.duration.tuplets[0].type)

    @mock.patch('music21.duration.Tuplet')
    def testTuplets3(self, mockTuplet):
        '''
        scaleToTuplet(): with three objects, their duration is scaled properly. (With @tuplet == 'i1').
        '''
        objs = [mock.MagicMock(spec=note.Note()) for _ in range(3)]
        for obj in objs:
            obj.duration = mock.MagicMock()
            obj.duration.type = 'duration type'
            obj.duration.tuplets = [mock.MagicMock()]
        elem = ETree.Element('tupletDef', attrib={'m21TupletNum': '12', 'm21TupletNumbase': '400',
                                                  'tuplet': 'i1'})
        mockTuplet.return_value = 'a Tuplet'
        expectedCall = mock.call(numberNotesActual=12, durationActual='duration type',
                                 numberNotesNormal=400, durationNormal='duration type')

        base.scaleToTuplet(objs, elem)

        self.assertEqual(3, mockTuplet.call_count)
        for eachCall in mockTuplet.call_args_list:
            self.assertEqual(expectedCall, eachCall)
        for obj in objs:
            self.assertEqual('start', obj.duration.tuplets[0].type)

    @mock.patch('music21.duration.Tuplet')
    def testTuplets4(self, mockTuplet):
        '''
        scaleToTuplet(): with one object, its duration is scaled properly. (With @tuplet == 't1').
        '''
        obj = mock.MagicMock(spec=note.Note())
        obj.duration = mock.MagicMock()
        obj.duration.type = 'duration type'
        obj.duration.tuplets = [mock.MagicMock()]
        elem = ETree.Element('tupletDef', attrib={'m21TupletNum': '12', 'm21TupletNumbase': '400',
                                                  'tuplet': 't1'})
        mockTuplet.return_value = 'a Tuplet'
        expectedCall = mock.call(numberNotesActual=12, durationActual='duration type',
                                 numberNotesNormal=400, durationNormal='duration type')

        base.scaleToTuplet(obj, elem)

        self.assertEqual(1, mockTuplet.call_count)
        self.assertEqual(expectedCall, mockTuplet.call_args_list[0])
        self.assertEqual('stop', obj.duration.tuplets[0].type)

    @mock.patch('music21.duration.Tuplet')
    def testTuplets5(self, mockTuplet):
        '''
        scaleToTuplet(): with three objects, their duration is scaled properly. (One of the objects
        isn't a Note/Chord/Rest).
        '''
        objs = [mock.MagicMock(spec=note.Note()) for _ in range(3)]
        for obj in objs:
            obj.duration = mock.MagicMock()
            obj.duration.type = 'duration type'
            obj.duration.tuplets = [mock.MagicMock()]
        objs[1] = mock.MagicMock(spec=clef.TrebleClef())
        elem = ETree.Element('tupletDef', attrib={'m21TupletNum': '12', 'm21TupletNumbase': '400',
                                                  'tuplet': 'i1'})
        mockTuplet.return_value = 'a Tuplet'
        expectedCall = mock.call(numberNotesActual=12, durationActual='duration type',
                                 numberNotesNormal=400, durationNormal='duration type')

        base.scaleToTuplet(objs, elem)

        self.assertEqual(2, mockTuplet.call_count)
        for eachCall in mockTuplet.call_args_list:
            self.assertEqual(expectedCall, eachCall)
        self.assertEqual('start', objs[0].duration.tuplets[0].type)
        self.assertEqual([], objs[1].duration.call_args_list)
        self.assertEqual('start', objs[2].duration.tuplets[0].type)

    def testTuplets6(self):
        '''
        tupletFromElement(): when either @num or @numbase isn't in the element, raise an
            MeiAttributeError.
        '''
        # missing @numbase
        elem = ETree.Element('tuplet', attrib={'num': '3'})
        self.assertRaises(base.MeiAttributeError, base.tupletFromElement, elem)
        try:
            base.tupletFromElement(elem)
        except base.MeiAttributeError as err:
            self.assertEqual(base._MISSING_TUPLET_DATA, err.args[0])
        # missing @num
        elem = ETree.Element('tuplet', attrib={'numbase': '2'})
        self.assertRaises(base.MeiAttributeError, base.tupletFromElement, elem)
        try:
            base.tupletFromElement(elem)
        except base.MeiAttributeError as err:
            self.assertEqual(base._MISSING_TUPLET_DATA, err.args[0])

    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.scaleToTuplet')
    @mock.patch('music21.mei.base.beamTogether')
    def testTuplets7(self, mockBeam, mockTuplet, mockEmbedded):  # pylint: disable=unused-argument
        '''
        tupletFromElement(): everything set properly in a triplet; no extraneous elements
        '''
        elem = ETree.Element('tuplet', attrib={'num': '3', 'numbase': '2'})
        mockNotes = [mock.MagicMock(spec=note.Note()) for _ in range(3)]
        for obj in mockNotes:
            obj.duration.tuplets = [mock.MagicMock(spec=duration.Tuplet())]
            obj.duration.tuplets[0].type = 'default'
        mockTuplet.return_value = mockNotes
        mockBeam.side_effect = lambda x: x

        actual = base.tupletFromElement(elem)

        self.assertSequenceEqual(mockNotes, actual)
        mockBeam.assert_called_once_with(mockNotes)
        self.assertEqual('start', mockNotes[0].duration.tuplets[0].type)
        self.assertEqual('default', mockNotes[1].duration.tuplets[0].type)
        self.assertEqual('stop', mockNotes[2].duration.tuplets[0].type)

    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.scaleToTuplet')
    @mock.patch('music21.mei.base.beamTogether')
    def testTuplets8(self, mockBeam, mockTuplet, mockEmbedded):  # pylint: disable=unused-argument
        '''
        tupletFromElement(): everything set properly in a triplet; extraneous elements interposed
        '''
        # NB: elements 0, 3, and 5 are the Notes; elements 1, 2, and 4 are not
        elem = ETree.Element('tuplet', attrib={'num': '3', 'numbase': '2'})
        mockNotes = [mock.MagicMock(spec=note.Note()) for _ in range(6)]
        for obj in mockNotes:
            obj.duration.tuplets = [mock.MagicMock(spec=duration.Tuplet())]
            obj.duration.tuplets[0].type = 'default'
        for i in (1, 2, 4):
            mockNotes[i] = mock.MagicMock(spec=clef.TrebleClef())
        mockTuplet.return_value = mockNotes
        mockBeam.side_effect = lambda x: x

        actual = base.tupletFromElement(elem)

        self.assertSequenceEqual(mockNotes, actual)
        mockBeam.assert_called_once_with(mockNotes)
        self.assertEqual('start', mockNotes[0].duration.tuplets[0].type)
        self.assertEqual('default', mockNotes[3].duration.tuplets[0].type)
        self.assertEqual('stop', mockNotes[5].duration.tuplets[0].type)

    @mock.patch('music21.mei.base._processEmbeddedElements')
    @mock.patch('music21.mei.base.scaleToTuplet')
    @mock.patch('music21.mei.base.beamTogether')
    def testTuplets9(self, mockBeam, mockTuplet, mockEmbedded):  # pylint: disable=unused-argument
        '''
        tupletFromElement(): everything set properly in a triplet; extraneous elements interposed,
            prepended, and appended
        '''
        # NB: elements 1, 4, and 6 are the Notes; elements 0, 2, 3, 5, and 7 are not
        elem = ETree.Element('tuplet', attrib={'num': '3', 'numbase': '2'})
        mockNotes = [mock.MagicMock(spec=note.Note()) for _ in range(8)]
        for obj in mockNotes:
            obj.duration.tuplets = [mock.MagicMock(spec=duration.Tuplet())]
            obj.duration.tuplets[0].type = 'default'
        for i in (0, 2, 3, 5, 7):
            mockNotes[i] = mock.MagicMock(spec=clef.TrebleClef())
        mockTuplet.return_value = mockNotes
        mockBeam.side_effect = lambda x: x

        actual = base.tupletFromElement(elem)

        self.assertSequenceEqual(mockNotes, actual)
        mockBeam.assert_called_once_with(mockNotes)
        self.assertEqual('start', mockNotes[1].duration.tuplets[0].type)
        self.assertEqual('default', mockNotes[4].duration.tuplets[0].type)
        self.assertEqual('stop', mockNotes[6].duration.tuplets[0].type)

    def testTuplet10(self):
        '''
        _guessTuplets(): given a list of stuff without tuplet-guessing attributes, make no changes
        '''
        theLayer = [note.Note(quarterLength=1.0) for _ in xrange(5)]
        expectedDurs = [1.0 for _ in xrange(5)]

        actual = base._guessTuplets(theLayer)  # pylint: disable=protected-access

        for i in xrange(len(expectedDurs)):
            self.assertEqual(expectedDurs[i], actual[i].quarterLength)

    def testTuplet11a(self):
        '''
        _guessTuplets(): with 5 notes, a triplet at the beginning is done correctly
        '''
        theLayer = [note.Note(quarterLength=1.0) for _ in xrange(5)]
        theLayer[0].m21TupletSearch = 'start'
        theLayer[0].m21TupletNum = '3'
        theLayer[0].m21TupletNumbase = '2'
        theLayer[2].m21TupletSearch = 'end'
        theLayer[2].m21TupletNum = '3'
        theLayer[2].m21TupletNumbase = '2'
        expectedDurs = [Fraction(2, 3), Fraction(2, 3), Fraction(2, 3), 1.0, 1.0]

        actual = base._guessTuplets(theLayer)  # pylint: disable=protected-access

        for i in xrange(len(expectedDurs)):
            self.assertEqual(expectedDurs[i], actual[i].quarterLength)
        for i in [0, 2]:
            self.assertFalse(hasattr(theLayer[i], 'm21TupletSearch'))
            self.assertFalse(hasattr(theLayer[i], 'm21TupletNum'))
            self.assertFalse(hasattr(theLayer[i], 'm21TupletNumbase'))

    def testTuplet11b(self):
        '''
        _guessTuplets(): with 5 notes, a triplet in the middle is done correctly
        '''
        theLayer = [note.Note(quarterLength=1.0) for _ in xrange(5)]
        theLayer[1].m21TupletSearch = 'start'
        theLayer[1].m21TupletNum = '3'
        theLayer[1].m21TupletNumbase = '2'
        theLayer[3].m21TupletSearch = 'end'
        theLayer[3].m21TupletNum = '3'
        theLayer[3].m21TupletNumbase = '2'
        expectedDurs = [1.0, Fraction(2, 3), Fraction(2, 3), Fraction(2, 3), 1.0]

        actual = base._guessTuplets(theLayer)  # pylint: disable=protected-access

        for i in xrange(len(expectedDurs)):
            self.assertEqual(expectedDurs[i], actual[i].quarterLength)
        for i in [1, 3]:
            self.assertFalse(hasattr(theLayer[i], 'm21TupletSearch'))
            self.assertFalse(hasattr(theLayer[i], 'm21TupletNum'))
            self.assertFalse(hasattr(theLayer[i], 'm21TupletNumbase'))

    def testTuplet11c(self):
        '''
        _guessTuplets(): with 5 notes, a triplet at the end is done correctly
        '''
        theLayer = [note.Note(quarterLength=1.0) for _ in xrange(5)]
        theLayer[2].m21TupletSearch = 'start'
        theLayer[2].m21TupletNum = '3'
        theLayer[2].m21TupletNumbase = '2'
        theLayer[4].m21TupletSearch = 'end'
        theLayer[4].m21TupletNum = '3'
        theLayer[4].m21TupletNumbase = '2'
        expectedDurs = [1.0, 1.0, Fraction(2, 3), Fraction(2, 3), Fraction(2, 3)]

        actual = base._guessTuplets(theLayer)  # pylint: disable=protected-access

        for i in xrange(len(expectedDurs)):
            self.assertEqual(expectedDurs[i], actual[i].quarterLength)
        for i in [2, 4]:
            self.assertFalse(hasattr(theLayer[i], 'm21TupletSearch'))
            self.assertFalse(hasattr(theLayer[i], 'm21TupletNum'))
            self.assertFalse(hasattr(theLayer[i], 'm21TupletNumbase'))


#------------------------------------------------------------------------------
class TestInstrDef(unittest.TestCase):
    '''Tests for instrDefFromElement().'''

    @mock.patch('music21.instrument.instrumentFromMidiProgram')
    def testUnit1(self, mockFromProg):
        '''instrDefFromElement(): when @midi.instrnum is given'''
        elem = ETree.Element('instrDef', attrib={'midi.instrnum': '71'})
        expFromProgArg = 71
        mockFromProg.return_value = 'Guess Which Instrument'
        expected = mockFromProg.return_value

        actual = base.instrDefFromElement(elem)

        self.assertEqual(expected, actual)
        mockFromProg.assert_called_once_with(expFromProgArg)

    @mock.patch('music21.instrument.fromString')
    def testUnit2(self, mockFromString):
        '''instrDefFromElement(): when @midi.instrname is given, and it works'''
        elem = ETree.Element('instrDef', attrib={'midi.instrname': 'Tuba'})
        expFromStringArg = 'Tuba'
        mockFromString.return_value = "That's right: tuba"
        expected = mockFromString.return_value

        actual = base.instrDefFromElement(elem)

        self.assertEqual(expected, actual)
        mockFromString.assert_called_once_with(expFromStringArg)

    @mock.patch('music21.mei.base.instrument')
    def testUnit3a(self, mockInstr):
        '''instrDefFromElement(): when @midi.instrname is given, and it explodes (AttributeError)'''
        # For Py3 we have to replace the exception, since it's not okay to catch classes that don't
        # inherit from BaseException (which a MagicMock obviously doesn't)
        mockInstr.InstrumentException = instrument.InstrumentException
        elem = ETree.Element('instrDef', attrib={'midi.instrname': 'Gold-Plated Kazoo'})
        expFromStringArg = 'Gold-Plated Kazoo'
        mockInstr.fromString = mock.MagicMock()
        mockInstr.fromString.side_effect = AttributeError
        mockInstr.Instrument.return_value = mock.MagicMock()
        mockInstr.Instrument.return_value.partName = None
        expected = mockInstr.Instrument.return_value

        actual = base.instrDefFromElement(elem)

        self.assertEqual(expected, actual)
        mockInstr.fromString.assert_called_once_with(expFromStringArg)
        self.assertEqual(expFromStringArg, actual.partName)

    @mock.patch('music21.mei.base.instrument')
    def testUnit3b(self, mockInstr):
        '''instrDefFromElement(): when @midi.instrname is given, and it explodes (InstrumentException)'''
        # For Py3 we have to replace the exception, since it's not okay to catch classes that don't
        # inherit from BaseException (which a MagicMock obviously doesn't)
        mockInstr.InstrumentException = instrument.InstrumentException
        elem = ETree.Element('instrDef', attrib={'midi.instrname': 'Gold-Plated Kazoo'})
        expFromStringArg = 'Gold-Plated Kazoo'
        mockInstr.fromString = mock.MagicMock()
        mockInstr.fromString.side_effect = instrument.InstrumentException
        mockInstr.Instrument.return_value = mock.MagicMock()
        mockInstr.Instrument.return_value.partName = None
        expected = mockInstr.Instrument.return_value

        actual = base.instrDefFromElement(elem)

        self.assertEqual(expected, actual)
        mockInstr.fromString.assert_called_once_with(expFromStringArg)
        self.assertEqual(expFromStringArg, actual.partName)


#------------------------------------------------------------------------------
class TestMeasureFromElement(unittest.TestCase):
    '''Tests for measureFromElement() and its helper functions.'''

    def testMakeBarline1(self):
        '''
        _makeBarlines(): when @left and @right are None, nothing happens
        '''
        elem = ETree.Element('measure')
        staves = {'1': stream.Measure(), '2': stream.Measure(), '3': stream.Measure(), '4': 4}

        staves = base._makeBarlines(elem, staves)

        for i in ('1', '2', '3'):
            self.assertIsNone(staves[i].leftBarline)
            self.assertIsNone(staves[i].rightBarline)
        self.assertEqual(4, staves['4'])

    def testMakeBarline2(self):
        '''
        _makeBarlines(): when @left and @right are a simple barline, that barline is assigned
        '''
        elem = ETree.Element('measure', attrib={'left': 'dbl', 'right': 'dbl'})
        staves = {'1': stream.Measure(), '2': stream.Measure(), '3': stream.Measure(), '4': 4}

        staves = base._makeBarlines(elem, staves)

        for i in ('1', '2', '3'):
            self.assertIsInstance(staves[i].leftBarline, bar.Barline)
            self.assertEqual('double', staves[i].leftBarline.style)
            self.assertIsInstance(staves[i].rightBarline, bar.Barline)
            self.assertEqual('double', staves[i].rightBarline.style)
        self.assertEqual(4, staves['4'])

    def testMakeBarline3(self):
        '''
        _makeBarlines(): when @left and @right are "rptboth," that's done properly
        '''
        elem = ETree.Element('measure', attrib={'left': 'rptboth', 'right': 'rptboth'})
        staves = {'1': stream.Measure(), '2': stream.Measure(), '3': stream.Measure(), '4': 4}

        staves = base._makeBarlines(elem, staves)

        for i in ('1', '2', '3'):
            self.assertIsInstance(staves[i].leftBarline, bar.Repeat)
            self.assertEqual('heavy-light', staves[i].leftBarline.style)
            self.assertIsInstance(staves[i].rightBarline, bar.Repeat)
            self.assertEqual('final', staves[i].rightBarline.style)
        self.assertEqual(4, staves['4'])

    def testCorrectMRestDurs1(self):
        '''
        _correctMRestDurs(): nothing happens when there isn't at object with "m21wasMRest"

        This is an integration test of sorts, using no Mock objects.
        '''
        staves = {'1': stream.Measure([stream.Voice([note.Rest(), note.Rest()])]),
                  '2': stream.Measure([stream.Voice([note.Rest(), note.Rest()])])}
        base._correctMRestDurs(staves, 2.0)
        self.assertEqual(1.0, staves['1'].voices[0][0].quarterLength)
        self.assertEqual(1.0, staves['1'].voices[0][1].quarterLength)
        self.assertEqual(1.0, staves['2'].voices[0][0].quarterLength)
        self.assertEqual(1.0, staves['2'].voices[0][1].quarterLength)

    def testCorrectMRestDurs2(self):
        '''
        _correctMRestDurs(): things with "m21wasMRest" are adjusted properly

        This is an integration test of sorts, using no Mock objects.
        '''
        staves = {'1': stream.Measure([stream.Voice([note.Rest()])]),
                  '2': stream.Measure([stream.Voice([note.Rest(), note.Rest()])])}
        staves['1'][0][0].m21wasMRest = True
        base._correctMRestDurs(staves, 2.0)
        self.assertEqual(2.0, staves['1'].voices[0][0].quarterLength)
        self.assertEqual(1.0, staves['2'].voices[0][0].quarterLength)
        self.assertEqual(1.0, staves['2'].voices[0][1].quarterLength)
        self.assertFalse(hasattr(staves['1'].voices[0][0], 'm21wasMRest'))

    def testCorrectMRestDurs3(self):
        '''
        _correctMRestDurs(): works with more than 1 voice per part, and for things that aren't Voice

        This is an integration test of sorts, using no Mock objects.
        '''
        staves = {'1': stream.Measure([stream.Voice([note.Rest()]), stream.Voice([note.Rest()])]),
                  '2': stream.Measure([meter.TimeSignature('4/4'), stream.Voice([note.Note()])])}
        staves['1'][0][0].m21wasMRest = True
        staves['1'][1][0].m21wasMRest = True
        base._correctMRestDurs(staves, 2.0)
        self.assertEqual(2.0, staves['1'].voices[0][0].quarterLength)
        self.assertEqual(2.0, staves['1'].voices[1][0].quarterLength)
        self.assertEqual(1.0, staves['2'].voices[0][0].quarterLength)
        self.assertFalse(hasattr(staves['1'][0][0], 'm21wasMRest'))
        self.assertFalse(hasattr(staves['1'][1][0], 'm21wasMRest'))

    @mock.patch('music21.mei.base.staffFromElement')
    @mock.patch('music21.mei.base._correctMRestDurs')
    @mock.patch('music21.mei.base._makeBarlines')
    @mock.patch('music21.stream.Measure')
    @mock.patch('music21.stream.Voice')
    def testMeasureUnit1(self, mockVoice, mockMeasure, mockMakeBarlines, mockCorrectDurs, mockStaffFE):
        '''
        measureFromElement(): test 1
            - "elem" has an @n attribute
            - some staves have <mRest> without @dur (same behaviour to as if no staves did)
            - a rest-filled measure is created for the "n" value in "expectedNs" that's missing a
              corresponding <staff> element, and its Measure has the same @n as "elem"
            - activeMeter isn't None, and it is larger than the (internal) maxBarDuration

        mocked: staffFromElement(), stream.Measure() and Voice, _correctMRestDurs(), _makeBarlines()
        '''
        staffTag = '{}staff'.format(_MEINS)
        elem = ETree.Element('measure', attrib={'n': '42'})
        innerStaffs = [ETree.Element(staffTag, attrib={'n': str(n + 1)}) for n in range(3)]
        for eachStaff in innerStaffs:
            elem.append(eachStaff)
        # @n="4" is in "expectedNs" but we're leaving it out as part of the test
        backupNum = 900  # should be ignored by measureFromElement()
        expectedNs = ['1', '2', '3', '4']
        slurBundle = mock.MagicMock(name='slurBundle')
        activeMeter = mock.MagicMock(name='activeMeter')
        activeMeter.totalLength = 4.0  # this must match Measure.duration.quarterLength
        # prepare the mock Measure objects returned by mockMeasure
        mockMeasRets = [mock.MagicMock(name='Measure {}'.format(i + 1)) for i in range(4)]
        expected = mockMeasRets  # finish preparing "expected" below...
        for meas in mockMeasRets:
            meas.duration = mock.MagicMock(spec_set=duration.Duration)
            meas.duration.quarterLength = 4.0  # must match activeMeter.totalLength
        mockMeasure.side_effect = lambda *x, **y: mockMeasRets.pop(0)
        # prepare mock of _makeBarlines() which returns "staves"
        mockMakeBarlines.side_effect = lambda elem, staves: staves
        # prepare mock of _correctMRestDurs()
        mockCorrectDurs.return_value = None
        # prepare mock of staffFromElement(), which just needs to return several unique things
        staffFEreturns = [i for i in range(len(innerStaffs))]
        mockStaffFE.side_effect = lambda *x, **y: staffFEreturns.pop(0)
        # prepare mock of stream.Voice
        mockVoice.return_value = mock.MagicMock(name='Voice')
        # ... finish preparing "expected"
        expected = {n: expected[i] for i, n in enumerate(expectedNs)}

        actual = base.measureFromElement(elem, backupNum, expectedNs, slurBundle, activeMeter)

        self.assertDictEqual(expected, actual)
        # ensure staffFromElement() was called properly
        self.assertEqual(len(innerStaffs), mockStaffFE.call_count)
        for eachStaff in innerStaffs:
            mockStaffFE.assert_any_call(eachStaff, slurBundle=slurBundle)
        # ensure Measure.__init__() was called properly
        self.assertEqual(len(expected), mockMeasure.call_count)
        for i in range(len(innerStaffs)):
            mockMeasure.assert_any_call(i, number=int(elem.get('n')))
        mockMeasure.assert_any_call([mockVoice.return_value], number=int(elem.get('n')))
        # ensure the mocked Voice was set to "id" of 1
        self.assertEqual('1', mockVoice.return_value.id)
        # ensure the mocked _correctMRestDurs() was called properly
        mockCorrectDurs.assert_called_once_with(expected, 4.0)
        # ensure the mocked _makeBarlines() was called prooperly
        mockMakeBarlines.assert_called_once_with(elem, expected)

    def testMeasureIntegration1(self):
        '''
        measureFromElement(): test 1
            - "elem" has an @n attribute
            - some staves have <mRest> without @dur (same behaviour to as if no staves did)
            - a rest-filled measure is created for the "n" value in "expectedNs" that's missing a
              corresponding <staff> element, and its Measure has the same @n as "elem"
            - activeMeter isn't None, and it is larger than the (internal) maxBarDuration
            - the right barline is set properly ("dbl")

        no mocks
        '''
        staffTag = '{}staff'.format(_MEINS)
        layerTag = '{}layer'.format(_MEINS)
        noteTag = '{}note'.format(_MEINS)
        elem = ETree.Element('measure', attrib={'n': '42', 'right': 'dbl'})
        innerStaffs = [ETree.Element(staffTag, attrib={'n': str(n + 1)}) for n in range(3)]
        for i, eachStaff in enumerate(innerStaffs):
            thisLayer = ETree.Element(layerTag, attrib={'n': '1'})
            thisLayer.append(ETree.Element(noteTag,
                                           attrib={'pname': 'G', 'oct': str(i + 1), 'dur': '1'}))
            eachStaff.append(thisLayer)
            elem.append(eachStaff)
        # @n="4" is in "expectedNs" but we're leaving it out as part of the test
        backupNum = 900  # should be ignored by measureFromElement()
        expectedNs = ['1', '2', '3', '4']
        slurBundle = spanner.SpannerBundle()
        activeMeter = meter.TimeSignature('8/8')  # bet you thought this would be 4/4, eh?

        actual = base.measureFromElement(elem, backupNum, expectedNs, slurBundle, activeMeter)

        # ensure the right number and @n of parts
        self.assertEqual(4, len(actual.keys()))
        for eachN in expectedNs:
            self.assertTrue(eachN in actual.keys())
        # ensure the measure number is set properly,
        #        there is one voice with one note with its octave set equal to the staff's @n,
        #        the right barline was set properly
        for eachN in ['1', '2', '3']:
            self.assertEqual(42, actual[eachN].number)
            self.assertEqual(2, len(actual[eachN]))  # first the Note, then the Barline
            self.assertIsInstance(actual[eachN][0], stream.Voice)
            self.assertEqual(1, len(actual[eachN][0]))
            self.assertIsInstance(actual[eachN][0][0], note.Note)
            self.assertEqual(int(eachN), actual[eachN][0][0].pitch.octave)
            self.assertIsInstance(actual[eachN].rightBarline, bar.Barline)
            self.assertEqual('double', actual[eachN].rightBarline.style)
        # ensure voice '4' with Rest of proper duration, right measure number, and right barline
        self.assertEqual(42, actual['4'].number)
        self.assertEqual(2, len(actual['4']))  # first the Rest, then the Barline
        self.assertIsInstance(actual['4'][0], stream.Voice)
        self.assertEqual(1, len(actual['4'][0]))
        self.assertIsInstance(actual['4'][0][0], note.Rest)
        self.assertEqual(activeMeter.totalLength, actual['4'][0][0].duration.quarterLength)
        self.assertIsInstance(actual[eachN].rightBarline, bar.Barline)
        self.assertEqual('double', actual[eachN].rightBarline.style)

    @mock.patch('music21.mei.base.staffFromElement')
    @mock.patch('music21.mei.base._correctMRestDurs')
    @mock.patch('music21.mei.base._makeBarlines')
    @mock.patch('music21.stream.Measure')
    @mock.patch('music21.stream.Voice')
    def testMeasureUnit2(self, mockVoice, mockMeasure, mockMakeBarlines, mockCorrectDurs, mockStaffFE):
        '''
        measureFromElement(): test 2
            - "elem" doesn't have an @n attribute
            - all staves have <mRest> without @dur
            - a rest-filled measure is created for the "n" value in "expectedNs" that's missing a
              corresponding <staff> element, and it properly uses "backupNum"

        mocked: staffFromElement(), stream.Measure() and Voice, _correctMRestDurs(), _makeBarlines()
        '''
        staffTag = '{}staff'.format(_MEINS)
        elem = ETree.Element('measure')
        innerStaffs = [ETree.Element(staffTag, attrib={'n': str(n + 1)}) for n in range(3)]
        for eachStaff in innerStaffs:
            elem.append(eachStaff)
        # @n="4" is in "expectedNs" but we're leaving it out as part of the test
        backupNum = 900  # should be used by measureFromElement()
        expectedNs = ['1', '2', '3', '4']
        slurBundle = mock.MagicMock(name='slurBundle')
        activeMeter = mock.MagicMock(name='activeMeter')
        activeMeter.totalLength = 12.0  # this must be longer than Measure.duration.quarterLength
        # prepare the mock Measure objects returned by mockMeasure
        mockMeasRets = [mock.MagicMock(name='Measure {}'.format(i + 1)) for i in range(4)]
        expected = mockMeasRets  # finish preparing "expected" below...
        for meas in mockMeasRets:
            meas.duration = mock.MagicMock(spec_set=duration.Duration)
            meas.duration.quarterLength = base._DUR_ATTR_DICT[None]  # must be _DUR_ATTR_DICT[None]
        mockMeasure.side_effect = lambda *x, **y: mockMeasRets.pop(0)
        # prepare mock of _makeBarlines() which returns "staves"
        mockMakeBarlines.side_effect = lambda elem, staves: staves
        # prepare mock of _correctMRestDurs()
        mockCorrectDurs.return_value = None
        # prepare mock of staffFromElement(), which just needs to return several unique things
        staffFEreturns = [i for i in range(len(innerStaffs))]
        mockStaffFE.side_effect = lambda *x, **y: staffFEreturns.pop(0)
        # prepare mock of stream.Voice
        mockVoice.return_value = mock.MagicMock(name='Voice')
        # ... finish preparing "expected"
        expected = {n: expected[i] for i, n in enumerate(expectedNs)}

        actual = base.measureFromElement(elem, backupNum, expectedNs, slurBundle, activeMeter)

        self.assertDictEqual(expected, actual)
        # ensure staffFromElement() was called properly
        self.assertEqual(len(innerStaffs), mockStaffFE.call_count)
        for eachStaff in innerStaffs:
            mockStaffFE.assert_any_call(eachStaff, slurBundle=slurBundle)
        # ensure Measure.__init__() was called properly
        self.assertEqual(len(expected), mockMeasure.call_count)
        for i in range(len(innerStaffs)):
            mockMeasure.assert_any_call(i, number=backupNum)
        mockMeasure.assert_any_call([mockVoice.return_value], number=backupNum)
        # ensure the mocked Voice was set to "id" of 1
        self.assertEqual('1', mockVoice.return_value.id)
        # ensure the mocked _correctMRestDurs() was called properly
        mockCorrectDurs.assert_called_once_with(expected, 12.0)
        # ensure the mocked _makeBarlines() was called prooperly
        mockMakeBarlines.assert_called_once_with(elem, expected)

    def testMeasureIntegration2(self):
        '''
        measureFromElement(): test 2
            - "elem" doesn't have an @n attribute
            - all staves have <mRest> without @dur (and only 3 of the 4 are specified at all)
            - a rest-filled measure is created for the "n" value in "expectedNs" that's missing a
              corresponding <staff> element, and it properly uses "backupNum"
            - the right barline is set properly ("rptboth")

        no mocks
        '''
        staffTag = '{}staff'.format(_MEINS)
        layerTag = '{}layer'.format(_MEINS)
        mRestTag = '{}mRest'.format(_MEINS)
        elem = ETree.Element('measure', attrib={'right': 'rptboth'})
        innerStaffs = [ETree.Element(staffTag, attrib={'n': str(n + 1)}) for n in range(3)]
        for i, eachStaff in enumerate(innerStaffs):
            thisLayer = ETree.Element(layerTag, attrib={'n': '1'})
            thisLayer.append(ETree.Element(mRestTag))
            eachStaff.append(thisLayer)
            elem.append(eachStaff)
        # @n="4" is in "expectedNs" but we're leaving it out as part of the test
        backupNum = 900  # should be used by measureFromElement()
        expectedNs = ['1', '2', '3', '4']
        slurBundle = spanner.SpannerBundle()
        activeMeter = meter.TimeSignature('8/8')  # bet you thought this would be 4/4, eh?

        actual = base.measureFromElement(elem, backupNum, expectedNs, slurBundle, activeMeter)

        # ensure the right number and @n of parts (we expect one additional key, for the "rptboth")
        self.assertEqual(5, len(actual.keys()))
        for eachN in expectedNs:
            self.assertTrue(eachN in actual.keys())
        self.assertTrue('next @left' in actual.keys())
        # ensure the measure number is set properly,
        #        there is one voice with one note with its octave set equal to the staff's @n,
        #        the right barline was set properly
        # (Note we can test all four parts together this time---the fourth should be indistinguishable)
        for eachN in expectedNs:
            self.assertEqual(backupNum, actual[eachN].number)
            self.assertEqual(2, len(actual[eachN]))  # first the Note, then the Barline
            self.assertIsInstance(actual[eachN][0], stream.Voice)
            self.assertEqual(1, len(actual[eachN][0]))
            self.assertIsInstance(actual[eachN][0][0], note.Rest)
            self.assertEqual(activeMeter.totalLength, actual['4'][0][0].duration.quarterLength)
            self.assertIsInstance(actual[eachN].rightBarline, bar.Repeat)
            self.assertEqual('final', actual[eachN].rightBarline.style)

    @mock.patch('music21.mei.base.staffFromElement')
    @mock.patch('music21.mei.base._correctMRestDurs')
    @mock.patch('music21.mei.base._makeBarlines')
    @mock.patch('music21.stream.Measure')
    @mock.patch('music21.mei.base.staffDefFromElement')
    def testMeasureUnit3a(self, mockStaffDefFE, mockMeasure, mockMakeBarlines, mockCorrectDurs, mockStaffFE):
        '''
        measureFromElement(): test 3a
            - there is one part
            - there is a <staffDef> which has its required @n attribute

        mocked: staffFromElement(), staffDefFromElement, stream.Measure(), _correctMRestDurs(), _makeBarlines(),
        '''
        staffTag = '{}staff'.format(_MEINS)
        staffDefTag = '{}staffDef'.format(_MEINS)
        elem = ETree.Element('measure', attrib={'n': '42'})
        staffDefElem = ETree.Element(staffDefTag, attrib={'n': '1', 'lines': '5'})
        elem.append(staffDefElem)
        staffElem = ETree.Element(staffTag, attrib={'n': '1'})
        elem.append(staffElem)
        backupNum = 900  # should be ignored by measureFromElement()
        expectedNs = ['1']
        slurBundle = mock.MagicMock(name='slurBundle')
        activeMeter = mock.MagicMock(name='activeMeter')
        activeMeter.totalLength = 4.0  # this must match Measure.duration.quarterLength
        # prepare the mock Measure object returned by mockMeasure
        mockMeasure.return_value = mock.MagicMock(name='Measure 1')
        # prepare mock of _makeBarlines() which returns "staves"
        mockMakeBarlines.side_effect = lambda elem, staves: staves
        # prepare mock of _correctMRestDurs()
        mockCorrectDurs.return_value = None
        # prepare mock of staffFromElement(), which just needs to return several unique things
        mockStaffFE.return_value = 'staffFromElement() return value'
        # prepare mock of staffDefFromElement()
        mockStaffDefFE.return_value = {'clef': mock.MagicMock(name='SomeClef')}
        # prepare the expected return value
        expected = {'1': mockMeasure.return_value}

        actual = base.measureFromElement(elem, backupNum, expectedNs, slurBundle, activeMeter)

        self.assertDictEqual(expected, actual)
        # ensure staffFromElement() was called properly
        mockStaffFE.assert_called_once_with(staffElem, slurBundle=slurBundle)
        # ensure staffDefFromElement() was called properly
        mockStaffDefFE.assert_called_once_with(staffDefElem, slurBundle)
        # ensure Measure.__init__() was called properly
        mockMeasure.assert_called_once_with(mockStaffFE.return_value, number=42)
        mockMeasure.return_value.insert.assert_called_once_with(0, mockStaffDefFE.return_value['clef'])

    @mock.patch('music21.mei.base.staffFromElement')
    @mock.patch('music21.mei.base._correctMRestDurs')
    @mock.patch('music21.mei.base._makeBarlines')
    @mock.patch('music21.stream.Measure')
    @mock.patch('music21.mei.base.environLocal')
    def testMeasureUnit3b(self, mockEnviron, mockMeasure, mockMakeBarlines, mockCorrectDurs, mockStaffFE):
        '''
        measureFromElement(): test 3b
            - there is one part
            - there is a <staffDef> which does not have its required @n attribute

        mocked: staffFromElement(), environLocal, stream.Measure(), _correctMRestDurs(), _makeBarlines(),
        '''
        staffTag = '{}staff'.format(_MEINS)
        staffDefTag = '{}staffDef'.format(_MEINS)
        elem = ETree.Element('measure', attrib={'n': '42'})
        staffDefElem = ETree.Element(staffDefTag, attrib={'lines': '5'})
        elem.append(staffDefElem)
        staffElem = ETree.Element(staffTag, attrib={'n': '1'})
        elem.append(staffElem)
        backupNum = 900  # should be ignored by measureFromElement()
        expectedNs = ['1']
        slurBundle = mock.MagicMock(name='slurBundle')
        activeMeter = mock.MagicMock(name='activeMeter')
        activeMeter.totalLength = 4.0  # this must match Measure.duration.quarterLength
        # prepare the mock Measure object returned by mockMeasure
        mockMeasure.return_value = mock.MagicMock(name='Measure 1')
        # prepare mock of _makeBarlines() which returns "staves"
        mockMakeBarlines.side_effect = lambda elem, staves: staves
        # prepare mock of _correctMRestDurs()
        mockCorrectDurs.return_value = None
        # prepare mock of staffFromElement(), which just needs to return several unique things
        mockStaffFE.return_value = 'staffFromElement() return value'
        # prepare the expected return value
        expected = {'1': mockMeasure.return_value}

        actual = base.measureFromElement(elem, backupNum, expectedNs, slurBundle, activeMeter)

        self.assertDictEqual(expected, actual)
        # ensure staffFromElement() was called properly
        mockStaffFE.assert_called_once_with(staffElem, slurBundle=slurBundle)
        # ensure Measure.__init__() was called properly
        mockMeasure.assert_called_once_with(mockStaffFE.return_value, number=42)
        self.assertEqual(0, mockMeasure.return_value.insert.call_count)
        # ensure environLocal.warn() was called properly
        mockEnviron.warn.assert_called_once_with(base._UNIMPLEMENTED_IMPORT.format('<staffDef>', '@n'))

    def testMeasureIntegration3(self):
        '''
        measureFromElement(): test 3
            - there is one part
            - there is a <staffDef> which has its required @n attribute

        NB: I won't bother making an integration equivalent to unit test 3b, since I would have to
            mock "environLocal" to know whether it worked, and "no mocks" is the whole point of this

        no mocks
        '''
        staffTag = '{}staff'.format(_MEINS)
        layerTag = '{}layer'.format(_MEINS)
        noteTag = '{}note'.format(_MEINS)
        staffDefTag = '{}staffDef'.format(_MEINS)
        elem = ETree.Element('measure')
        elem.append(ETree.Element(staffDefTag, attrib={'n': '1', 'lines': '5', 'clef.line': '4', 'clef.shape': 'F'}))
        innerStaff = ETree.Element(staffTag, attrib={'n': '1'})
        innerLayer = ETree.Element(layerTag, attrib={'n': '1'})
        innerLayer.append(ETree.Element(noteTag))
        innerStaff.append(innerLayer)
        elem.append(innerStaff)
        backupNum = 900  # should be used by measureFromElement()
        expectedNs = ['1']
        slurBundle = spanner.SpannerBundle()
        activeMeter = meter.TimeSignature('8/8')  # bet you thought this would be 4/4, eh?

        actual = base.measureFromElement(elem, backupNum, expectedNs, slurBundle, activeMeter)

        # ensure the right number and @n of parts
        self.assertEqual(['1'], list(actual.keys()))
        # ensure the Measure has its expected Voice, BassClef, and Instrument
        self.assertEqual(backupNum, actual['1'].number)
        self.assertEqual(2, len(actual['1']))  # the Voice, plus a Clef and Instrument from staffDefFE()
        foundVoice = False
        foundClef = False
        for item in actual['1']:
            if isinstance(item, stream.Voice):
                foundVoice = True
            elif isinstance(item, clef.BassClef):
                foundClef = True
        self.assertTrue(foundVoice is True)
        self.assertTrue(foundClef is True)


#------------------------------------------------------------------------------
class TestSectionScore(unittest.TestCase):
    '''Tests for scoreFromElement(), sectionFromElement(), and their helper function sectionScoreCore().'''

    @mock.patch('music21.mei.base.sectionScoreCore')
    def testSection1(self, mockCore):
        '''
        Mock sectionScoreCore(). This is very straight-forward.
        '''
        mockCore.return_value = 5
        elem = ETree.Element('section')
        allPartNs = ['1', '2', '3']
        activeMeter = meter.TimeSignature('12/8')
        nextMeasureLeft = bar.Repeat()
        backupMeasureNum = 42
        slurBundle = spanner.SpannerBundle()
        expected = mockCore.return_value

        actual = base.sectionFromElement(elem, allPartNs, activeMeter, nextMeasureLeft, backupMeasureNum, slurBundle)

        self.assertEqual(expected, actual)
        mockCore.assert_called_once_with(elem,
                                         allPartNs,
                                         slurBundle,
                                         activeMeter=activeMeter,
                                         nextMeasureLeft=nextMeasureLeft,
                                         backupMeasureNum=backupMeasureNum)

    @mock.patch('music21.mei.base.allPartsPresent')
    @mock.patch('music21.mei.base.sectionScoreCore')
    @mock.patch('music21.stream.Part')
    @mock.patch('music21.stream.Score')
    def testScoreUnit1(self, mockScore, mockPart, mockCore, mockAllParts):
        '''
        scoreFromElement(): unit test with all basic functionality

        It's two parts, each with two things in them.

        Mocks on allPartsPresent(), sectionScoreCore(), stream.Part(), and stream.Score().
        '''
        elem = ETree.Element('score')
        mockAllParts.return_value = ['1', '2']
        mockCore.return_value = ({'1': ['1-1', '1-2'], '2': ['2-1', '2-2']},
                                 'three', 'other', 'things')
        mockScore.side_effect = lambda x: [x[0], x[1]]  # can't just return "x" in this case because it confuses the mocks
        mockPart1 = mock.MagicMock()
        mockPart1.append = mock.MagicMock()
        mockPart2 = mock.MagicMock()
        mockPart2.append = mock.MagicMock()
        mockPartReturns = [mockPart1, mockPart2]
        mockPart.side_effect = lambda: mockPartReturns.pop(0)
        slurBundle = mock.MagicMock(spec_set=spanner.SpannerBundle)
        slurBundle.list = 'slurBundle list'
        expected = [mockPart1, mockPart2, slurBundle.list]

        actual = base.scoreFromElement(elem, slurBundle)

        self.assertEqual(expected, actual)
        mockAllParts.assert_called_once_with(elem)
        mockCore.assert_called_once_with(elem, mockAllParts.return_value, slurBundle=slurBundle)
        mockScore.assert_called_once_with([mockPart1, mockPart2])
        self.assertEqual(2, mockPart1.append.call_count)
        self.assertEqual(2, mockPart2.append.call_count)
        mockPart1.append.assert_any_call('1-1')
        mockPart1.append.assert_any_call('1-2')
        mockPart2.append.assert_any_call('2-1')
        mockPart2.append.assert_any_call('2-2')

    def testScoreIntegration1(self):
        '''
        scoreFromElement(): integration test with all basic functionality

        It's two parts, each with two things in them.
        '''
        elem = """<score xmlns="http://www.music-encoding.org/ns/mei">
            <scoreDef meter.count="8" meter.unit="8">
                <staffGrp>
                    <staffDef n="1" clef.shape="G" clef.line="2"/>
                    <staffDef n="2" clef.shape="F" clef.line="4"/>
                </staffGrp>
            </scoreDef>
            <section>
                <measure>
                    <staff n="1">
                        <layer n="1">
                            <note pname="G" oct="4" dur="2" slur="1i"/>
                            <note pname="A" oct="4" dur="2" slur="1t"/>
                        </layer>
                    </staff>
                    <staff n="2">
                        <layer n="1">
                            <note pname="G" oct="2" dur="1"/>
                        </layer>
                    </staff>
                </measure>
            </section>
        </score>"""
        elem = ETree.fromstring(elem)
        slurBundle = spanner.SpannerBundle()

        actual = base.scoreFromElement(elem, slurBundle)

        # This is complicated... I'm sorry... but it's a rather detailed test of the whole system,
        # so I hope it's worth it!
        self.assertEqual(2, len(actual.parts))
        self.assertEqual(3, len(actual))  # parts plus "slurBundle"
        self.assertEqual(1, len(actual.parts[0]))  # one Measure in each part
        self.assertEqual(1, len(actual.parts[1]))
        self.assertIsInstance(actual.parts[0][0], stream.Measure)
        self.assertIsInstance(actual.parts[1][0], stream.Measure)
        self.assertEqual(3, len(actual.parts[0][0]))  # each Measure has a Voice, a Clef, a TimeSignature
        self.assertEqual(3, len(actual.parts[1][0]))
        # Inspect the Voice and the Note objects inside it
        self.assertIsInstance(actual.parts[0][0][0], stream.Voice)
        self.assertIsInstance(actual.parts[1][0][0], stream.Voice)
        self.assertEqual(2, len(actual.parts[0][0][0]))  # two Note in upper part
        self.assertEqual(1, len(actual.parts[1][0][0]))  # one Note in lower part
        self.assertIsInstance(actual.parts[0][0][0][0], note.Note)  # upper part, note 1
        self.assertEqual('G4', actual.parts[0][0][0][0].nameWithOctave)
        self.assertEqual(2.0, actual.parts[0][0][0][0].quarterLength)
        self.assertIsInstance(actual.parts[0][0][0][1], note.Note)  # upper part, note 2
        self.assertEqual('A4', actual.parts[0][0][0][1].nameWithOctave)
        self.assertEqual(2.0, actual.parts[0][0][0][1].quarterLength)
        self.assertIsInstance(actual.parts[1][0][0][0], note.Note)  # lower part
        self.assertEqual('G2', actual.parts[1][0][0][0].nameWithOctave)
        self.assertEqual(4.0, actual.parts[1][0][0][0].quarterLength)
        # Inspect the Clef and TimeSignature objects that follow the Voice
        self.assertIsInstance(actual.parts[0][0][1], clef.TrebleClef)  # upper
        self.assertIsInstance(actual.parts[0][0][2], meter.TimeSignature)
        self.assertEqual('8/8', actual.parts[0][0][2].ratioString)
        self.assertIsInstance(actual.parts[1][0][1], clef.BassClef)  # lower
        self.assertIsInstance(actual.parts[1][0][2], meter.TimeSignature)
        self.assertEqual('8/8', actual.parts[1][0][2].ratioString)

    @mock.patch('music21.mei.base.measureFromElement')
    @mock.patch('music21.mei.base.sectionFromElement')
    @mock.patch('music21.mei.base.scoreDefFromElement')
    @mock.patch('music21.mei.base.staffDefFromElement')
    def testCoreUnit1(self, mockStaffDFE, mockScoreDFE, mockSectionFE, mockMeasureFE):
        '''
        sectionScoreCore(): everything basic, as called by scoreFromElement()
            - no kwargs
                - and the <measure> has no @n; it would be set to "1" automatically
            - one of everything (<section>, <scoreDef>, and <staffDef>)
            - that the <measure> in here won't be processed (<measure> must be in a <section>)
            - things in a <section> are appended properly (different for <score> and <section>)

        mocked:
            - measureFromElement()
            - sectionFromElement()
            - scoreDefFromElement()
            - staffDefFromElement()
        '''
        # setup the arguments
        # NB: there's more MEI here than we need, but it's shared between unit & integration tests
        elem = """<score xmlns="http://www.music-encoding.org/ns/mei">
            <scoreDef meter.count="8" meter.unit="8"/>
            <staffDef n="1" clef.shape="G" clef.line="2"/>
            <measure/>
            <section>
                <measure>
                    <staff n="1">
                        <layer n="1">
                            <note pname="G" oct="4" dur="1"/>
                        </layer>
                    </staff>
                </measure>
            </section>
        </score>"""
        elem = ETree.fromstring(elem)
        slurBundle = mock.MagicMock()
        allPartNs = ['1']
        # setup sectionFromElement()
        expActiveMeter = mock.MagicMock(spec_set=meter.TimeSignature)
        expMeasureNum = 1
        expNMLeft = 'barline for the next Meausre'
        expPart1 = [mock.MagicMock(spec_set=stream.Stream)]
        mockSectionFE.return_value = ({'1': expPart1},
                                      expActiveMeter, expNMLeft, expMeasureNum)
        # setup scoreDefFromElement()
        scoreDefActiveMeter = mock.MagicMock(spec_set=meter.TimeSignature)
        mockScoreDFE.return_value = {'all-part objects': [scoreDefActiveMeter],
                                     '1': {'whatever': '8/8'}}
        # setup staffDefFromElement()
        mockStaffDFE.return_value = {'whatever': 'treble clef'}
        # prepare the "expected" return
        expected = {'1': [expPart1]}
        expected = (expected, expActiveMeter, expNMLeft, expMeasureNum)

        actual = base.sectionScoreCore(elem, allPartNs, slurBundle)

        # ensure expected == actual
        self.assertEqual(expected, actual)
        # ensure measureFromElement() wasn't called
        self.assertEqual(0, mockMeasureFE.call_count)
        # ensure sectionFromElement()
        mockSectionFE.assert_called_once_with(mock.ANY,
                                              allPartNs,
                                              activeMeter=scoreDefActiveMeter,
                                              nextMeasureLeft=None,
                                              backupMeasureNum=0,
                                              slurBundle=slurBundle)
        self.assertEqual('{}section'.format(_MEINS), mockSectionFE.call_args_list[0][0][0].tag)
        # ensure scoreDefFromElement()
        mockScoreDFE.assert_called_once_with(mock.ANY, slurBundle)
        self.assertEqual('{}scoreDef'.format(_MEINS), mockScoreDFE.call_args_list[0][0][0].tag)
        # ensure staffDefFromElement()
        mockStaffDFE.assert_called_once_with(mock.ANY, slurBundle)
        self.assertEqual('{}staffDef'.format(_MEINS), mockStaffDFE.call_args_list[0][0][0].tag)
        # ensure the "inNextThing" numbers and mock.TimeSignature were put into the mocked Part
        self.assertEqual(3, expPart1[0].insert.call_count)
        expPart1[0].insert.assert_any_call(0.0, scoreDefActiveMeter)
        expPart1[0].insert.assert_any_call(0.0, '8/8')
        expPart1[0].insert.assert_any_call(0.0, 'treble clef')

    def testCoreIntegration1(self):
        '''
        sectionScoreCore(): everything basic, as called by scoreFromElement()
            - no kwargs
                - and the <measure> has no @n; it would be set to "1" automatically
            - one of everything (<section>, <scoreDef>, and <staffDef>)
            - that the <measure> in here won't be processed (<measure> must be in a <section>)
            - things in a <section> are appended properly (different for <score> and <section>)
        '''
        # setup the arguments
        elem = """<score xmlns="http://www.music-encoding.org/ns/mei">
            <scoreDef meter.count="8" meter.unit="8"/>
            <staffDef n="1" clef.shape="G" clef.line="2"/>
            <measure/>
            <section>
                <measure>
                    <staff n="1">
                        <layer n="1">
                            <note pname="G" oct="4" dur="1"/>
                        </layer>
                    </staff>
                </measure>
            </section>
        </score>"""
        elem = ETree.fromstring(elem)
        slurBundle = spanner.SpannerBundle()
        allPartNs = ['1']

        parsed, activeMeter, nextMeasureLeft, backupMeasureNum = base.sectionScoreCore(elem, allPartNs, slurBundle)

        # ensure simple returns are okay
        self.assertEqual('8/8', activeMeter.ratioString)
        self.assertIsNone(nextMeasureLeft)
        self.assertEqual(1, backupMeasureNum)
        # ensure "parsed" is the right format
        self.assertEqual(1, len(parsed))
        self.assertTrue('1' in parsed)
        self.assertEqual(1, len(parsed['1']))  # there is one <section>
        self.assertEqual(1, len(parsed['1'][0]))  # there is one Measure
        meas = parsed['1'][0][0]
        self.assertIsInstance(meas, stream.Measure)
        self.assertEqual(1, meas.number)
        self.assertEqual(3, len(meas))  # a Voice, a Clef, a TimeSignature
        self.assertIsInstance(meas[0], stream.Voice)  # check out the Voice and its Note
        self.assertEqual(1, len(meas[0]))
        self.assertIsInstance(meas[0][0], note.Note)
        self.assertEqual('G4', meas[0][0].nameWithOctave)
        self.assertIsInstance(meas[1], clef.TrebleClef)  # check out the Clef
        self.assertIsInstance(meas[2], meter.TimeSignature)  # check out the TimeSignature
        self.assertEqual('8/8', meas[2].ratioString)