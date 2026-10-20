import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6 import QtCore, QtGui, QtWidgets

    from anylabeling.views.labeling.shape import Shape
    from anylabeling.views.labeling.widgets.canvas import Canvas

    PYQT_AVAILABLE = True
except Exception:
    PYQT_AVAILABLE = False


class FakeMouseEvent:
    def __init__(self, button=None, ctrl=False):
        self._button = button or QtCore.Qt.MouseButton.LeftButton
        self._ctrl = ctrl

    def button(self):
        return self._button

    def buttons(self):
        return self._button

    def modifiers(self):
        if self._ctrl:
            return QtCore.Qt.KeyboardModifier.ControlModifier
        return QtCore.Qt.KeyboardModifier.NoModifier


@unittest.skipUnless(
    PYQT_AVAILABLE, "PyQt6 is required for canvas region edit tests"
)
class TestCanvasRegionEdit(unittest.TestCase):

    def setUp(self):
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])
        self.canvas = Canvas(parent=None)
        self.canvas.pixmap = QtGui.QPixmap(100, 100)
        self.canvas.pixmap.fill(QtGui.QColor("black"))
        self.shape = Shape(label="object", shape_type="polygon")
        self.shape.points = [
            QtCore.QPointF(x, y)
            for x, y in [(10.0, 10.0), (50.0, 10.0), (50.0, 50.0), (10.0, 50.0)]
        ]
        self.shape.close()
        self.shape.selected = True
        self.canvas.shapes = [self.shape]
        self.canvas.selected_shapes = [self.shape]
        self.canvas.store_shapes()

    def tearDown(self):
        self.canvas.close()
        self.app.processEvents()

    def press(self, x, y, ctrl=False):
        self.canvas._brush_mouse_press(
            FakeMouseEvent(ctrl=ctrl), QtCore.QPointF(x, y)
        )

    def drag_rectangle(self, p1, p2, ctrl=False):
        self.press(*p1, ctrl=ctrl)
        self.canvas._region_mouse_release(
            FakeMouseEvent(ctrl=ctrl), QtCore.QPointF(*p2)
        )

    def xs(self):
        return [point.x() for point in self.shape.points]

    def test_dragged_rectangle_adds_to_mask(self):
        self.canvas.set_brush_mode(True, "rectangle")
        self.drag_rectangle((40, 10), (80, 50))
        self.assertGreaterEqual(max(self.xs()), 79)
        self.assertEqual(len(self.canvas._brush_undo_stack), 2)

    def test_ctrl_rectangle_cuts_from_mask(self):
        self.canvas.set_brush_mode(True, "rectangle")
        self.drag_rectangle((30, 0), (60, 60), ctrl=True)
        self.assertLessEqual(max(self.xs()), 30)
        self.canvas.set_brush_mode(False)
        self.assertFalse(self.canvas.is_brush_mode)
        self.assertIsNone(self.shape.mask)
        self.assertLessEqual(max(self.xs()), 30)

    def test_two_click_rectangle(self):
        self.canvas.set_brush_mode(True, "rectangle")
        self.drag_rectangle((40, 10), (40, 10))
        self.assertEqual(len(self.canvas._region_points), 1)
        self.press(80, 50)
        self.assertEqual(self.canvas._region_points, [])
        self.assertGreaterEqual(max(self.xs()), 79)

    def test_polygon_cut_that_splits_keeps_largest_piece(self):
        self.canvas.set_brush_mode(True, "polygon")
        for x, y in [(20, 0), (25, 0), (25, 60), (20, 60)]:
            self.press(x, y, ctrl=True)
        self.press(20, 0, ctrl=True)  # closes on the first vertex
        self.assertEqual(self.canvas._region_points, [])
        self.assertGreaterEqual(min(self.xs()), 25)

    def test_escape_drops_pending_polygon_before_cancelling(self):
        self.canvas.set_brush_mode(True, "polygon")
        self.press(60, 10)
        self.press(80, 10)
        key = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyPress,
            QtCore.Qt.Key.Key_Escape,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        self.canvas._brush_key_press(key)
        self.assertEqual(self.canvas._region_points, [])
        self.assertTrue(self.canvas.is_brush_mode)
        self.canvas._brush_key_press(key)
        self.assertFalse(self.canvas.is_brush_mode)

    def test_enter_closes_polygon_and_right_click_commits(self):
        self.canvas.set_brush_mode(True, "polygon")
        for x, y in [(40, 10), (90, 10), (90, 50)]:
            self.press(x, y)
        enter = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyPress,
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        self.assertTrue(self.canvas._brush_key_press(enter))
        self.assertGreaterEqual(max(self.xs()), 89)
        for x, y in [(0, 0), (5, 0), (5, 5)]:
            self.press(x, y)
        self.canvas._brush_mouse_release(
            FakeMouseEvent(QtCore.Qt.MouseButton.RightButton)
        )
        self.assertFalse(self.canvas.is_brush_mode)
        self.assertGreaterEqual(max(self.xs()), 89)

    def test_switching_tools_keeps_history(self):
        self.canvas.set_brush_mode(True, "rectangle")
        self.drag_rectangle((40, 10), (80, 50))
        self.canvas.set_brush_mode(True, "polygon")
        self.assertEqual(self.canvas.brush_tool, "polygon")
        self.assertEqual(len(self.canvas._brush_undo_stack), 2)
        self.canvas.brush_undo()
        self.assertLessEqual(max(self.xs()), 51)
        self.canvas.set_brush_mode(False)
        self.assertEqual(self.canvas.brush_tool, "brush")


if __name__ == "__main__":
    unittest.main()
