import unittest
import sys
import os

sys.path.append(os.path.abspath("./../"))
from GcodeWoodgrainer import *

class TestGcodeWoodgrainer(unittest.TestCase):

    def test_isWoodgrainedAlreadyLineReportsTrueForWoodgrainedLine(self):
        line = ";HAS_BEEN_WOODGRAINED"
        self.assertTrue(isWoodgrainedAlreadyLine(line))
        line = "some other text ;HAS_BEEN_WOODGRAINED"
        self.assertTrue(isWoodgrainedAlreadyLine(line))
        line = ";HAS_BEEN_WOODGRAINED some other text"
        self.assertTrue(isWoodgrainedAlreadyLine(line))

    def test_isWoodgrainedAlreadyLineReportsFalseForNonWoodgrainedLine(self):
        line = "foo"
        self.assertFalse(isWoodgrainedAlreadyLine(line))
        line = "bar"
        self.assertFalse(isWoodgrainedAlreadyLine(line))
        line = ""
        self.assertFalse(isWoodgrainedAlreadyLine(line))

    def test_linesHaveBeenWoodGrainedReportsTrueForWoodgrainedFile(self):
        lines = ["foo", "bar", ";HAS_BEEN_WOODGRAINED", "spam", "eggs"]
        self.assertTrue(linesHaveBeenWoodGrained(lines))
        lines = ["foo", "bar", ";HAS_BEEN_WOODGRAINED", "spam", "eggs", ";HAS_BEEN_WOODGRAINED", ";HAS_BEEN_WOODGRAINED"]
        self.assertTrue(linesHaveBeenWoodGrained(lines))

    def test_linesHaveBeenWoodGrainedReportsFalseForNonWoodgrainedFile(self):
        lines = ["foo", "bar", "spam", "eggs"]
        self.assertFalse(linesHaveBeenWoodGrained(lines))

    def test_isLayerChangeLine(self):
        self.assertTrue(isLayerChangeLine(";LAYER:1"))
        self.assertTrue(isLayerChangeLine(";BEFORE_LAYER_CHANGE"))
        self.assertTrue(isLayerChangeLine(";WOODGRAIN_INSERT_LAYER"))
        self.assertFalse(isLayerChangeLine(";LAYER"))
        self.assertFalse(isLayerChangeLine("G1 X117.46 Y99.042 E.09266"))
        self.assertFalse(isLayerChangeLine("G1 Z2.1 F720"))
        self.assertFalse(isLayerChangeLine(";AFTER_LAYER_CHANGE"))

    def test_getTempStaysInRange(self):
        # Test each 100 times just to be sure
        for i in range(100):
            self.assertGreaterEqual(getTemp(200,250,1), 200)
            self.assertGreaterEqual(getTemp(200,250,5), 200)
            self.assertGreaterEqual(getTemp(200,250,50), 200)
            self.assertGreaterEqual(getTemp(200,250,100), 200)
            self.assertLessEqual(getTemp(200,250,1), 250)
            self.assertLessEqual(getTemp(200,250,5), 250)
            self.assertLessEqual(getTemp(200,250,50), 250)
            self.assertLessEqual(getTemp(200,250,100), 250)

    def test_processLinesInsertsTemperatureChangeCommand(self):
        lines = ["foo", "bar", ";LAYER:1", "G1 X100", "G1 X110", ";LAYER:2", "G1 X120"]
        result = processLines(lines, 200, 250, 5, 1)
        # Should be 1 temperature change line, and 1 woograined identifier line
        self.assertGreater(len(result['lines']), len(lines))
        self.assertEqual(result['numlayers'], 2)
        self.assertEqual(result['numtempchanges'], 1)
        self.assertRegex(result['lines'][7], r'M104')

    def test_processLinesRaisesOnAlreadyWoodgrained(self):
        lines = ["foo", ";HAS_BEEN_WOODGRAINED", "bar", ";LAYER:1", "G1 X100", "G1 X110", ";LAYER:2", "G1 X120"]
        with self.assertRaises(GcodeAlreadyWoodifiedError):
            processLines(lines, 200, 250, 5, 1)

    def test_makeTempChangeLine(self):
        self.assertRegex(makeTempChangeLine(200), r"M104 *S200")
        self.assertRegex(makeTempChangeLine(50), r"M104 *S50")


if __name__ == '__main__':
    unittest.main()