import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtCore import Qt

    from anylabeling.views.labeling.widgets.canvas import Canvas

    PYQT_AVAILABLE = True
except Exception:
    PYQT_AVAILABLE = False


@unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 is required for pan margin tests")
class TestCanvasPanMargin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(
            []
        )

    def setUp(self):
        self.canvas = Canvas(parent=None)
        self.canvas.load_pixmap(QtGui.QPixmap(200, 100))
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.resize(400, 300)
        self.scroll_area.show()
        self.set_scale(4.0)

    def tearDown(self):
        self.scroll_area.close()
        self.app.processEvents()

    def set_scale(self, scale):
        self.canvas.scale = scale
        self.canvas.adjustSize()

    def widget_pos(self, x, y):
        return (
            QtCore.QPointF(x, y) + self.canvas.offset_to_center()
        ) * self.canvas.scale

    def click(self, x, y):
        pos = self.widget_pos(x, y)
        self.canvas.mousePressEvent(
            QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseButtonPress,
                pos,
                pos,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
        )

    def move(self, x, y):
        pos = self.widget_pos(x, y)
        self.canvas.mouseMoveEvent(
            QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove,
                pos,
                pos,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            )
        )

    def test_zoomed_image_pans_past_its_edges(self):
        viewport = self.scroll_area.viewport().size()
        bars = {
            Qt.Orientation.Horizontal: self.scroll_area.horizontalScrollBar(),
            Qt.Orientation.Vertical: self.scroll_area.verticalScrollBar(),
        }
        for bar in bars.values():
            bar.setValue(bar.maximum())
        bottom_right = self.canvas.transform_pos(
            QtCore.QPointF(
                bars[Qt.Orientation.Horizontal].value() + viewport.width(),
                bars[Qt.Orientation.Vertical].value() + viewport.height(),
            )
        )
        # The view extends past the image, so its edge can sit inside it.
        self.assertGreater(bottom_right.x(), self.canvas.pixmap.width())
        self.assertGreater(bottom_right.y(), self.canvas.pixmap.height())

        for bar in bars.values():
            bar.setValue(0)
        top_left = self.canvas.transform_pos(
            QtCore.QPointF(
                bars[Qt.Orientation.Horizontal].value(),
                bars[Qt.Orientation.Vertical].value(),
            )
        )
        self.assertLess(top_left.x(), 0)
        self.assertLess(top_left.y(), 0)

    def test_polygon_points_outside_snap_to_nearest_edge(self):
        self.canvas.set_editing(False)
        self.canvas.create_mode = "polygon"

        self.click(-20, 50)
        self.assertEqual(self.canvas.current[0], QtCore.QPointF(0, 50))

        # Past the bottom-right corner: nearest pixel is the corner itself.
        self.move(260, 140)
        self.assertEqual(self.canvas.line[1], QtCore.QPointF(199, 99))
        self.click(260, 140)
        self.assertEqual(self.canvas.current[-1], QtCore.QPointF(199, 99))

    def test_point_outside_snaps_to_edge(self):
        self.canvas.set_editing(False)
        self.canvas.create_mode = "point"

        self.click(80, -15)

        self.assertEqual(len(self.canvas.shapes), 1)
        self.assertEqual(self.canvas.shapes[0][0], QtCore.QPointF(80, 0))


if __name__ == "__main__":
    unittest.main()
