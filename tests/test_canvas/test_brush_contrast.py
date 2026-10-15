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


@unittest.skipUnless(
    PYQT_AVAILABLE, "PyQt6 is required for canvas brush contrast tests"
)
class TestCanvasBrushContrast(unittest.TestCase):

    def setUp(self):
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])
        self.canvas = Canvas(parent=None)

    def tearDown(self):
        self.canvas.close()
        self.app.processEvents()

    def load_image(self, color):
        self.canvas.pixmap = QtGui.QPixmap(100, 100)
        self.canvas.pixmap.fill(QtGui.QColor(color))

    def enter_brush_mode(self):
        shape = Shape(label="object", shape_type="polygon")
        shape.points = [
            QtCore.QPointF(x, y)
            for x, y in [(20, 20), (80, 20), (80, 80), (20, 80)]
        ]
        shape.close()
        shape.selected = True
        self.canvas.shapes = [shape]
        self.canvas.selected_shapes = [shape]
        self.canvas.store_shapes()
        self.canvas.set_brush_mode(True)
        self.assertTrue(self.canvas.is_brush_mode)
        return shape

    def paint(self, painter_fn):
        image = QtGui.QImage(100, 100, QtGui.QImage.Format.Format_RGB32)
        image.fill(QtGui.QColor(127, 0, 127))
        painter = QtGui.QPainter(image)
        painter_fn(painter)
        painter.end()
        return image

    def ring_color(self, center=(50, 50)):
        self.canvas.brush_radius = 10
        self.canvas.prev_move_point = QtCore.QPointF(*center)
        image = self.paint(self.canvas._paint_brush_cursor)
        return image.pixelColor(center[0] + 10, center[1])

    def test_brush_ring_is_black_on_light_and_white_on_dark_image(self):
        self.load_image("white")
        self.enter_brush_mode()
        self.assertEqual(self.ring_color().lightness(), 0)

        self.load_image("black")
        self.assertEqual(self.ring_color().lightness(), 255)

    def test_brush_ring_does_not_flicker_on_mid_grey(self):
        self.load_image("white")
        self.enter_brush_mode()
        self.assertEqual(self.ring_color().lightness(), 0)

        # Mid grey sits inside the hysteresis band, so the ring keeps its colour.
        self.load_image(QtGui.QColor(128, 128, 128))
        self.assertEqual(self.ring_color().lightness(), 0)

    def test_eraser_ring_stays_red(self):
        self.load_image("white")
        self.enter_brush_mode()
        self.canvas.eraser_mode = True
        color = self.ring_color()
        self.assertGreater(color.red(), color.green())

    def test_brush_outline_contrasts_with_image_under_it(self):
        self.load_image("white")
        self.enter_brush_mode()
        image = self.paint(self.canvas._paint_brush_overlays)
        self.assertLess(image.pixelColor(50, 20).lightness(), 64)

        self.load_image("black")
        image = self.paint(self.canvas._paint_brush_overlays)
        self.assertGreater(image.pixelColor(50, 20).lightness(), 192)


if __name__ == "__main__":
    unittest.main()
