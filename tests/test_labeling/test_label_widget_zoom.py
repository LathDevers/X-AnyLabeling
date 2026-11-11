import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6 import QtCore, QtGui

from anylabeling.views.labeling.label_widget import LabelingWidget
from tests.test_canvas.test_navigation import (  # noqa: F401
    NavigationView,
    image_position,
    navigation_app,
    view,
)

NavigationView.pinch_zoom_request = LabelingWidget.pinch_zoom_request


def pinch(view, factor, point):
    view.canvas.pinch_zoom_request.emit(
        factor, (point - QtCore.QPointF(view.canvas.pos())).toPoint()
    )


def assert_kept(actual, expected):
    assert actual.x() == pytest.approx(expected.x(), abs=0.5)
    assert actual.y() == pytest.approx(expected.y(), abs=0.5)


@pytest.fixture
def pinch_view(view):
    view.canvas.pinch_zoom_request.connect(view.pinch_zoom_request)
    return view


def test_pinch_zoom_does_not_drift_over_many_events(pinch_view):
    point = QtCore.QPointF(330, 90) + QtCore.QPointF(pinch_view.canvas.pos())
    before = image_position(pinch_view, point)

    for _ in range(60):
        pinch(pinch_view, 1.013, point)
    for _ in range(30):
        pinch(pinch_view, 0.99, point)

    assert pinch_view.canvas.scale > 1.5
    assert_kept(image_position(pinch_view, point), before)


def test_tiny_pinch_steps_are_not_swallowed_by_zoom_rounding(pinch_view):
    point = QtCore.QPointF(200, 150) + QtCore.QPointF(pinch_view.canvas.pos())
    for _ in range(100):
        pinch(pinch_view, 1.002, point)
    assert pinch_view.canvas.scale == pytest.approx(1.002**100)


def test_pinch_after_pan_anchors_on_new_point_under_cursor(pinch_view):
    point = QtCore.QPointF(200, 150) + QtCore.QPointF(pinch_view.canvas.pos())
    for _ in range(10):
        pinch(pinch_view, 1.02, point)

    # Trackpad pan: the image moves while the cursor stays put.
    pinch_view.pan_canvas(QtCore.QPointF(-120, -120))
    after_pan = image_position(pinch_view, point)

    pinch(pinch_view, 1.02, point)

    assert_kept(image_position(pinch_view, point), after_pan)


def wheel(view, phase, pixel, angle):
    point = QtCore.QPointF(200, 150)
    return QtGui.QWheelEvent(
        point,
        QtCore.QPointF(view.canvas.mapToGlobal(point.toPoint())),
        pixel,
        angle,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        phase,
        False,
    )


def test_trackpad_scroll_pans_instead_of_zooming(view):
    scale = view.canvas.scale
    offset = QtCore.QPointF(view.canvas.pan_offset)

    view.canvas.wheelEvent(
        wheel(
            view,
            QtCore.Qt.ScrollPhase.ScrollUpdate,
            QtCore.QPoint(-30, 12),
            QtCore.QPoint(-90, 36),
        )
    )

    assert view.canvas.scale == scale
    assert view.canvas.pan_offset == offset + QtCore.QPointF(-30, 12)


def test_mouse_wheel_still_zooms(view):
    requests = []
    view.canvas.zoom_request.connect(lambda delta, pos: requests.append(delta))

    view.canvas.wheelEvent(
        wheel(
            view,
            QtCore.Qt.ScrollPhase.NoScrollPhase,
            QtCore.QPoint(),
            QtCore.QPoint(0, 120),
        )
    )

    assert requests == [120]


def test_native_pinch_gesture_reaches_zoom(pinch_view):
    scale = pinch_view.canvas.scale
    point = QtCore.QPointF(200, 150)
    gesture = QtGui.QNativeGestureEvent(
        QtCore.Qt.NativeGestureType.ZoomNativeGesture,
        QtGui.QPointingDevice.primaryPointingDevice(),
        2,
        point,
        point,
        point,
        0.1,
        QtCore.QPointF(),
    )

    assert pinch_view.canvas.event(gesture)

    assert pinch_view.canvas.scale == pytest.approx(scale * 1.1)
