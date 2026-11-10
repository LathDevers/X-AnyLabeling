import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import numpy as np
    from PyQt6 import QtCore, QtGui, QtWidgets

    from anylabeling.views.labeling.shape import Shape
    from anylabeling.views.labeling.widgets.canvas import Canvas

    PYQT_AVAILABLE = True
except Exception:
    PYQT_AVAILABLE = False


class FakeMouseEvent:
    def __init__(self, ctrl=False):
        self._ctrl = ctrl

    def button(self):
        return QtCore.Qt.MouseButton.LeftButton

    def buttons(self):
        return QtCore.Qt.MouseButton.LeftButton

    def modifiers(self):
        if self._ctrl:
            return QtCore.Qt.KeyboardModifier.ControlModifier
        return QtCore.Qt.KeyboardModifier.NoModifier


def points(xys):
    return [QtCore.QPointF(x, y) for x, y in xys]


@unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 is required for mask hole tests")
class TestMaskHoles(unittest.TestCase):

    def setUp(self):
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])
        self.canvas = Canvas(parent=None)
        self.canvas.pixmap = QtGui.QPixmap(100, 100)
        self.canvas.pixmap.fill(QtGui.QColor("black"))
        self.canvas.brush_simplify_epsilon_px = 0.0
        self.shape = Shape(label="object", shape_type="polygon")
        self.shape.points = points([(10, 10), (80, 10), (80, 80), (10, 80)])
        self.shape.close()
        self.shape.selected = True
        self.canvas.shapes = [self.shape]
        self.canvas.selected_shapes = [self.shape]
        self.canvas.store_shapes()

    def tearDown(self):
        self.canvas.close()
        self.app.processEvents()

    def cut_rectangle(self, p1, p2):
        self.canvas._brush_mouse_press(
            FakeMouseEvent(ctrl=True), QtCore.QPointF(*p1)
        )
        self.canvas._region_mouse_release(
            FakeMouseEvent(ctrl=True), QtCore.QPointF(*p2)
        )

    def test_cut_is_filled_without_keep_holes(self):
        self.canvas.set_brush_mode(True, "rectangle")
        self.assertFalse(self.canvas.brush_keep_holes)
        self.cut_rectangle((30, 30), (50, 50))
        self.canvas.set_brush_mode(False)
        self.assertEqual(self.shape.holes, [])

    def test_keep_holes_commits_hole(self):
        self.canvas.set_brush_mode(True, "rectangle")
        self.canvas.set_brush_keep_holes(True)
        self.cut_rectangle((30, 30), (50, 50))
        self.canvas.set_brush_mode(False)

        self.assertEqual(len(self.shape.holes), 1)
        self.assertFalse(self.canvas.brush_keep_holes)
        path = self.shape.make_path()
        self.assertFalse(path.contains(QtCore.QPointF(40, 40)))
        self.assertTrue(path.contains(QtCore.QPointF(20, 20)))

    def test_shape_with_holes_enables_keep_holes_and_round_trips(self):
        self.shape.holes = [points([(30, 30), (50, 30), (50, 50), (30, 50)])]
        self.canvas.set_brush_mode(True, "brush")
        self.assertTrue(self.canvas.brush_keep_holes)
        before = self.shape.mask.copy()
        self.assertEqual(before[40, 40], 0)
        self.assertEqual(before[30, 30], 255)

        # Repeated stroke commits must not erode the hole rim.
        for _ in range(3):
            self.canvas._update_shape_points_from_mask(self.shape)
        self.assertTrue(np.array_equal(self.shape.mask, before))
        self.assertEqual(len(self.shape.holes), 1)

    def test_turning_keep_holes_off_fills_them_undoably(self):
        self.shape.holes = [points([(30, 30), (50, 30), (50, 50), (30, 50)])]
        self.canvas.set_brush_mode(True, "brush")
        self.canvas.set_brush_keep_holes(False)
        self.assertEqual(self.shape.holes, [])
        self.assertEqual(self.shape.mask[40, 40], 255)
        self.canvas.brush_undo()
        self.assertTrue(self.canvas.brush_keep_holes)
        self.assertEqual(self.shape.mask[40, 40], 0)
        self.assertEqual(len(self.shape.holes), 1)

    def test_cancel_restores_holes(self):
        self.shape.holes = [points([(30, 30), (50, 30), (50, 50), (30, 50)])]
        self.canvas.set_brush_mode(True, "brush")
        self.canvas.set_brush_keep_holes(False)
        self.canvas.cancel_brush_mode()
        self.assertEqual(len(self.shape.holes), 1)

    def test_island_inside_hole_is_dropped(self):
        self.canvas.set_brush_mode(True, "brush")
        self.canvas.set_brush_keep_holes(True)
        self.shape.mask[25:66, 25:66] = 0
        self.shape.mask[40:46, 40:46] = 255
        self.canvas._update_shape_points_from_mask(self.shape)
        self.assertEqual(self.shape.mask[42, 42], 0)
        self.assertEqual(len(self.shape.holes), 1)

    def test_holes_serialize_and_move(self):
        self.shape.holes = [points([(30, 30), (50, 30), (50, 50), (30, 50)])]
        data = self.shape.to_dict()
        self.assertEqual(data["holes"][0][0], (30.0, 30.0))
        loaded = Shape().load_from_dict(data)
        self.assertEqual(loaded.holes[0][2], QtCore.QPointF(50, 50))
        self.assertNotIn("holes", loaded.other_data)
        loaded.move_by(QtCore.QPointF(5, 0))
        self.assertEqual(loaded.holes[0][0], QtCore.QPointF(35, 30))
        self.assertNotIn("holes", Shape(shape_type="polygon").to_dict())


if __name__ == "__main__":
    unittest.main()
