import os
import subprocess
import sys
import textwrap
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6 import QtCore, QtGui, QtWidgets

    from anylabeling.views.labeling.label_widget import (
        LabelingWidget,
        _can_subtract_shapes,
    )
    from anylabeling.views.labeling.shape import Shape
    from anylabeling.views.labeling.widgets.canvas import Canvas

    PYQT_AVAILABLE = True
except Exception:
    PYQT_AVAILABLE = False


def make_shape(label, xys, shape_type="polygon"):
    shape = Shape(label=label, shape_type=shape_type)
    shape.points = [QtCore.QPointF(x, y) for x, y in xys]
    shape.close()
    return shape


@unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 is required for subtract tests")
class TestSubtractSelection(unittest.TestCase):

    def setUp(self):
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])
        self.canvas = Canvas(parent=None)
        self.canvas.pixmap = QtGui.QPixmap(200, 200)
        self.target = make_shape(
            "leaf", [(0, 0), (100, 0), (100, 100), (0, 100)]
        )
        self.target.attributes = {"kind": "a"}
        self.other = make_shape("other", [(150, 150), (160, 150), (160, 160)])
        self.cutter = make_shape(
            "stem",
            [(40, -10), (60, -10), (60, 110), (40, 110)],
            shape_type="rectangle",
        )
        self.canvas.shapes = [self.target, self.other, self.cutter]
        self.canvas.store_shapes()
        self.widget = SimpleNamespace(
            canvas=self.canvas,
            label_list=Mock(),
            load_shapes=Mock(
                side_effect=lambda shapes, **kwargs: self.canvas.load_shapes(
                    shapes
                )
            ),
            set_dirty=Mock(),
        )

    def tearDown(self):
        self.canvas.close()
        self.app.processEvents()

    def test_target_is_replaced_in_place_by_its_pieces(self):
        self.canvas.selected_shapes = [self.target, self.cutter]
        backups = len(self.canvas.shapes_backups)

        LabelingWidget.subtract_selection(self.widget)

        shapes = self.canvas.shapes
        self.assertEqual(len(shapes), 4)
        self.assertNotIn(self.target, shapes)
        left, right = shapes[0], shapes[1]
        self.assertEqual(shapes[2:], [self.other, self.cutter])
        for piece in (left, right):
            self.assertEqual(piece.label, "leaf")
            self.assertEqual(piece.attributes, {"kind": "a"})
            self.assertEqual(piece.holes, [])
        self.assertEqual(len(self.canvas.shapes_backups), backups + 1)
        self.widget.label_list.clear.assert_called_once_with()

    def test_enclosed_cutter_makes_a_hole(self):
        inner = make_shape("hole", [(30, 30), (70, 30), (70, 70), (30, 70)])
        self.canvas.shapes.append(inner)
        self.canvas.selected_shapes = [self.target, inner]

        LabelingWidget.subtract_selection(self.widget)

        piece = self.canvas.shapes[0]
        self.assertEqual(len(piece.holes), 1)
        self.assertIn(inner, self.canvas.shapes)

    def test_disjoint_cutter_changes_nothing(self):
        self.canvas.selected_shapes = [self.other, self.cutter]
        before = list(self.canvas.shapes)

        LabelingWidget.subtract_selection(self.widget)

        self.assertEqual(self.canvas.shapes, before)
        self.widget.set_dirty.assert_not_called()

    def test_enablement_needs_unlocked_polygon_targets_and_area_cutter(self):
        self.assertTrue(_can_subtract_shapes([self.target, self.cutter]))
        self.assertFalse(_can_subtract_shapes([self.cutter, self.target]))
        self.assertFalse(_can_subtract_shapes([self.target]))
        self.target.locked = True
        self.assertFalse(_can_subtract_shapes([self.target, self.cutter]))


class TestSubtractSelectionInMainWindow(unittest.TestCase):

    def test_pieces_reach_the_canvas_and_shortcut_triggers(self):
        # Runs the real window: the label list reloads the canvas when rows are removed, which a mocked list hides.
        script = textwrap.dedent("""\
            import os
            import tempfile
            from pathlib import Path
            from PyQt6 import QtCore, QtGui, QtWidgets
            from PyQt6.QtTest import QTest
            from anylabeling import config
            import anylabeling.resources.resources
            from anylabeling.views.mainwindow import MainWindow
            from anylabeling.views.labeling.shape import Shape

            def make(label, xys, shape_type="polygon"):
                shape = Shape(label=label, shape_type=shape_type)
                shape.points = [QtCore.QPointF(x, y) for x, y in xys]
                shape.close()
                return shape

            with tempfile.TemporaryDirectory() as directory:
                config.set_work_directory(directory)
                config.current_config_file = str(
                    Path(directory) / '.xanylabelingrc'
                )
                app = QtWidgets.QApplication([])
                window = MainWindow(app, config=config.get_default_config())
                view = window.labeling_widget.view
                image = QtGui.QImage(200, 200, QtGui.QImage.Format.Format_RGB32)
                image.fill(QtGui.QColor('gray'))
                path = os.path.join(directory, 'a.png')
                image.save(path)
                view.load_file(path)
                target = make('leaf', [(10, 10), (150, 10), (150, 150), (10, 150)])
                cutter = make(
                    'stem', [(60, 0), (90, 0), (90, 190), (60, 190)], 'rectangle'
                )
                view.load_shapes([target, cutter], replace=False)
                window.show()
                app.processEvents()
                view.canvas.select_shapes([target, cutter])
                QTest.keyClick(
                    view.canvas,
                    QtCore.Qt.Key.Key_X,
                    QtCore.Qt.KeyboardModifier.ControlModifier
                    | QtCore.Qt.KeyboardModifier.ShiftModifier,
                )
                app.processEvents()
                labels = [shape.label for shape in view.canvas.shapes]
                assert labels == ['leaf', 'leaf', 'stem'], labels
                assert len(view.label_list) == 3
                view.undo_shape_edit()
                labels = [shape.label for shape in view.canvas.shapes]
                assert labels == ['leaf', 'stem'], labels
                window.close()
            """)
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
