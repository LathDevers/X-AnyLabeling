import unittest

from anylabeling.views.labeling.utils.geometry import (
    shape_geometry,
    subtract_geometry,
)

SQUARE = [(0, 0), (100, 0), (100, 100), (0, 100)]


def area(ring):
    return 0.5 * abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1])
        )
    )


class TestSubtractGeometry(unittest.TestCase):

    def test_band_splits_target_in_two(self):
        target = shape_geometry("polygon", SQUARE)
        cutter = shape_geometry(
            "rectangle", [(40, -10), (60, -10), (60, 110), (40, 110)]
        )

        pieces = subtract_geometry(target, cutter)

        self.assertEqual(len(pieces), 2)
        for outer, holes in pieces:
            self.assertAlmostEqual(area(outer), 4000)
            self.assertEqual(holes, [])

    def test_cutter_inside_target_leaves_a_hole(self):
        target = shape_geometry("polygon", SQUARE)
        cutter = shape_geometry(
            "polygon", [(30, 30), (70, 30), (70, 70), (30, 70)]
        )

        (outer, holes), = subtract_geometry(target, cutter)

        self.assertAlmostEqual(area(outer), 10000)
        self.assertEqual(len(holes), 1)
        self.assertAlmostEqual(area(holes[0]), 1600)

    def test_part_inside_cutter_hole_survives(self):
        target = shape_geometry(
            "polygon", [(40, 40), (60, 40), (60, 60), (40, 60)]
        )
        cutter = shape_geometry(
            "polygon", SQUARE, [[(45, 45), (55, 45), (55, 55), (45, 55)]]
        )

        (outer, holes), = subtract_geometry(target, cutter)

        self.assertAlmostEqual(area(outer), 100)
        self.assertEqual(holes, [])

    def test_target_inside_cutter_vanishes(self):
        target = shape_geometry(
            "polygon", [(40, 40), (60, 40), (60, 60), (40, 60)]
        )
        cutter = shape_geometry("polygon", SQUARE)

        self.assertEqual(subtract_geometry(target, cutter), [])

    def test_circle_cutter_and_invalid_input(self):
        circle = shape_geometry("circle", [(50, 50), (60, 50)])
        self.assertAlmostEqual(circle.area, 314.0, delta=2)
        self.assertIsNone(shape_geometry("circle", [(5, 5), (5, 5)]))
        self.assertIsNone(shape_geometry("line", [(0, 0), (1, 1)]))
        bowtie = shape_geometry(
            "polygon", [(0, 0), (10, 10), (10, 0), (0, 10)]
        )
        self.assertTrue(bowtie.is_valid)

    def test_slivers_are_dropped(self):
        target = shape_geometry("polygon", SQUARE)
        cutter = shape_geometry(
            "polygon", [(0.5, -1), (101, -1), (101, 101), (0.5, 101)]
        )

        self.assertEqual(subtract_geometry(target, cutter, min_area=60), [])


if __name__ == "__main__":
    unittest.main()
