import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtCore import Qt

    from anylabeling.views.labeling.label_widget import LabelingWidget
    from anylabeling.views.labeling.widgets.canvas import Canvas
    from anylabeling.views.labeling.widgets.zoom_widget import ZoomWidget

    PYQT_AVAILABLE = True
except Exception:
    PYQT_AVAILABLE = False


if PYQT_AVAILABLE:

    class ZoomHarness:
        """Real canvas in a real scroll area, driven by LabelingWidget's zoom methods"""

        zoom_request = LabelingWidget.zoom_request
        pinch_zoom_request = LabelingWidget.pinch_zoom_request
        add_zoom = LabelingWidget.add_zoom
        _zoom_anchor = LabelingWidget._zoom_anchor
        _restore_zoom_anchor = LabelingWidget._restore_zoom_anchor
        _pinch_anchor_stale = LabelingWidget._pinch_anchor_stale

        def __init__(self, image_size, zoom):
            self.canvas = Canvas(parent=None)
            self.canvas.load_pixmap(QtGui.QPixmap(*image_size))
            self.scroll_area = QtWidgets.QScrollArea()
            self.scroll_area.setWidget(self.canvas)
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.resize(400, 300)
            self.scroll_area.show()
            self.scroll_bars = {
                Qt.Orientation.Vertical: self.scroll_area.verticalScrollBar(),
                Qt.Orientation.Horizontal: self.scroll_area.horizontalScrollBar(),
            }
            self.zoom_widget = ZoomWidget()
            self.zoom_widget.valueChanged.connect(self.paint_canvas)
            self._pinch_zoom_value = None
            self._pinch_anchor = None
            self.set_zoom(zoom)
            # Start with the image's top-left at the viewport's, past the
            # pan margin, as LabelingWidget does after loading.
            margin = self.canvas.pan_margin()
            self.set_scroll(Qt.Orientation.Horizontal, margin.width())
            self.set_scroll(Qt.Orientation.Vertical, margin.height())

        def paint_canvas(self):
            self.canvas.scale = 0.01 * self.zoom_widget.value()
            self.canvas.adjustSize()

        def set_zoom(self, value):
            self.zoom_widget.setValue(value)

        def set_scroll(self, orientation, value):
            self.scroll_bars[orientation].setValue(round(value))

        def image_point_at(self, viewport_pos):
            return self.canvas.transform_pos(
                QtCore.QPointF(viewport_pos - self.canvas.pos())
            )

        def canvas_pos(self, viewport_pos):
            return viewport_pos - self.canvas.pos()


@unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 is required for zoom tests")
class TestLabelWidgetZoomAnchor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(
            []
        )

    def assert_image_point_kept(self, harness, viewport_pos, before, places):
        after = harness.image_point_at(viewport_pos)
        self.assertAlmostEqual(after.x(), before.x(), places=places)
        self.assertAlmostEqual(after.y(), before.y(), places=places)

    def test_wheel_zoom_keeps_point_under_cursor(self):
        harness = ZoomHarness((1000, 800), zoom=100)
        cursor = QtCore.QPoint(300, 70)
        before = harness.image_point_at(cursor)

        harness.zoom_request(120, harness.canvas_pos(cursor))

        self.assertGreater(harness.zoom_widget.value(), 100)
        self.assert_image_point_kept(harness, cursor, before, places=0)

    def test_zoom_anchors_overflowing_axis_when_other_axis_fits(self):
        # Portrait image: canvas width is pinned to the viewport, height overflows.
        harness = ZoomHarness((200, 1000), zoom=100)
        cursor = QtCore.QPoint(200, 250)
        before = harness.image_point_at(cursor)

        harness.zoom_request(120, harness.canvas_pos(cursor))

        self.assertAlmostEqual(
            harness.image_point_at(cursor).y(), before.y(), places=0
        )

    def test_pinch_zoom_does_not_drift_over_many_events(self):
        harness = ZoomHarness((1000, 800), zoom=100)
        cursor = QtCore.QPoint(330, 90)
        before = harness.image_point_at(cursor)

        for _ in range(60):
            harness.pinch_zoom_request(1.013, harness.canvas_pos(cursor))
        for _ in range(30):
            harness.pinch_zoom_request(0.99, harness.canvas_pos(cursor))

        self.assertGreater(harness.zoom_widget.value(), 150)
        self.assert_image_point_kept(harness, cursor, before, places=0)

    def test_pinch_after_pan_anchors_on_new_point_under_cursor(self):
        harness = ZoomHarness((1000, 800), zoom=100)
        cursor = QtCore.QPoint(200, 150)
        for _ in range(10):
            harness.pinch_zoom_request(1.02, harness.canvas_pos(cursor))

        # Trackpad pan: the image scrolls while the cursor stays put.
        for orientation in harness.scroll_bars:
            harness.set_scroll(
                orientation, harness.scroll_bars[orientation].value() + 120
            )
        after_pan = harness.image_point_at(cursor)

        harness.pinch_zoom_request(1.02, harness.canvas_pos(cursor))

        self.assert_image_point_kept(harness, cursor, after_pan, places=0)


if __name__ == "__main__":
    unittest.main()
