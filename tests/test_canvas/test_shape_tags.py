import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6 import QtCore, QtGui, QtWidgets

    from anylabeling.views.labeling.widgets.canvas import Canvas

    PYQT_AVAILABLE = True
except Exception:
    PYQT_AVAILABLE = False


@unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 is required for shape tag tests")
class TestCanvasShapeTags(unittest.TestCase):

    def setUp(self):
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])
        self.canvas = Canvas(parent=None)

    def tearDown(self):
        self.canvas.close()
        self.app.processEvents()

    def key_event(self, event_type, key, auto_repeat=False, modifiers=None):
        return QtGui.QKeyEvent(
            event_type,
            key,
            modifiers or QtCore.Qt.KeyboardModifier.NoModifier,
            "",
            auto_repeat,
        )

    def test_toggle_hides_tags_without_changing_show_settings(self):
        self.assertTrue(self.canvas.shape_tags_visible())
        self.canvas.hide_shape_tags = True
        self.assertFalse(self.canvas.shape_tags_visible())
        self.assertTrue(self.canvas.show_texts)
        self.assertTrue(self.canvas.show_labels)
        self.assertTrue(self.canvas.show_attributes)

    def test_holding_h_hides_tags_until_release(self):
        press = QtCore.QEvent.Type.KeyPress
        release = QtCore.QEvent.Type.KeyRelease
        key = QtCore.Qt.Key.Key_H

        self.canvas.keyPressEvent(self.key_event(press, key))
        self.assertFalse(self.canvas.shape_tags_visible())

        # Auto-repeat releases while the key is held must not show tags.
        self.canvas.keyReleaseEvent(
            self.key_event(release, key, auto_repeat=True)
        )
        self.assertFalse(self.canvas.shape_tags_visible())

        self.canvas.keyReleaseEvent(self.key_event(release, key))
        self.assertTrue(self.canvas.shape_tags_visible())

    def test_modified_h_does_not_hide_tags(self):
        self.canvas.keyPressEvent(
            self.key_event(
                QtCore.QEvent.Type.KeyPress,
                QtCore.Qt.Key.Key_H,
                modifiers=QtCore.Qt.KeyboardModifier.ShiftModifier,
            )
        )
        self.assertTrue(self.canvas.shape_tags_visible())

    def test_focus_out_restores_held_tags(self):
        self.canvas.keyPressEvent(
            self.key_event(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_H)
        )
        self.canvas.focusOutEvent(
            QtGui.QFocusEvent(QtCore.QEvent.Type.FocusOut)
        )
        self.assertTrue(self.canvas.shape_tags_visible())


if __name__ == "__main__":
    unittest.main()
